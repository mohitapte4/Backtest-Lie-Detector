"""
Seed benchmark cases for the Backtest Lie Detector.

These are manually curated, high-quality cases that serve as the foundation
of the benchmark. Each case has been verified for ground truth accuracy.
"""

from backtest_lie_detector.schemas import (
    BenchmarkCase,
    Difficulty,
    Module,
    SourceFields,
    Validity,
    ViolationType,
)

# =============================================================================
# Module 1: Ticker Time Machine
# =============================================================================

TTM_META_2018 = BenchmarkCase(
    id="ttm_meta_2018_cambridge",
    module=Module.TICKER_TIME_MACHINE,
    difficulty=Difficulty.EASY,
    prompt=(
        "A researcher studies the Cambridge Analytica event on 2018-03-20 and queries "
        "daily returns using ticker META. Audit this workflow. Is it point-in-time valid? "
        "If not, identify the issue and propose a repair."
    ),
    expected_validity=Validity.INVALID,
    expected_violations=[ViolationType.IDENTIFIER_TIME_TRAVEL],
    expected_repair=[
        "Use the historical ticker valid on 2018-03-20, not the modern ticker.",
        "The correct ticker was FB on 2018-03-20.",
        "Resolve the security using a point-in-time identifier such as CRSP PERMNO."
    ],
    ground_truth_notes=(
        "Meta Platforms did not trade under ticker META on 2018-03-20. "
        "The company was still Facebook Inc. trading under ticker FB. "
        "META became the ticker on June 9, 2022, after the corporate rebrand."
    ),
    source_fields=SourceFields(
        company="Meta Platforms / Facebook",
        event_date="2018-03-20",
        bad_ticker="META",
        historical_ticker="FB",
    ),
    requires_data_validation=False,
    data_source="manual"
)

TTM_GOOGLE_SHARE_CLASS = BenchmarkCase(
    id="ttm_google_share_class_2014",
    module=Module.TICKER_TIME_MACHINE,
    difficulty=Difficulty.MEDIUM,
    prompt=(
        "A researcher studies Google's stock split announcement on April 2, 2014 and "
        "queries returns using ticker GOOGL. The researcher uses GOOGL throughout their "
        "backtest from 2010 to 2020. Audit this workflow for point-in-time validity."
    ),
    expected_validity=Validity.INVALID,
    expected_violations=[
        ViolationType.IDENTIFIER_TIME_TRAVEL,
        ViolationType.ISSUER_SECURITY_CONFUSION
    ],
    expected_repair=[
        "GOOGL (Class A) and GOOG (Class C) were created in April 2014 stock split.",
        "Before April 2014, only GOOG existed as a single share class.",
        "Use GOOG for pre-split period and clarify which share class is intended post-split.",
        "Consider using CRSP PERMNO to track the security consistently."
    ],
    ground_truth_notes=(
        "Google's Class A (GOOGL) and Class C (GOOG) share structure was created "
        "in the April 2014 stock split. Before this, there was only one ticker: GOOG. "
        "Using GOOGL before April 2014 would fail to retrieve data."
    ),
    source_fields=SourceFields(
        company="Alphabet Inc. / Google",
        event_date="2014-04-02",
        ticker="GOOGL",
        extra={
            "split_date": "2014-04-03",
            "pre_split_ticker": "GOOG",
            "class_a_ticker": "GOOGL",
            "class_c_ticker": "GOOG"
        }
    ),
    requires_data_validation=False,
    data_source="manual"
)

