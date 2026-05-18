"""
Code-Based Benchmark Cases for V6.

These cases present actual Python code snippets or pseudocode that the LLM
must audit for point-in-time violations. They are designed to be extremely
hard because:

1. The model must understand code semantics, not just prose
2. Bugs are hidden in implementation details (wrong columns, off-by-one)
3. Comments may be misleading (say one thing, do another)
4. Some valid code looks suspicious (tests overcaution)

Categories:
- Subtle implementation bugs (wrong date column, merge order, lag errors)
- Deceptive code (comments lie, professional but wrong)
- Valid but suspicious (correct code that looks like it has bugs)
"""

from backtest_lie_detector.schemas import (
    BenchmarkCase,
    Difficulty,
    Module,
    SourceFields,
    Validity,
    ViolationType,
)


CODE_CASES = [
    # =========================================================================
    # Case 1: Wrong date column - uses datadate instead of rdq
    # INVALID - Classic Compustat mistake
    # =========================================================================
    BenchmarkCase(
        id="code_datadate_not_rdq",
        module=Module.ACCOUNTING_AVAILABILITY,
        difficulty=Difficulty.HARD,
        prompt='''
Audit this Python code for point-in-time validity:

```python
import pandas as pd

def build_value_portfolio(compustat_df, portfolio_date):
    """Build a value portfolio using book-to-market ratios."""
    
    # Get latest annual fundamentals with 6-month lag
    cutoff = portfolio_date - pd.DateOffset(months=6)
    
    available = compustat_df[compustat_df['datadate'] <= cutoff].copy()
    
    # Keep most recent observation per firm
    available = available.sort_values('datadate').groupby('gvkey').tail(1)
    
    # Calculate book-to-market
    available['bm'] = available['ceq'] / available['mktcap']
    
    # Select top tercile
    threshold = available['bm'].quantile(0.67)
    value_stocks = available[available['bm'] >= threshold]
    
    return value_stocks['gvkey'].tolist()
```
''',
        expected_validity=Validity.INVALID,
        expected_violations=[ViolationType.ACCOUNTING_AVAILABILITY_LEAKAGE],
        expected_repair=[
            "Use 'rdq' (report date of quarterly) instead of 'datadate' for availability check.",
            "datadate is the fiscal period end date, not when data became available.",
            "A December fiscal year end (datadate) isn't public until the 10-K filing (rdq) in Feb/March."
        ],
        ground_truth_notes=(
            "The code uses 'datadate' which is fiscal period end, not data availability. "
            "For a December FYE company, datadate=Dec 31 but rdq (report date) might be Feb 28. "
            "Using datadate <= cutoff allows using data before it was filed."
        ),
        source_fields=SourceFields(
            extra={"bug_type": "wrong_date_column", "wrong": "datadate", "correct": "rdq"},
        ),
        data_source="manual",
        case_tags=["code_case", "subtle_bug", "requires_dataset_semantics"],
        source_note="Common Compustat mistake - datadate vs rdq",
    ),

    # =========================================================================
    # Case 2: Comment says 6-month lag but code uses 3 months
    # INVALID - Comment lies
    # =========================================================================
    BenchmarkCase(
        id="code_comment_lies_lag",
        module=Module.ACCOUNTING_AVAILABILITY,
        difficulty=Difficulty.HARD,
        prompt='''
Audit this code for point-in-time validity:

```python
def get_available_fundamentals(fundamentals, as_of_date):
    """
    Get fundamentals available as of a given date.
    
    Uses a conservative 6-month lag from fiscal year end to ensure
    all 10-K filings have been published.
    """
    # Apply conservative lag to ensure data availability
    lag_months = 3
    cutoff = as_of_date - pd.DateOffset(months=lag_months)
    
    # Filter to data with fiscal year end before cutoff
    available = fundamentals[fundamentals['fiscal_year_end'] <= cutoff]
    
    return available
```
''',
        expected_validity=Validity.INVALID,
        expected_violations=[ViolationType.ACCOUNTING_AVAILABILITY_LEAKAGE],
        expected_repair=[
            "The docstring claims 6-month lag but code uses lag_months=3.",
            "3 months from fiscal year end is not enough for many 10-K filings.",
            "Either fix the code to use 6 months or fix the docstring and validate 3 months is sufficient."
        ],
        ground_truth_notes=(
            "The docstring says '6-month lag' but the code sets lag_months=3. "
            "This is a dangerous bug because the comment suggests careful methodology "
            "while the implementation uses an insufficient lag."
        ),
        source_fields=SourceFields(
            extra={"bug_type": "comment_code_mismatch", "comment_says": "6 months", "code_does": "3 months"},
        ),
        data_source="manual",
        case_tags=["code_case", "deceptive_code", "misleading_language"],
        source_note="Comment says one thing, code does another",
    ),

    # =========================================================================
    # Case 3: Correct CRSP delisting return handling - VALID
    # Tests if model understands the compounding formula
    # =========================================================================
    BenchmarkCase(
        id="code_correct_dlret_valid",
        module=Module.SURVIVORSHIP_DELISTING,
        difficulty=Difficulty.HARD,
        prompt='''
Audit this code for point-in-time validity:

```python
def calculate_total_return(crsp_row):
    """
    Calculate total return including delisting return.
    Follows Shumway (1997) methodology.
    """
    ret = crsp_row['ret']
    dlret = crsp_row['dlret']
    
    # Handle missing values
    if pd.isna(ret):
        ret = 0
    if pd.isna(dlret):
        dlret = 0
    
    # Compound the returns
    total_ret = (1 + ret) * (1 + dlret) - 1
    
    return total_ret

# Apply to CRSP data
crsp_monthly['total_ret'] = crsp_monthly.apply(calculate_total_return, axis=1)
```
''',
        expected_validity=Validity.VALID,
        expected_violations=[],
        expected_repair=[],
        ground_truth_notes=(
            "This is CORRECT delisting return handling. The formula (1+ret)*(1+dlret)-1 "
            "properly compounds the regular return with the delisting return. This follows "
            "Shumway (1997) methodology. The model should NOT flag this as invalid."
        ),
        source_fields=SourceFields(
            extra={"methodology": "Shumway (1997)", "formula": "(1+ret)*(1+dlret)-1"},
        ),
        data_source="manual",
        case_tags=["code_case", "trap_valid", "requires_dataset_semantics"],
        source_note="Correct CRSP delisting methodology - should NOT be flagged",
    ),

    # =========================================================================
    # Case 4: Merge leaks future data - wrong merge direction
    # INVALID - Subtle merge bug
    # =========================================================================
    BenchmarkCase(
        id="code_merge_leaks_future",
        module=Module.ACCOUNTING_AVAILABILITY,
        difficulty=Difficulty.HARD,
        prompt='''
Audit this portfolio construction code:

```python
def construct_portfolio(prices, fundamentals, formation_date):
    """Construct portfolio using price and fundamental data."""
    
    # Get prices as of formation date
    prices_t = prices[prices['date'] == formation_date]
    
    # Merge with fundamentals (most recent available)
    portfolio = fundamentals.merge(
        prices_t[['permno', 'prc', 'shrout']],
        on='permno',
        how='left'
    )
    
    # Calculate market cap and book-to-market
    portfolio['mktcap'] = abs(portfolio['prc']) * portfolio['shrout']
    portfolio['bm'] = portfolio['book_equity'] / portfolio['mktcap']
    
    return portfolio[portfolio['bm'] > 0]
```

The fundamentals dataframe contains all historical fundamentals without date filtering.
''',
        expected_validity=Validity.INVALID,
        expected_violations=[ViolationType.ACCOUNTING_AVAILABILITY_LEAKAGE],
        expected_repair=[
            "The fundamentals dataframe is not filtered by date before merging.",
            "This allows future fundamentals to be used for the formation_date portfolio.",
            "Filter fundamentals to only include data available as of formation_date before merging."
        ],
        ground_truth_notes=(
            "The merge uses unfiltered fundamentals - it could include future data. "
            "The comment says 'most recent available' but the code doesn't enforce this. "
            "fundamentals should be filtered to reporting_date <= formation_date first."
        ),
        source_fields=SourceFields(
            extra={"bug_type": "unfiltered_merge"},
        ),
        data_source="manual",
        case_tags=["code_case", "subtle_bug"],
        source_note="Merge without date filter leaks future data",
    ),

    # =========================================================================
    # Case 5: Off-by-one in shift - monthly vs daily confusion
    # INVALID
    # =========================================================================
    BenchmarkCase(
        id="code_shift_off_by_one",
        module=Module.ACCOUNTING_AVAILABILITY,
        difficulty=Difficulty.HARD,
        prompt='''
Audit this momentum signal calculation:

```python
def calculate_momentum(returns_monthly):
    """
    Calculate 12-month momentum signal.
    Skip the most recent month to avoid microstructure effects.
    """
    # Cumulative return over months t-12 to t-2 (skip month t-1)
    returns_monthly['mom_12_2'] = (
        returns_monthly.groupby('permno')['ret']
        .apply(lambda x: x.shift(1).rolling(11).apply(lambda r: (1+r).prod() - 1))
    )
    
    return returns_monthly
```

This is applied to end-of-month CRSP returns where each row is one month.
''',
        expected_validity=Validity.INVALID,
        expected_violations=[ViolationType.ACCOUNTING_AVAILABILITY_LEAKAGE],
        expected_repair=[
            "shift(1) only skips 1 month, but rolling(11) then goes back 11 more months.",
            "This calculates months t-12 to t-1, not t-12 to t-2 as intended.",
            "Use shift(2).rolling(10) to properly skip month t-1 and calculate t-12 to t-2."
        ],
        ground_truth_notes=(
            "shift(1).rolling(11) gives months t-12 to t-1, not t-12 to t-2. "
            "To skip the most recent month (t-1), you need shift(2).rolling(10). "
            "This is an off-by-one error in the lag calculation."
        ),
        source_fields=SourceFields(
            extra={"bug_type": "off_by_one_shift", "intended": "t-12 to t-2", "actual": "t-12 to t-1"},
        ),
        data_source="manual",
        case_tags=["code_case", "subtle_bug"],
        source_note="Shift/rolling off-by-one error",
    ),

    # =========================================================================
    # Case 6: Correct point-in-time Compustat usage - VALID
    # =========================================================================
    BenchmarkCase(
        id="code_correct_pit_compustat_valid",
        module=Module.ACCOUNTING_AVAILABILITY,
        difficulty=Difficulty.HARD,
        prompt='''
Audit this Compustat data preparation:

```python
def get_pit_fundamentals(compustat, as_of_date):
    """
    Get point-in-time fundamentals using actual filing dates.
    """
    # Filter to filings that were public by as_of_date
    # rdq is the report date (when 10-K/10-Q was filed)
    available = compustat[compustat['rdq'] <= as_of_date].copy()
    
    # For each firm, keep only the most recent filing
    available = (available
        .sort_values(['gvkey', 'rdq'])
        .groupby('gvkey')
        .tail(1)
    )
    
    return available[['gvkey', 'datadate', 'rdq', 'at', 'ceq', 'ni']]
```
''',
        expected_validity=Validity.VALID,
        expected_violations=[],
        expected_repair=[],
        ground_truth_notes=(
            "This is CORRECT point-in-time handling. The code filters by rdq (report/filing date) "
            "not datadate (fiscal period end). This ensures only publicly available data is used. "
            "The model should NOT flag this as invalid."
        ),
        source_fields=SourceFields(
            extra={"methodology": "point-in-time using rdq"},
        ),
        data_source="manual",
        case_tags=["code_case", "trap_valid", "requires_dataset_semantics"],
        source_note="Correct PIT Compustat - should NOT be flagged",
    ),

    # =========================================================================
    # Case 7: Uses current S&P 500 list for historical backtest
    # INVALID - survivorship bias
    # =========================================================================
    BenchmarkCase(
        id="code_current_sp500_historical",
        module=Module.SURVIVORSHIP_DELISTING,
        difficulty=Difficulty.HARD,
        prompt='''
Audit this backtest universe construction:

```python
# Load current S&P 500 constituents (downloaded today, May 2026)
sp500 = pd.read_csv('sp500_constituents.csv')
sp500_tickers = set(sp500['ticker'].tolist())

def backtest_strategy(prices, start_date='2010-01-01', end_date='2020-12-31'):
    """Backtest momentum strategy on S&P 500 stocks."""
    
    # Filter to S&P 500 universe
    prices = prices[prices['ticker'].isin(sp500_tickers)]
    
    # Filter to backtest period
    prices = prices[(prices['date'] >= start_date) & (prices['date'] <= end_date)]
    
    # ... rest of strategy implementation
    return calculate_returns(prices)
```
''',
        expected_validity=Validity.INVALID,
        expected_violations=[ViolationType.SURVIVORSHIP_BIAS],
        expected_repair=[
            "Uses 2026 S&P 500 constituents for a 2010-2020 backtest.",
            "This excludes companies that were in S&P 500 during 2010-2020 but later removed.",
            "Use historical constituent lists for each rebalance date."
        ],
        ground_truth_notes=(
            "Classic survivorship bias. The 2026 S&P 500 list excludes companies like "
            "Lehman Brothers, Bear Stearns that were constituents during 2010-2020. "
            "This inflates backtest returns by excluding failures."
        ),
        source_fields=SourceFields(
            extra={"bug_type": "survivorship_bias", "list_date": "2026", "backtest_period": "2010-2020"},
        ),
        data_source="manual",
        case_tags=["code_case", "subtle_bug"],
        source_note="Current index constituents for historical backtest",
    ),

    # =========================================================================
    # Case 8: Price filter uses adjusted prices - INVALID
    # =========================================================================
    BenchmarkCase(
        id="code_adjusted_price_filter",
        module=Module.TICKER_TIME_MACHINE,
        difficulty=Difficulty.HARD,
        prompt='''
Audit this penny stock filter:

```python
def filter_penny_stocks(crsp_data, min_price=5.0):
    """
    Remove penny stocks (price < $5) to ensure liquidity.
    Uses split-adjusted prices for consistency.
    """
    # Use adjusted closing price for filter
    crsp_data['adj_prc'] = crsp_data['prc'] / crsp_data['cfacpr']
    
    # Filter out penny stocks
    filtered = crsp_data[crsp_data['adj_prc'] >= min_price]
    
    return filtered
```

This is applied to a backtest from 2000-2020.
''',
        expected_validity=Validity.INVALID,
        expected_violations=[ViolationType.ADJUSTED_PRICE_MISUSE],
        expected_repair=[
            "Split-adjusted prices should not be used for price-level filters.",
            "A stock at $50 in 2000 might show adj_prc of $5 due to later 10:1 split.",
            "Use raw prices (prc) for minimum price eligibility rules."
        ],
        ground_truth_notes=(
            "Adjusted prices back-adjust for splits. A stock trading at $50 in 2000 "
            "that later had a 10:1 split would show adj_prc of $5 for 2000. "
            "Using adjusted prices for a $5 filter incorrectly excludes this stock."
        ),
        source_fields=SourceFields(
            extra={"bug_type": "adjusted_price_for_filter"},
        ),
        data_source="manual",
        case_tags=["code_case", "subtle_bug", "requires_dataset_semantics"],
        source_note="Adjusted prices for price-level filter is wrong",
    ),

    # =========================================================================
    # Case 9: Looks like lookahead but is actually fine - VALID
    # Uses "future" variable name but it's actually lagged
    # =========================================================================
    BenchmarkCase(
        id="code_misleading_varname_valid",
        module=Module.ACCOUNTING_AVAILABILITY,
        difficulty=Difficulty.HARD,
        prompt='''
Audit this earnings surprise calculation:

```python
def calculate_earnings_surprise(ibes_data):
    """Calculate standardized unexpected earnings (SUE)."""
    
    # Sort by firm and announcement date
    ibes_data = ibes_data.sort_values(['ticker', 'anndats'])
    
    # Get the "future" actual EPS (this is what we're predicting)
    # Actually this is the CURRENT quarter's actual, used AFTER announcement
    ibes_data['future_eps'] = ibes_data.groupby('ticker')['actual_eps'].shift(0)
    
    # Get consensus forecast made BEFORE the announcement
    ibes_data['forecast_eps'] = ibes_data.groupby('ticker')['meanest'].shift(1)
    
    # SUE = (Actual - Forecast) / Std Dev of past surprises
    ibes_data['surprise'] = ibes_data['future_eps'] - ibes_data['forecast_eps']
    
    return ibes_data
```

The data is already filtered to only include announcements that have occurred.
''',
        expected_validity=Validity.VALID,
        expected_violations=[],
        expected_repair=[],
        ground_truth_notes=(
            "Despite the variable name 'future_eps', the code is correct. shift(0) just means "
            "current row value. The forecast from shift(1) is from the previous period, "
            "so it WAS available before the current announcement. The 'future' naming is "
            "misleading but the logic is point-in-time valid."
        ),
        source_fields=SourceFields(
            extra={"trap": "misleading variable name"},
        ),
        data_source="manual",
        case_tags=["code_case", "trap_valid", "misleading_language"],
        source_note="Variable name 'future' is misleading but code is correct",
    ),

    # =========================================================================
    # Case 10: Professional docstring, completely wrong implementation
    # INVALID
    # =========================================================================
    BenchmarkCase(
        id="code_professional_but_wrong",
        module=Module.FILING_CLOCK,
        difficulty=Difficulty.HARD,
        prompt='''
Audit this SEC filing processor:

```python
class SECFilingProcessor:
    """
    Process SEC filings with strict point-in-time controls.
    
    This processor ensures that filings are only used after their
    official EDGAR acceptance timestamp. We use the acceptanceDatetime
    field from the EDGAR API to determine exact availability.
    
    Validated against SEC EDGAR documentation and backtested for
    timing accuracy.
    """
    
    def __init__(self, filings_df):
        self.filings = filings_df
    
    def get_available_filings(self, as_of_date):
        """Get filings available as of the given date."""
        # Filter to filings with filing date before as_of_date
        available = self.filings[
            self.filings['filingDate'] <= as_of_date
        ]
        return available
```

Note: filingDate is the calendar date of filing, not the acceptance timestamp.
''',
        expected_validity=Validity.INVALID,
        expected_violations=[ViolationType.FILING_CLOCK_LEAKAGE],
        expected_repair=[
            "The docstring mentions 'acceptanceDatetime' but code uses 'filingDate'.",
            "filingDate is just the calendar date, not the exact acceptance time.",
            "A filing on date X might be accepted at 5 PM - can't trade at 10 AM that day.",
            "Use acceptanceDatetime for intraday timing accuracy."
        ],
        ground_truth_notes=(
            "The docstring is very professional and mentions all the right things "
            "(acceptanceDatetime, EDGAR API, timing accuracy) but the actual code "
            "just uses filingDate which is only the calendar date. This is a "
            "dangerous bug hidden behind impressive documentation."
        ),
        source_fields=SourceFields(
            extra={"bug_type": "docstring_code_mismatch"},
        ),
        data_source="manual",
        case_tags=["code_case", "deceptive_code", "misleading_language"],
        source_note="Professional docstring, wrong implementation",
    ),

    # =========================================================================
    # Case 11: Correct adjusted return for total return calc - VALID
    # =========================================================================
    BenchmarkCase(
        id="code_correct_adj_return_valid",
        module=Module.TICKER_TIME_MACHINE,
        difficulty=Difficulty.HARD,
        prompt='''
Audit this total return calculation:

```python
def calculate_holding_period_return(crsp_data, start_date, end_date, permno):
    """
    Calculate total holding period return including dividends and splits.
    Uses CRSP adjusted prices which account for all distributions.
    """
    stock = crsp_data[crsp_data['permno'] == permno].copy()
    
    start_price = stock[stock['date'] == start_date]['adjprc'].values[0]
    end_price = stock[stock['date'] == end_date]['adjprc'].values[0]
    
    # Total return from adjusted prices
    total_return = (end_price / start_price) - 1
    
    return total_return
```

This is used to calculate historical total shareholder returns for completed periods.
''',
        expected_validity=Validity.VALID,
        expected_violations=[],
        expected_repair=[],
        ground_truth_notes=(
            "This is CORRECT usage of adjusted prices. For calculating total returns "
            "(including dividends and splits), adjusted prices are exactly right. "
            "The ratio of adjusted prices gives total return. This is different from "
            "using adjusted prices for price filters (which is wrong)."
        ),
        source_fields=SourceFields(
            extra={"correct_use": "total return calculation"},
        ),
        data_source="manual",
        case_tags=["code_case", "trap_valid", "requires_dataset_semantics"],
        source_note="Correct use of adjusted prices for returns",
    ),

    # =========================================================================
    # Case 12: Industry classification from current download - INVALID
    # =========================================================================
    BenchmarkCase(
        id="code_current_industry_codes",
        module=Module.SURVIVORSHIP_DELISTING,
        difficulty=Difficulty.HARD,
        prompt='''
Audit this industry-neutral portfolio construction:

```python
# Downloaded from Compustat in 2026
industry_codes = pd.read_csv('compustat_company_info.csv')[['gvkey', 'sic', 'naics']]

def build_industry_neutral_portfolio(stock_signals, formation_date):
    """
    Build industry-neutral portfolio by selecting top stocks within each industry.
    """
    # Merge signals with industry codes
    stocks = stock_signals.merge(industry_codes, on='gvkey')
    
    # Within each industry, select top 20% by signal
    def top_quintile(group):
        threshold = group['signal'].quantile(0.8)
        return group[group['signal'] >= threshold]
    
    portfolio = stocks.groupby('sic').apply(top_quintile)
    
    return portfolio

# Run backtest
for date in pd.date_range('2000-01-01', '2020-12-31', freq='M'):
    portfolio = build_industry_neutral_portfolio(signals, date)
```
''',
        expected_validity=Validity.INVALID,
        expected_violations=[ViolationType.CURRENT_METADATA_LEAKAGE],
        expected_repair=[
            "Uses 2026 industry codes for a 2000-2020 backtest.",
            "Companies change industries over time (e.g., Amazon from retail to tech).",
            "Use historical industry classifications valid at each formation date."
        ],
        ground_truth_notes=(
            "Industry classifications change over time. A company classified as "
            "'Technology' in 2026 might have been 'Retail' in 2000. Using current "
            "classifications for historical backtests biases industry-neutral construction."
        ),
        source_fields=SourceFields(
            extra={"bug_type": "current_metadata_for_historical"},
        ),
        data_source="manual",
        case_tags=["code_case", "subtle_bug"],
        source_note="Current industry codes for historical backtest",
    ),
]


def get_code_cases() -> list[BenchmarkCase]:
    """Return all code-based test cases."""
    return CODE_CASES


def get_case_ids() -> list[str]:
    """Return all code case IDs."""
    return [case.id for case in CODE_CASES]


def print_code_cases_summary():
    """Print summary of code cases."""
    print("=" * 70)
    print("CODE-BASED BENCHMARK CASES SUMMARY")
    print("=" * 70)
    
    valid_count = len([c for c in CODE_CASES if c.expected_validity == Validity.VALID])
    invalid_count = len([c for c in CODE_CASES if c.expected_validity == Validity.INVALID])
    
    print(f"\nTotal cases: {len(CODE_CASES)}")
    print(f"  Valid (trap cases): {valid_count}")
    print(f"  Invalid (bugs): {invalid_count}")
    
    print(f"\nCases:")
    for case in CODE_CASES:
        status = "[VALID]" if case.expected_validity == Validity.VALID else "[BUG]"
        tags = ", ".join(case.case_tags[:2])
        print(f"  {status:8} {case.id}: {tags}")
    
    print("=" * 70)


if __name__ == "__main__":
    print_code_cases_summary()
