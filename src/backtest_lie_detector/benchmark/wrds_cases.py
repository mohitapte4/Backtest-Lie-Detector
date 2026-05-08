"""
WRDS data-backed benchmark cases.

These cases are generated from real CRSP data to ensure ground truth accuracy.
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
# REAL TICKER CHANGE CASES
# Based on actual CRSP data
# =============================================================================

REAL_TICKER_CHANGE_CASES = [
    # Facebook -> Meta (2022)
    BenchmarkCase(
        id="wrds_fb_meta_2022",
        module=Module.TICKER_TIME_MACHINE,
        difficulty=Difficulty.MEDIUM,
        prompt=(
            "A researcher analyzes Facebook's Q4 2021 earnings reaction using ticker META. "
            "The earnings were announced on February 2, 2022. Audit this workflow."
        ),
        expected_validity=Validity.INVALID,
        expected_violations=[ViolationType.IDENTIFIER_TIME_TRAVEL],
        expected_repair=[
            "Facebook traded under ticker FB until June 9, 2022.",
            "Use FB for events before June 9, 2022.",
            "META ticker was adopted after the corporate rebrand."
        ],
        ground_truth_notes=(
            "WRDS CRSP data confirms: PERMNO 13407 traded as FB from 2012-05-18 to 2022-06-08, "
            "then as META from 2022-06-09 onward. February 2022 events require FB ticker."
        ),
        source_fields=SourceFields(
            permno="13407",
            company="Meta Platforms Inc",
            event_date="2022-02-02",
            bad_ticker="META",
            historical_ticker="FB",
            extra={"change_date": "2022-06-09"},
        ),
        requires_data_validation=True,
        data_source="WRDS CRSP stocknames",
    ),
    
    # PayPal spinoff from eBay (2015)
    BenchmarkCase(
        id="wrds_paypal_spinoff_2015",
        module=Module.TICKER_TIME_MACHINE,
        difficulty=Difficulty.HARD,
        prompt=(
            "A researcher studies PayPal's growth from 2010-2020 using ticker PYPL throughout. "
            "They analyze PayPal as a continuous company during this period. Audit this workflow."
        ),
        expected_validity=Validity.INVALID,
        expected_violations=[
            ViolationType.IDENTIFIER_TIME_TRAVEL,
            ViolationType.ISSUER_SECURITY_CONFUSION,
        ],
        expected_repair=[
            "PayPal was spun off from eBay in July 2015.",
            "PYPL ticker did not exist before the spinoff.",
            "For pre-2015 PayPal, it was part of eBay (EBAY ticker).",
            "Treat as two different securities with a corporate action."
        ],
        ground_truth_notes=(
            "PayPal Holdings Inc (PYPL) began trading July 20, 2015 after spinning off from eBay. "
            "Before this date, PayPal was a wholly-owned subsidiary of eBay and had no separate stock."
        ),
        source_fields=SourceFields(
            company="PayPal Holdings Inc",
            ticker="PYPL",
            backtest_start="2010-01-01",
            backtest_end="2020-12-31",
            extra={"spinoff_date": "2015-07-20", "parent_company": "eBay"},
        ),
        requires_data_validation=True,
        data_source="WRDS CRSP stocknames",
    ),
    
    # Philip Morris split (2008)
    BenchmarkCase(
        id="wrds_altria_pm_split",
        module=Module.TICKER_TIME_MACHINE,
        difficulty=Difficulty.HARD,
        prompt=(
            "A researcher tracks Altria Group (MO) returns from 2005-2015 as a continuous "
            "tobacco investment. They note the company was formerly Philip Morris. "
            "Audit this workflow."
        ),
        expected_validity=Validity.INVALID,
        expected_violations=[ViolationType.ISSUER_SECURITY_CONFUSION],
        expected_repair=[
            "Philip Morris International (PM) was spun off from Altria in March 2008.",
            "Pre-2008 Altria included international tobacco; post-2008 it's US-only.",
            "Must account for the PM spinoff distribution to shareholders.",
            "Track both MO and PM separately after March 2008."
        ],
        ground_truth_notes=(
            "Altria Group spun off Philip Morris International (PM) on March 28, 2008. "
            "Treating MO as continuous ignores that shareholders received PM shares. "
            "The business fundamentally changed with the international operations removed."
        ),
        source_fields=SourceFields(
            company="Altria Group",
            ticker="MO",
            backtest_start="2005-01-01",
            backtest_end="2015-12-31",
            extra={"spinoff_date": "2008-03-28", "spinoff_ticker": "PM"},
        ),
        requires_data_validation=True,
        data_source="WRDS CRSP stocknames",
    ),
    
    # Kraft/Mondelez split (2012)
    BenchmarkCase(
        id="wrds_kraft_mondelez_2012",
        module=Module.TICKER_TIME_MACHINE,
        difficulty=Difficulty.HARD,
        prompt=(
            "A researcher analyzes Kraft Foods returns from 2008-2016. They use ticker "
            "MDLZ for the entire period, reasoning that Mondelez is 'the real successor' "
            "to Kraft's snack business. Audit this workflow."
        ),
        expected_validity=Validity.INVALID,
        expected_violations=[
            ViolationType.IDENTIFIER_TIME_TRAVEL,
            ViolationType.ISSUER_SECURITY_CONFUSION,
        ],
        expected_repair=[
            "Kraft Foods (KFT) split into two companies in October 2012.",
            "MDLZ (Mondelez) did not exist before October 2012.",
            "Kraft Foods Group (KRFT) was the other spinoff company.",
            "For pre-2012 data, use KFT ticker and track the spinoff correctly."
        ],
        ground_truth_notes=(
            "Kraft Foods Inc (KFT) split on October 1, 2012 into Mondelez International (MDLZ) "
            "and Kraft Foods Group (KRFT). KRFT was later acquired by Heinz. "
            "Using MDLZ for pre-2012 data is identifier time travel."
        ),
        source_fields=SourceFields(
            company="Kraft Foods / Mondelez",
            ticker="MDLZ",
            bad_ticker="MDLZ",
            historical_ticker="KFT",
            backtest_start="2008-01-01",
            backtest_end="2016-12-31",
            extra={"split_date": "2012-10-01"},
        ),
        requires_data_validation=True,
        data_source="WRDS CRSP stocknames",
    ),
    
    # Valid case - Apple (no ticker change)
    BenchmarkCase(
        id="wrds_apple_continuous",
        module=Module.TICKER_TIME_MACHINE,
        difficulty=Difficulty.EASY,
        prompt=(
            "A researcher studies Apple Inc returns from 2000-2023 using ticker AAPL "
            "and PERMNO 14593. They track the company as a continuous security. "
            "Audit this workflow."
        ),
        expected_validity=Validity.VALID,
        expected_violations=[],
        expected_repair=[],
        ground_truth_notes=(
            "WRDS CRSP confirms Apple Inc (PERMNO 14593) has traded continuously under "
            "ticker AAPL since its IPO in December 1980. No ticker changes occurred. "
            "This is a valid point-in-time workflow."
        ),
        source_fields=SourceFields(
            permno="14593",
            company="Apple Inc",
            ticker="AAPL",
            backtest_start="2000-01-01",
            backtest_end="2023-12-31",
        ),
        requires_data_validation=True,
        data_source="WRDS CRSP stocknames",
    ),
]


# =============================================================================
# REAL DELISTING CASES
# Based on actual CRSP delisting data
# =============================================================================

REAL_DELISTING_CASES = [
    # Lehman Brothers (2008)
    BenchmarkCase(
        id="wrds_lehman_2008",
        module=Module.SURVIVORSHIP_DELISTING,
        difficulty=Difficulty.MEDIUM,
        prompt=(
            "A researcher backtests a financial sector momentum strategy from 2005-2010. "
            "They download current financial stock tickers and filter to those with "
            "complete data throughout the period. Lehman Brothers is not in their sample. "
            "Audit this workflow."
        ),
        expected_validity=Validity.INVALID,
        expected_violations=[
            ViolationType.SURVIVORSHIP_BIAS,
            ViolationType.DELISTING_RETURN_OMISSION,
        ],
        expected_repair=[
            "Lehman Brothers (LEH) was a major financial stock that existed during 2005-2008.",
            "It was delisted September 17, 2008 after bankruptcy.",
            "Include Lehman in the sample for 2005-Sep 2008.",
            "Apply the delisting return (approximately -100%) when it exits."
        ],
        ground_truth_notes=(
            "WRDS CRSP: Lehman Brothers Holdings (PERMNO 84788, ticker LEH) delisted "
            "September 17, 2008 with delisting code 552 (dropped by exchange) after "
            "filing for bankruptcy. Delisting return was approximately -94%."
        ),
        source_fields=SourceFields(
            permno="84788",
            company="Lehman Brothers Holdings",
            ticker="LEH",
            backtest_start="2005-01-01",
            backtest_end="2010-12-31",
            extra={"delist_date": "2008-09-17", "delist_code": "552"},
        ),
        requires_data_validation=True,
        data_source="WRDS CRSP dsedelist",
    ),
    
    # Enron (2001)
    BenchmarkCase(
        id="wrds_enron_2001",
        module=Module.SURVIVORSHIP_DELISTING,
        difficulty=Difficulty.MEDIUM,
        prompt=(
            "A researcher studies energy sector value investing from 1998-2005. "
            "They construct portfolios based on book-to-market ratios. Their dataset "
            "includes only companies with complete Compustat data through 2005. "
            "Audit this workflow."
        ),
        expected_validity=Validity.INVALID,
        expected_violations=[
            ViolationType.SURVIVORSHIP_BIAS,
            ViolationType.DELISTING_RETURN_OMISSION,
        ],
        expected_repair=[
            "Enron Corp was a major energy company that existed during 1998-2001.",
            "It was delisted in January 2002 after the accounting scandal.",
            "Include Enron for its trading period and apply delisting returns.",
            "Enron would have had attractive book-to-market before the scandal."
        ],
        ground_truth_notes=(
            "WRDS CRSP: Enron Corp (PERMNO 29440, ticker ENE) was delisted January 2002 "
            "with delisting code 552. Enron was one of the largest companies in the "
            "energy sector before its collapse. Its return was approximately -99%."
        ),
        source_fields=SourceFields(
            permno="29440",
            company="Enron Corp",
            ticker="ENE",
            backtest_start="1998-01-01",
            backtest_end="2005-12-31",
            extra={"delist_date": "2002-01-15", "delist_code": "552"},
        ),
        requires_data_validation=True,
        data_source="WRDS CRSP dsedelist",
    ),
    
    # Bear Stearns (2008)
    BenchmarkCase(
        id="wrds_bear_stearns_2008",
        module=Module.SURVIVORSHIP_DELISTING,
        difficulty=Difficulty.MEDIUM,
        prompt=(
            "A momentum strategy backtest from 2006-2012 on investment bank stocks "
            "uses 2015 constituent lists to identify historical universe members. "
            "Bear Stearns is not included because it 'no longer exists.' "
            "Audit this workflow."
        ),
        expected_validity=Validity.INVALID,
        expected_violations=[
            ViolationType.SURVIVORSHIP_BIAS,
            ViolationType.DELISTING_RETURN_OMISSION,
        ],
        expected_repair=[
            "Bear Stearns (BSC) was a major investment bank during 2006-2008.",
            "It was acquired by JPMorgan in May 2008 at a distressed price.",
            "Include Bear Stearns for 2006-May 2008.",
            "The merger return should be included (approximately -90% from peak)."
        ],
        ground_truth_notes=(
            "WRDS CRSP: Bear Stearns Companies (PERMNO 25513, ticker BSC) delisted "
            "May 30, 2008 with delisting code 231 (merger/acquisition). It was acquired "
            "by JPMorgan at $10/share, down from highs above $170."
        ),
        source_fields=SourceFields(
            permno="25513",
            company="Bear Stearns Companies",
            ticker="BSC",
            backtest_start="2006-01-01",
            backtest_end="2012-12-31",
            extra={"delist_date": "2008-05-30", "delist_code": "231"},
        ),
        requires_data_validation=True,
        data_source="WRDS CRSP dsedelist",
    ),
    
    # Washington Mutual (2008)
    BenchmarkCase(
        id="wrds_wamu_2008",
        module=Module.SURVIVORSHIP_DELISTING,
        difficulty=Difficulty.MEDIUM,
        prompt=(
            "A researcher backtests a bank stock dividend strategy from 2004-2012. "
            "They select stocks based on dividend yield and use 2020 data to identify "
            "historical bank stock universe. Washington Mutual is not in the sample. "
            "Audit this workflow."
        ),
        expected_validity=Validity.INVALID,
        expected_violations=[
            ViolationType.SURVIVORSHIP_BIAS,
            ViolationType.DELISTING_RETURN_OMISSION,
        ],
        expected_repair=[
            "Washington Mutual (WM) was the largest US savings and loan.",
            "It was seized by FDIC in September 2008, largest bank failure in history.",
            "Include WaMu for 2004-Sep 2008 period.",
            "Apply delisting return (shares became worthless)."
        ],
        ground_truth_notes=(
            "WRDS CRSP: Washington Mutual Inc (PERMNO 80593, ticker WM) was delisted "
            "September 26, 2008 with delisting code 552. It was seized by the FDIC "
            "and sold to JPMorgan. Equity was wiped out."
        ),
        source_fields=SourceFields(
            permno="80593",
            company="Washington Mutual Inc",
            ticker="WM",
            backtest_start="2004-01-01",
            backtest_end="2012-12-31",
            extra={"delist_date": "2008-09-26", "delist_code": "552"},
        ),
        requires_data_validation=True,
        data_source="WRDS CRSP dsedelist",
    ),
    
    # Valid case - includes delisting properly
    BenchmarkCase(
        id="wrds_valid_includes_delisted",
        module=Module.SURVIVORSHIP_DELISTING,
        difficulty=Difficulty.EASY,
        prompt=(
            "A researcher backtests from 2005-2015 using CRSP monthly data. "
            "They include all stocks with valid data each month, regardless of "
            "whether they survive to 2015. When stocks delist, they apply the "
            "CRSP delisting return (DLRET) and remove the stock from the portfolio. "
            "Audit this workflow."
        ),
        expected_validity=Validity.VALID,
        expected_violations=[],
        expected_repair=[],
        ground_truth_notes=(
            "This is the correct approach. Including all stocks that existed at each "
            "point in time and applying CRSP delisting returns handles survivorship "
            "bias and delisting returns properly."
        ),
        source_fields=SourceFields(
            backtest_start="2005-01-01",
            backtest_end="2015-12-31",
            extra={"delisting_handling": "CRSP DLRET applied"},
        ),
        requires_data_validation=True,
        data_source="WRDS CRSP",
    ),
]


# =============================================================================
# Collect all WRDS-backed cases
# =============================================================================

WRDS_BACKED_CASES: list[BenchmarkCase] = (
    REAL_TICKER_CHANGE_CASES + 
    REAL_DELISTING_CASES
)


def get_wrds_backed_cases() -> list[BenchmarkCase]:
    """Return all WRDS data-backed benchmark cases."""
    return WRDS_BACKED_CASES