TTM_ATT_TICKER_REUSE = BenchmarkCase(
    id="ttm_att_ticker_reuse",
    module=Module.TICKER_TIME_MACHINE,
    difficulty=Difficulty.HARD,
    prompt=(
        "A researcher analyzes returns for telecommunications companies using ticker 'T' "
        "from 1980 to 2020. They assume 'T' consistently refers to AT&T throughout. "
        "Audit this workflow for point-in-time validity."
    ),
    expected_validity=Validity.INVALID,
    expected_violations=[
        ViolationType.IDENTIFIER_TIME_TRAVEL,
        ViolationType.ISSUER_SECURITY_CONFUSION
    ],
    expected_repair=[
        "Use CRSP PERMNO or CUSIP to track AT&T across corporate restructurings.",
        "The original AT&T (Ma Bell) was broken up in 1984.",
        "The current AT&T Inc. (ticker T) is the result of SBC acquiring AT&T in 2005.",
        "Track the specific legal entity and security through each corporate action."
    ],
    ground_truth_notes=(
        "The ticker 'T' has a complex history. The original AT&T was broken up in 1984. "
        "SBC Communications acquired AT&T Corp in 2005 and adopted the AT&T name and ticker. "
        "Simply using ticker 'T' assumes continuity that doesn't exist at the issuer level."
    ),
    source_fields=SourceFields(
        company="AT&T Inc.",
        ticker="T",
        backtest_start="1980-01-01",
        backtest_end="2020-12-31",
        extra={
            "breakup_date": "1984-01-01",
            "sbc_merger_date": "2005-11-18"
        }
    ),
    requires_data_validation=False,
    data_source="manual"
)

# =============================================================================
# Module 2: Filing Clock Challenge
# =============================================================================

FILING_CLOCK_AFTER_CLOSE = BenchmarkCase(
    id="filing_clock_after_close_8k",
    module=Module.FILING_CLOCK,
    difficulty=Difficulty.EASY,
    prompt=(
        "A strategy trades at 3:55 PM ET on 2021-05-03 using information from an 8-K "
        "accepted by EDGAR at 4:07 PM ET on the same day. Audit this workflow. Is it valid?"
    ),
    expected_validity=Validity.INVALID,
    expected_violations=[ViolationType.FILING_CLOCK_LEAKAGE],
    expected_repair=[
        "Do not use the 8-K for a decision timestamp before the EDGAR acceptance time.",
        "Move the trade decision to after the filing was available.",
        "Alternatively, move the trade to the next trading session."
    ],
    ground_truth_notes=(
        "The filing was accepted at 4:07 PM ET, but the trading decision was made at "
        "3:55 PM ET. The information in the 8-K was not available at decision time."
    ),
    source_fields=SourceFields(
        decision_timestamp="2021-05-03 15:55:00 America/New_York",
        filing_timestamp="2021-05-03 16:07:00 America/New_York",
        extra={"filing_type": "8-K"}
    ),
    requires_data_validation=False,
    data_source="manual"
)

FILING_CLOCK_WEEKEND = BenchmarkCase(
    id="filing_clock_weekend_10k",
    module=Module.FILING_CLOCK,
    difficulty=Difficulty.MEDIUM,
    prompt=(
        "A company files its 10-K on Saturday, March 12, 2022 at 2:30 PM ET. "
        "A trading strategy uses information from this 10-K to trade at market open "
        "on Monday, March 14, 2022 at 9:30 AM ET. Audit this workflow."
    ),
    expected_validity=Validity.VALID,
    expected_violations=[],
    expected_repair=[],
    ground_truth_notes=(
        "The 10-K was filed on Saturday and the trade occurs at Monday market open. "
        "The filing was available for over 40 hours before the trade. This is valid."
    ),
    source_fields=SourceFields(
        decision_timestamp="2022-03-14 09:30:00 America/New_York",
        filing_timestamp="2022-03-12 14:30:00 America/New_York",
        extra={"filing_type": "10-K"}
    ),
    requires_data_validation=False,
    data_source="manual"
)

FILING_CLOCK_PREMARKET = BenchmarkCase(
    id="filing_clock_premarket_earnings",
    module=Module.FILING_CLOCK,
    difficulty=Difficulty.MEDIUM,
    prompt=(
        "A company releases earnings via 8-K filed at 7:15 AM ET on 2023-02-15. "
        "A trading strategy uses this earnings information to trade at 9:31 AM ET "
        "the same day. Is this workflow point-in-time valid?"
    ),
    expected_validity=Validity.VALID,
    expected_violations=[],
    expected_repair=[],
    ground_truth_notes=(
        "The 8-K was filed at 7:15 AM ET, over 2 hours before the trade at 9:31 AM ET. "
        "The information was publicly available before market open. This is valid."
    ),
    source_fields=SourceFields(
        decision_timestamp="2023-02-15 09:31:00 America/New_York",
        filing_timestamp="2023-02-15 07:15:00 America/New_York",
        extra={"filing_type": "8-K", "content": "earnings"}
    ),
    requires_data_validation=False,
    data_source="manual"
)

# =============================================================================
# Module 3: Accounting Availability Trap
# =============================================================================

ACCOUNTING_FY_VS_FILING = BenchmarkCase(
    id="acct_fy_end_vs_filing_date",
    module=Module.ACCOUNTING_AVAILABILITY,
    difficulty=Difficulty.EASY,
    prompt=(
        "A portfolio is formed on 2023-01-15 using fiscal-year 2022 net income from "
        "Compustat. The company's fiscal year ended on 2022-12-31, but the 10-K was "
        "filed on 2023-02-20. Audit this workflow."
    ),
    expected_validity=Validity.INVALID,
    expected_violations=[ViolationType.ACCOUNTING_AVAILABILITY_LEAKAGE],
    expected_repair=[
        "Do not treat fiscal year end as the information availability date.",
        "Use only accounting variables from filings available before portfolio formation.",
        "Use the most recent available annual data (FY2021) or quarterly data."
    ],
    ground_truth_notes=(
        "The 2022 annual data was not publicly available on 2023-01-15. "
        "The 10-K containing this data was not filed until 2023-02-20. "
        "Using FY2022 data on 2023-01-15 is look-ahead bias."
    ),
    source_fields=SourceFields(
        portfolio_date="2023-01-15",
        fiscal_year_end="2022-12-31",
        filing_date="2023-02-20",
    ),
    requires_data_validation=False,
    data_source="manual"
)

ACCOUNTING_QUARTERLY_LAG = BenchmarkCase(
    id="acct_quarterly_availability",
    module=Module.ACCOUNTING_AVAILABILITY,
    difficulty=Difficulty.MEDIUM,
    prompt=(
        "A strategy forms portfolios on the first trading day of each month using "
        "the most recent quarterly earnings. In April 2023, it uses Q1 2023 earnings "
        "which were reported on April 25, 2023. The portfolio was formed on April 3, 2023. "
        "Audit this workflow."
    ),
    expected_validity=Validity.INVALID,
    expected_violations=[ViolationType.ACCOUNTING_AVAILABILITY_LEAKAGE],
    expected_repair=[
        "Use only earnings data from reports filed before portfolio formation.",
        "On April 3, 2023, the most recent available data would be Q4 2022.",
        "Implement a proper lag in the data pipeline."
    ],
    ground_truth_notes=(
        "Q1 2023 ended on March 31, 2023, but the earnings were not reported until "
        "April 25, 2023. Using Q1 2023 data on April 3, 2023 is look-ahead bias."
    ),
    source_fields=SourceFields(
        portfolio_date="2023-04-03",
        fiscal_year_end="2023-03-31",
        filing_date="2023-04-25",
        extra={"quarter": "Q1 2023"}
    ),
    requires_data_validation=False,
    data_source="manual"
)

ACCOUNTING_RESTATEMENT = BenchmarkCase(
    id="acct_restatement_leakage",
    module=Module.ACCOUNTING_AVAILABILITY,
    difficulty=Difficulty.HARD,
    prompt=(
        "A researcher backtests a strategy using Compustat data from 2005-2015. "
        "In 2012, Company XYZ restated its 2010 financials due to an accounting error. "
        "The backtest uses the restated 2010 values for portfolio formation in January 2011. "
        "Audit this workflow."
    ),
    expected_validity=Validity.INVALID,
    expected_violations=[ViolationType.RESTATEMENT_LEAKAGE],
    expected_repair=[
        "Use point-in-time data that reflects what was known at each historical date.",
        "The restated values from 2012 were not available in January 2011.",
        "Use Compustat point-in-time snapshots or the originally reported values."
    ],
    ground_truth_notes=(
        "Restated financials incorporate corrections made after the original filing. "
        "Using restated 2010 values in 2011 is look-ahead bias because the restatement "
        "did not occur until 2012."
    ),
    source_fields=SourceFields(
        company="Company XYZ (hypothetical)",
        portfolio_date="2011-01-15",
        extra={
            "original_filing_date": "2011-02-28",
            "restatement_date": "2012-03-15",
            "fiscal_year": "2010"
        }
    ),
    requires_data_validation=False,
    data_source="manual"
)

# =============================================================================
# Module 4: Survivorship and Delisting Trap
# =============================================================================

SURVIVORSHIP_CURRENT_UNIVERSE = BenchmarkCase(
    id="survivorship_current_universe_2000_2020",
    module=Module.SURVIVORSHIP_DELISTING,
    difficulty=Difficulty.EASY,
    prompt=(
        "A backtest from 2000 to 2020 uses only companies that are still listed in 2026. "
        "It excludes companies that delisted or merged before 2026. Audit this workflow."
    ),
    expected_validity=Validity.INVALID,
    expected_violations=[
        ViolationType.SURVIVORSHIP_BIAS,
        ViolationType.DELISTING_RETURN_OMISSION
    ],
    expected_repair=[
        "Construct the investable universe point-in-time.",
        "Include firms that existed during the backtest even if they later delisted.",
        "Handle delisting returns where applicable.",
        "Use CRSP universe flags to identify tradeable securities at each point."
    ],
    ground_truth_notes=(
        "Using only firms alive in 2026 introduces survivorship bias. "
        "The backtest excludes companies like Lehman Brothers, Enron, and thousands "
        "of other firms that existed during 2000-2020 but no longer trade."
    ),
    source_fields=SourceFields(
        backtest_start="2000-01-01",
        backtest_end="2020-12-31",
        universe_filter="still listed in 2026"
    ),
    requires_data_validation=False,
    data_source="manual"
)

SURVIVORSHIP_DELISTING_RETURNS = BenchmarkCase(
    id="survivorship_delisting_returns_missing",
    module=Module.SURVIVORSHIP_DELISTING,
    difficulty=Difficulty.MEDIUM,
    prompt=(
        "A momentum strategy backtest from 2000-2010 uses CRSP daily returns. "
        "When a stock delists, the strategy simply drops the stock from the portfolio "
        "on the last trading day and ignores any delisting return. Audit this workflow."
    ),
    expected_validity=Validity.INVALID,
    expected_violations=[ViolationType.DELISTING_RETURN_OMISSION],
    expected_repair=[
        "Include CRSP delisting returns (DLRET) when stocks delist.",
        "For performance-related delistings, apply appropriate delisting return assumptions.",
        "Document the treatment of different delisting codes."
    ],
    ground_truth_notes=(
        "CRSP provides delisting returns that capture the final return when a stock "
        "stops trading. Ignoring these returns, especially for distressed delistings, "
        "biases performance upward by missing large negative final returns."
    ),
    source_fields=SourceFields(
        backtest_start="2000-01-01",
        backtest_end="2010-12-31",
        extra={"strategy_type": "momentum"}
    ),
    requires_data_validation=False,
    data_source="manual"
)

SURVIVORSHIP_SP500_CONSTITUENTS = BenchmarkCase(
    id="survivorship_sp500_historical",
    module=Module.SURVIVORSHIP_DELISTING,
    difficulty=Difficulty.MEDIUM,
    prompt=(
        "A researcher backtests a value strategy on S&P 500 stocks from 1990 to 2020 "
        "using the current (2026) S&P 500 constituent list. Audit this workflow."
    ),
    expected_validity=Validity.INVALID,
    expected_violations=[ViolationType.SURVIVORSHIP_BIAS],
    expected_repair=[
        "Use historical S&P 500 constituent lists as of each rebalance date.",
        "Account for index additions and deletions over time.",
        "Consider using CRSP/Compustat merged with historical index membership data."
    ],
    ground_truth_notes=(
        "The S&P 500 composition changes frequently. Using current constituents "
        "for historical analysis excludes companies that were in the index but later "
        "removed (often due to poor performance, mergers, or bankruptcies)."
    ),
    source_fields=SourceFields(
        backtest_start="1990-01-01",
        backtest_end="2020-12-31",
        universe_filter="current S&P 500 constituents",
        extra={"index": "S&P 500"}
    ),
    requires_data_validation=False,
    data_source="manual"
)

# =============================================================================
# Valid Control Cases (important for calibration)
# =============================================================================

VALID_HISTORICAL_TICKER = BenchmarkCase(
    id="valid_historical_ticker_apple",
    module=Module.TICKER_TIME_MACHINE,
    difficulty=Difficulty.EASY,
    prompt=(
        "A researcher studies Apple's iPhone announcement on January 9, 2007 and "
        "queries daily returns using ticker AAPL. Audit this workflow."
    ),
    expected_validity=Validity.VALID,
    expected_violations=[],
    expected_repair=[],
    ground_truth_notes=(
        "Apple Inc. has traded under ticker AAPL continuously since going public in 1980. "
        "Using AAPL for the 2007 iPhone event is point-in-time valid."
    ),
    source_fields=SourceFields(
        company="Apple Inc.",
        event_date="2007-01-09",
        ticker="AAPL"
    ),
    requires_data_validation=False,
    data_source="manual"
)

VALID_LAGGED_ACCOUNTING = BenchmarkCase(
    id="valid_lagged_accounting_data",
    module=Module.ACCOUNTING_AVAILABILITY,
    difficulty=Difficulty.EASY,
    prompt=(
        "A portfolio is formed on 2023-04-01 using fiscal-year 2022 data. "
        "The company filed its 10-K on 2023-02-25. Audit this workflow."
    ),
    expected_validity=Validity.VALID,
    expected_violations=[],
    expected_repair=[],
    ground_truth_notes=(
        "The 10-K was filed on February 25, 2023, over a month before the "
        "portfolio formation date of April 1, 2023. The data was publicly available."
    ),
    source_fields=SourceFields(
        portfolio_date="2023-04-01",
        fiscal_year_end="2022-12-31",
        filing_date="2023-02-25"
    ),
    requires_data_validation=False,
    data_source="manual"
)

# =============================================================================
# Collect all seed cases
# =============================================================================

SEED_CASES: list[BenchmarkCase] = [
    # Ticker Time Machine (3 cases)
    TTM_META_2018,
    TTM_GOOGLE_SHARE_CLASS,
    TTM_ATT_TICKER_REUSE,
    # Filing Clock (3 cases)
    FILING_CLOCK_AFTER_CLOSE,
    FILING_CLOCK_WEEKEND,
    FILING_CLOCK_PREMARKET,
    # Accounting Availability (3 cases)
    ACCOUNTING_FY_VS_FILING,
    ACCOUNTING_QUARTERLY_LAG,
    ACCOUNTING_RESTATEMENT,
    # Survivorship/Delisting (3 cases)
    SURVIVORSHIP_CURRENT_UNIVERSE,
    SURVIVORSHIP_DELISTING_RETURNS,
    SURVIVORSHIP_SP500_CONSTITUENTS,
    # Valid controls (2 cases)
    VALID_HISTORICAL_TICKER,
    VALID_LAGGED_ACCOUNTING,
]


def get_seed_cases_by_module(module: Module) -> list[BenchmarkCase]:
    """Get all seed cases for a specific module."""
    return [case for case in SEED_CASES if case.module == module]


def get_seed_cases_by_difficulty(difficulty: Difficulty) -> list[BenchmarkCase]:
    """Get all seed cases of a specific difficulty."""
    return [case for case in SEED_CASES if case.difficulty == difficulty]
