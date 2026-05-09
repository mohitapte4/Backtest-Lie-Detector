"""
Calibration-focused benchmark cases for V4.

These cases test whether models can avoid overcaution and express uncertainty:
1. Valid Trap Cases (8): Look suspicious but are actually correct
2. Ambiguous Cases (8): Correct answer is "needs more information"
3. Hard Invalid Cases (4): Subtle but real violations

Purpose: Test calibration - can models distinguish truly invalid workflows
from valid-but-suspicious ones, and express uncertainty when appropriate?
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
# VALID TRAP CASES (8)
# These look suspicious but are actually correct - test overcaution
# =============================================================================

VALID_TRAP_CASES = [
    BenchmarkCase(
        id="cal_valid_crsp_adjusted_return",
        module=Module.TICKER_TIME_MACHINE,
        difficulty=Difficulty.HARD,
        prompt=(
            "A researcher calculates long-term buy-and-hold returns for 500 stocks "
            "from 2010-2020 using CRSP adjusted closing prices. They compute total "
            "return as (adjusted_price_end / adjusted_price_start) - 1. The goal is "
            "measuring total shareholder return including dividends and splits. "
            "Audit this workflow."
        ),
        expected_validity=Validity.VALID,
        expected_violations=[],
        expected_repair=[],
        ground_truth_notes=(
            "CRSP adjusted prices are designed exactly for this purpose - computing "
            "total returns that incorporate splits, dividends, and distributions. "
            "Using adjusted prices for total return calculation is correct methodology. "
            "This is valid and should not be flagged."
        ),
        source_fields=SourceFields(
            backtest_start="2010-01-01",
            backtest_end="2020-12-31",
            extra={
                "calculation": "total return from adjusted prices",
                "source": "CRSP documentation"
            },
        ),
        data_source="manual",
        case_tags=["trap_valid", "requires_dataset_semantics"],
        source_note="CRSP documentation on adjusted prices",
    ),
    
    BenchmarkCase(
        id="cal_valid_delisting_conservative",
        module=Module.SURVIVORSHIP_DELISTING,
        difficulty=Difficulty.HARD,
        prompt=(
            "A researcher backtests a value strategy from 1995-2015. For stocks that "
            "delist, they use CRSP DLRET when available. When DLRET is missing for "
            "performance-related delistings (codes 400-599), they impute -30% following "
            "Shumway (1997). For merger-related delistings, they use the last available "
            "return. They document this methodology in their paper. Audit this workflow."
        ),
        expected_validity=Validity.VALID,
        expected_violations=[],
        expected_repair=[],
        ground_truth_notes=(
            "This follows academic best practices for handling delisting returns. "
            "Using available DLRET, conservative imputation for missing performance "
            "delistings (-30%), and appropriate treatment of mergers is the standard "
            "approach recommended by Shumway and Warther. This is valid methodology."
        ),
        source_fields=SourceFields(
            backtest_start="1995-01-01",
            backtest_end="2015-12-31",
            extra={
                "dlret_handling": "CRSP DLRET + Shumway imputation",
                "source": "Shumway (1997), Shumway & Warther (1999)"
            },
        ),
        data_source="manual",
        case_tags=["trap_valid"],
        source_note="Shumway (1997), Shumway & Warther (1999)",
    ),
    
    BenchmarkCase(
        id="cal_valid_ticker_permno_resolved",
        module=Module.TICKER_TIME_MACHINE,
        difficulty=Difficulty.HARD,
        prompt=(
            "A researcher studies Meta Platforms' stock performance during 2020-2021. "
            "They first look up the company in CRSP using the current name 'Meta', "
            "obtain PERMNO 13407, then retrieve all historical data using that PERMNO. "
            "For 2020-2021, this correctly returns data under ticker FB. They report "
            "results referencing the company as 'Meta (formerly Facebook)'. "
            "Audit this workflow."
        ),
        expected_validity=Validity.VALID,
        expected_violations=[],
        expected_repair=[],
        ground_truth_notes=(
            "Using PERMNO to retrieve historical data is the correct approach. The "
            "researcher correctly resolved the modern company name to a persistent "
            "identifier (PERMNO 13407), which then returns the historically correct "
            "ticker (FB) for 2020-2021. The naming in the report is cosmetic. This "
            "workflow is point-in-time valid."
        ),
        source_fields=SourceFields(
            permno="13407",
            company="Meta Platforms / Facebook",
            extra={"resolution_method": "PERMNO lookup"},
        ),
        data_source="WRDS CRSP",
        case_tags=["trap_valid", "requires_identifier_reasoning"],
        source_note="WRDS CRSP stocknames",
    ),
    
    BenchmarkCase(
        id="cal_valid_filing_next_day",
        module=Module.FILING_CLOCK,
        difficulty=Difficulty.MEDIUM,
        prompt=(
            "An 8-K is filed at 4:10 PM ET on Monday, March 13, 2023. EDGAR shows "
            "acceptance time of 4:10 PM. A trading strategy executes at 9:35 AM ET "
            "on Tuesday, March 14, 2023, using information from that 8-K. "
            "Audit this workflow."
        ),
        expected_validity=Validity.VALID,
        expected_violations=[],
        expected_repair=[],
        ground_truth_notes=(
            "The filing was accepted at 4:10 PM Monday. Trading at 9:35 AM Tuesday "
            "is clearly after the filing became public. The overnight gap provides "
            "ample time for information dissemination. This is valid."
        ),
        source_fields=SourceFields(
            filing_timestamp="2023-03-13 16:10:00 America/New_York",
            decision_timestamp="2023-03-14 09:35:00 America/New_York",
        ),
        data_source="manual",
        case_tags=["trap_valid", "requires_timestamp_reasoning"],
        source_note="SEC EDGAR timing rules",
    ),
    
    BenchmarkCase(
        id="cal_valid_sp500_effective_date",
        module=Module.SURVIVORSHIP_DELISTING,
        difficulty=Difficulty.MEDIUM,
        prompt=(
            "A researcher replicates the S&P 500 index from 2010-2020. They use "
            "historical constituent lists dated as of each month-end (effective "
            "membership). New additions are included starting the first trading "
            "day after the effective date. Deletions are removed after the effective "
            "date. They do not trade on announcement dates. Audit this workflow."
        ),
        expected_validity=Validity.VALID,
        expected_violations=[],
        expected_repair=[],
        ground_truth_notes=(
            "This is correct index replication methodology. Using effective-date "
            "constituent lists and trading after the effective date (not announcement "
            "date) avoids look-ahead bias. The researcher is using information that "
            "was publicly known at each rebalance point."
        ),
        source_fields=SourceFields(
            backtest_start="2010-01-01",
            backtest_end="2020-12-31",
            extra={"methodology": "effective-date constituents"},
        ),
        data_source="manual",
        case_tags=["trap_valid"],
        source_note="S&P Dow Jones Indices methodology",
    ),
    
    BenchmarkCase(
        id="cal_valid_earnings_afterclose_window",
        module=Module.FILING_CLOCK,
        difficulty=Difficulty.MEDIUM,
        prompt=(
            "A researcher studies earnings announcement reactions. For companies "
            "reporting after market close (after 4:00 PM ET), they define the event "
            "window as day t close to day t+1 close, where t is the announcement "
            "date. For companies reporting before market open, they use day t-1 "
            "close to day t close. They classify timing using I/B/E/S timestamps. "
            "Audit this workflow."
        ),
        expected_validity=Validity.VALID,
        expected_violations=[],
        expected_repair=[],
        ground_truth_notes=(
            "This is correct event study methodology. After-close announcements "
            "are incorporated overnight, so the reaction appears in day t+1 prices. "
            "Pre-market announcements are incorporated during day t trading. Using "
            "I/B/E/S timestamps to classify timing is standard practice."
        ),
        source_fields=SourceFields(
            extra={
                "event_window": "timing-adjusted",
                "timestamp_source": "I/B/E/S"
            },
        ),
        data_source="manual",
        case_tags=["trap_valid", "requires_timestamp_reasoning"],
        source_note="Event study methodology literature",
    ),
    
    BenchmarkCase(
        id="cal_valid_goog_liquidity_study",
        module=Module.TICKER_TIME_MACHINE,
        difficulty=Difficulty.HARD,
        prompt=(
            "A researcher studies market microstructure and liquidity for Alphabet "
            "from 2016-2023. They explicitly choose GOOG (Class C) over GOOGL "
            "(Class A) because GOOG has higher trading volume and tighter spreads, "
            "making it more suitable for liquidity analysis. They note that voting "
            "rights are not relevant for their microstructure research. "
            "Audit this workflow."
        ),
        expected_validity=Validity.VALID,
        expected_violations=[],
        expected_repair=[],
        ground_truth_notes=(
            "For liquidity and microstructure studies, GOOG vs GOOGL choice should "
            "be based on liquidity characteristics, not voting rights. The researcher "
            "explicitly justifies using GOOG for its superior liquidity metrics. "
            "Since voting rights are irrelevant to microstructure, this is valid."
        ),
        source_fields=SourceFields(
            company="Alphabet Inc",
            ticker="GOOG",
            extra={
                "justification": "liquidity focus, voting rights irrelevant",
                "study_type": "market microstructure"
            },
        ),
        data_source="manual",
        case_tags=["trap_valid", "requires_identifier_reasoning"],
        source_note="Alphabet share class structure",
    ),
    
    BenchmarkCase(
        id="cal_valid_compustat_lagged",
        module=Module.ACCOUNTING_AVAILABILITY,
        difficulty=Difficulty.HARD,
        prompt=(
            "A researcher backtests a value strategy from 2000-2020. They use "
            "Compustat annual data with a 6-month lag from fiscal year-end. For "
            "each portfolio formation in June, they use fundamentals from fiscal "
            "years ending in the prior calendar year. They verify that all 10-Ks "
            "in their sample were filed before the June formation date. "
            "Audit this workflow."
        ),
        expected_validity=Validity.VALID,
        expected_violations=[],
        expected_repair=[],
        ground_truth_notes=(
            "A 6-month lag from fiscal year-end for June portfolio formation is "
            "the standard Fama-French methodology. For December fiscal year-ends, "
            "this allows until June for 10-K filing (deadline is typically March "
            "for large firms). Verifying filing dates ensures point-in-time validity. "
            "This is correct methodology."
        ),
        source_fields=SourceFields(
            backtest_start="2000-01-01",
            backtest_end="2020-12-31",
            extra={
                "lag": "6 months from FYE",
                "formation": "June",
                "source": "Fama-French methodology"
            },
        ),
        data_source="manual",
        case_tags=["trap_valid", "requires_dataset_semantics"],
        source_note="Fama-French (1992) methodology",
    ),
]


# =============================================================================
# AMBIGUOUS CASES (8)
# Correct answer is "needs more information" - test uncertainty expression
# =============================================================================

AMBIGUOUS_CASES = [
    BenchmarkCase(
        id="cal_ambig_compustat_unknown_lag",
        module=Module.ACCOUNTING_AVAILABILITY,
        difficulty=Difficulty.HARD,
        prompt=(
            "A researcher uses Compustat annual fundamentals to construct book-to-"
            "market ratios for a 2010-2020 backtest. They form portfolios at the "
            "end of each June. The paper does not specify how fundamentals are "
            "aligned with portfolio formation dates. Audit this workflow."
        ),
        expected_validity=Validity.AMBIGUOUS,
        expected_violations=[],
        expected_repair=[
            "Need to know the lag between fiscal year-end and portfolio formation.",
            "Need to verify whether filing dates were checked.",
            "Need to know if point-in-time or current Compustat was used."
        ],
        ground_truth_notes=(
            "Without knowing the lag methodology, we cannot determine validity. "
            "If they used current FYE data immediately in January, it's invalid. "
            "If they used 6-month lagged data in June (Fama-French style), it's "
            "likely valid. More information is needed."
        ),
        source_fields=SourceFields(
            backtest_start="2010-01-01",
            backtest_end="2020-12-31",
            extra={"missing_info": "fundamentals-to-portfolio lag"},
        ),
        data_source="manual",
        case_tags=["ambiguous", "requires_dataset_semantics"],
        source_note="",
    ),
    
    BenchmarkCase(
        id="cal_ambig_filing_no_timestamp",
        module=Module.FILING_CLOCK,
        difficulty=Difficulty.HARD,
        prompt=(
            "A researcher studies 8-K filings and same-day stock returns. They "
            "state that each 8-K was 'filed on the event date' and measure returns "
            "on the filing date. The paper does not report acceptance times or "
            "specify when trading decisions were made. Audit this workflow."
        ),
        expected_validity=Validity.AMBIGUOUS,
        expected_violations=[],
        expected_repair=[
            "Need acceptance timestamps for each 8-K.",
            "Need to know when trading decisions were made (open, close, intraday).",
            "Need to verify filings were accepted before trading time."
        ],
        ground_truth_notes=(
            "An 8-K 'filed on the event date' could have been accepted at 6:00 AM "
            "or 9:00 PM. Without timestamps, we cannot verify that the filing was "
            "public before any trading decision. This is genuinely ambiguous."
        ),
        source_fields=SourceFields(
            extra={"missing_info": "acceptance timestamps and trade timing"},
        ),
        data_source="manual",
        case_tags=["ambiguous", "requires_timestamp_reasoning"],
        source_note="",
    ),
    
    BenchmarkCase(
        id="cal_ambig_goog_event_unclear",
        module=Module.TICKER_TIME_MACHINE,
        difficulty=Difficulty.HARD,
        prompt=(
            "A researcher studies Alphabet (ticker GOOG) stock reactions to "
            "corporate events from 2018-2023. The paper does not specify whether "
            "the events studied are governance-related (proxy votes, board changes) "
            "or general corporate events (earnings, product launches). "
            "Audit this workflow."
        ),
        expected_validity=Validity.AMBIGUOUS,
        expected_violations=[],
        expected_repair=[
            "Need to know the type of corporate events being studied.",
            "If governance events: GOOGL (voting shares) should be used.",
            "If general events or liquidity focus: GOOG may be acceptable."
        ],
        ground_truth_notes=(
            "GOOG is Class C (non-voting) while GOOGL is Class A (voting). For "
            "governance events, using GOOG would be inappropriate. For earnings "
            "or general events, both share classes react similarly. Cannot "
            "determine validity without knowing the event type."
        ),
        source_fields=SourceFields(
            company="Alphabet Inc",
            ticker="GOOG",
            extra={"missing_info": "event type (governance vs general)"},
        ),
        data_source="manual",
        case_tags=["ambiguous", "requires_identifier_reasoning"],
        source_note="",
    ),
    
    BenchmarkCase(
        id="cal_ambig_delisting_unknown",
        module=Module.SURVIVORSHIP_DELISTING,
        difficulty=Difficulty.HARD,
        prompt=(
            "A researcher's backtest drops observations with missing return data. "
            "The paper states they 'exclude observations where returns are not "
            "available.' It does not distinguish between delisting events, trading "
            "halts, data gaps, or non-trading days. Audit this workflow."
        ),
        expected_validity=Validity.AMBIGUOUS,
        expected_violations=[],
        expected_repair=[
            "Need to know what causes the missing returns.",
            "If delistings: must include DLRET or impute conservatively.",
            "If data gaps or halts: dropping may be acceptable.",
            "Need to verify this doesn't create survivorship bias."
        ],
        ground_truth_notes=(
            "Dropping 'missing returns' could be benign (holiday, data gap) or "
            "problematic (delisting without DLRET). Without knowing the cause, "
            "we cannot assess whether this introduces survivorship bias."
        ),
        source_fields=SourceFields(
            extra={"missing_info": "cause of missing returns"},
        ),
        data_source="manual",
        case_tags=["ambiguous"],
        source_note="",
    ),
    
    BenchmarkCase(
        id="cal_ambig_index_timing_unclear",
        module=Module.SURVIVORSHIP_DELISTING,
        difficulty=Difficulty.HARD,
        prompt=(
            "A researcher constructs portfolios based on S&P 500 membership from "
            "2005-2015. The paper states they 'use S&P 500 constituents' but does "
            "not specify whether membership is determined as of announcement date, "
            "effective date, or month-end. Audit this workflow."
        ),
        expected_validity=Validity.AMBIGUOUS,
        expected_violations=[],
        expected_repair=[
            "Need to specify when membership is determined.",
            "Announcement-date trading would be problematic.",
            "Effective-date or month-end membership is generally acceptable.",
            "Need to verify point-in-time versus current constituent lists."
        ],
        ground_truth_notes=(
            "S&P announcements precede effective dates by ~5 days. If trading on "
            "announcements using effective-date lists, that's look-ahead. If using "
            "effective-date lists for effective-date trading, it's valid. Cannot "
            "determine without more detail."
        ),
        source_fields=SourceFields(
            backtest_start="2005-01-01",
            backtest_end="2015-12-31",
            extra={"missing_info": "index membership timing methodology"},
        ),
        data_source="manual",
        case_tags=["ambiguous"],
        source_note="",
    ),
    
    BenchmarkCase(
        id="cal_ambig_adr_local_unclear",
        module=Module.TICKER_TIME_MACHINE,
        difficulty=Difficulty.HARD,
        prompt=(
            "A researcher studies Alibaba (BABA) stock reactions to Chinese "
            "regulatory announcements from 2016-2022. They use 'Alibaba stock "
            "prices' but do not specify whether they use the US-listed ADR (BABA) "
            "or Hong Kong-listed ordinary shares (9988.HK). Audit this workflow."
        ),
        expected_validity=Validity.AMBIGUOUS,
        expected_violations=[],
        expected_repair=[
            "Need to specify which security is used (ADR vs ordinary shares).",
            "If using ADR: must account for ADR ratio and trading hours.",
            "If using HK shares: timezone and market hours differ.",
            "Cross-listing dynamics may affect event study interpretation."
        ],
        ground_truth_notes=(
            "BABA ADR and 9988.HK have different trading hours and may react at "
            "different times to news. The ADR ratio (1:8) affects price levels. "
            "Cannot assess methodology without knowing which security was used."
        ),
        source_fields=SourceFields(
            company="Alibaba",
            extra={"missing_info": "ADR vs ordinary shares"},
        ),
        data_source="manual",
        case_tags=["ambiguous", "requires_identifier_reasoning"],
        source_note="",
    ),
    
    BenchmarkCase(
        id="cal_ambig_spinoff_adjustment",
        module=Module.TICKER_TIME_MACHINE,
        difficulty=Difficulty.HARD,
        prompt=(
            "A researcher computes long-run IBM returns from 2020-2023, a period "
            "that includes the Kyndryl spinoff in November 2021. They report a "
            "single cumulative return for IBM but do not describe how they handled "
            "the spinoff distribution. Audit this workflow."
        ),
        expected_validity=Validity.AMBIGUOUS,
        expected_violations=[],
        expected_repair=[
            "Need to know how the Kyndryl distribution was handled.",
            "If using CRSP adjusted returns: should be correct automatically.",
            "If using raw prices: must include KD distribution value.",
            "Without adjustment, returns would be understated by ~15%."
        ],
        ground_truth_notes=(
            "IBM shareholders received Kyndryl shares. Raw price return would show "
            "a ~15% drop that isn't a real loss. Need to know if total return "
            "(including KD value) or price return (potentially wrong) was used."
        ),
        source_fields=SourceFields(
            company="IBM",
            backtest_start="2020-01-01",
            backtest_end="2023-12-31",
            extra={"missing_info": "spinoff adjustment methodology"},
        ),
        data_source="manual",
        case_tags=["ambiguous", "requires_corporate_action_reasoning"],
        source_note="",
    ),
    
    BenchmarkCase(
        id="cal_ambig_intraday_timing",
        module=Module.FILING_CLOCK,
        difficulty=Difficulty.HARD,
        prompt=(
            "A researcher studies stock reactions to merger announcements. For "
            "each deal, they measure 'announcement-day returns' using close-to-close "
            "prices. The paper notes that announcements occurred on the same day "
            "as the measured return, but does not specify whether announcements "
            "were pre-market, intraday, or after-close. Audit this workflow."
        ),
        expected_validity=Validity.AMBIGUOUS,
        expected_violations=[],
        expected_repair=[
            "Need announcement timestamps to verify timing.",
            "If after-close: day t close-to-close misses the reaction.",
            "If pre-market or intraday: close-to-close captures it.",
            "Mixed timing would dilute measured abnormal returns."
        ],
        ground_truth_notes=(
            "Merger announcements can be pre-market, intraday, or after-close. "
            "Using day t close-to-close for after-close announcements would miss "
            "the reaction (which appears in day t+1). Cannot assess without "
            "knowing announcement timing."
        ),
        source_fields=SourceFields(
            extra={"missing_info": "announcement timestamps"},
        ),
        data_source="manual",
        case_tags=["ambiguous", "requires_timestamp_reasoning"],
        source_note="",
    ),
]


# =============================================================================
# HARD INVALID CASES (4)
# Subtle but real violations
# =============================================================================

HARD_INVALID_CASES = [
    BenchmarkCase(
        id="cal_invalid_ticker_reuse",
        module=Module.TICKER_TIME_MACHINE,
        difficulty=Difficulty.HARD,
        prompt=(
            "A researcher studies retail sector performance from 2003-2008 using "
            "ticker S. They treat ticker S as a single continuous security "
            "throughout the period and compute cumulative returns. They note "
            "'ticker S represents a major retail company.' Audit this workflow."
        ),
        expected_validity=Validity.INVALID,
        expected_violations=[
            ViolationType.IDENTIFIER_TIME_TRAVEL,
            ViolationType.ISSUER_SECURITY_CONFUSION,
        ],
        expected_repair=[
            "Ticker S was reassigned from Sears Roebuck to Sprint Nextel in 2005.",
            "Pre-2005 S = Sears (retail), Post-2005 S = Sprint (telecom).",
            "These are completely different companies.",
            "Use PERMNO to track specific securities, not tickers."
        ],
        ground_truth_notes=(
            "This is a classic ticker reuse trap. Ticker S belonged to Sears "
            "Roebuck (PERMNO 11850, retail) until 2005, then was reassigned to "
            "Sprint Nextel (PERMNO 87447, telecom). Treating this as one security "
            "produces nonsensical results."
        ),
        source_fields=SourceFields(
            ticker="S",
            backtest_start="2003-01-01",
            backtest_end="2008-12-31",
            extra={
                "sears_permno": "11850",
                "sprint_permno": "87447",
                "source": "CRSP stocknames"
            },
        ),
        data_source="WRDS CRSP",
        case_tags=["multi_violation", "requires_identifier_reasoning"],
        source_note="CRSP stocknames - ticker S reassignment 2005",
    ),
    
    BenchmarkCase(
        id="cal_invalid_filing_after_trade",
        module=Module.FILING_CLOCK,
        difficulty=Difficulty.HARD,
        prompt=(
            "A high-frequency trading strategy claims to use 8-K information. "
            "On April 15, 2023, an 8-K was accepted by EDGAR at 4:15 PM ET. The "
            "strategy executed a trade at 4:00 PM ET the same day based on "
            "'the 8-K contents.' Audit this workflow."
        ),
        expected_validity=Validity.INVALID,
        expected_violations=[ViolationType.FILING_CLOCK_LEAKAGE],
        expected_repair=[
            "The trade at 4:00 PM preceded the filing acceptance at 4:15 PM.",
            "The 8-K was not publicly available when the trade executed.",
            "This is impossible without non-public information.",
            "Trade must occur after filing acceptance time."
        ],
        ground_truth_notes=(
            "Simple chronology: 4:00 PM trade < 4:15 PM filing acceptance. "
            "The information in the 8-K was not public at trade time. This "
            "is either a data error or describes trading on non-public information."
        ),
        source_fields=SourceFields(
            filing_timestamp="2023-04-15 16:15:00 America/New_York",
            decision_timestamp="2023-04-15 16:00:00 America/New_York",
        ),
        data_source="manual",
        case_tags=["requires_timestamp_reasoning"],
        source_note="",
    ),
    
    BenchmarkCase(
        id="cal_invalid_modern_ticker_historical",
        module=Module.TICKER_TIME_MACHINE,
        difficulty=Difficulty.MEDIUM,
        prompt=(
            "A researcher studies the COVID-19 market crash in March 2020 and "
            "its impact on social media companies. They query daily returns for "
            "ticker META from February-April 2020. The paper analyzes 'Meta's "
            "stock performance during the pandemic selloff.' Audit this workflow."
        ),
        expected_validity=Validity.INVALID,
        expected_violations=[ViolationType.IDENTIFIER_TIME_TRAVEL],
        expected_repair=[
            "META ticker did not exist until June 9, 2022.",
            "In March 2020, the company traded under ticker FB.",
            "Use FB for any data before June 9, 2022.",
            "Query using PERMNO 13407 for consistent identification."
        ],
        ground_truth_notes=(
            "The ticker change from FB to META occurred on June 9, 2022. "
            "Querying META for March 2020 data would return no results or "
            "wrong data. The correct ticker was FB."
        ),
        source_fields=SourceFields(
            company="Meta Platforms / Facebook",
            bad_ticker="META",
            historical_ticker="FB",
            event_date="2020-03-15",
            extra={"ticker_change_date": "2022-06-09"},
        ),
        data_source="WRDS CRSP",
        case_tags=["requires_identifier_reasoning"],
        source_note="FB to META ticker change June 9, 2022",
    ),
    
    BenchmarkCase(
        id="cal_invalid_current_universe",
        module=Module.SURVIVORSHIP_DELISTING,
        difficulty=Difficulty.MEDIUM,
        prompt=(
            "A researcher backtests a momentum strategy on S&P 500 stocks from "
            "2005-2015. They download the current (2024) S&P 500 constituent list "
            "and query returns for these 500 companies throughout the backtest "
            "period. They note this ensures 'adequate liquidity and data quality.' "
            "Audit this workflow."
        ),
        expected_validity=Validity.INVALID,
        expected_violations=[
            ViolationType.SURVIVORSHIP_BIAS,
            ViolationType.DELISTING_RETURN_OMISSION,
        ],
        expected_repair=[
            "The 2024 S&P 500 list excludes companies that failed or were removed.",
            "Major failures during 2005-2015 (Lehman, Bear Stearns, etc.) are excluded.",
            "Use historical constituent lists at each point in time.",
            "Include delisting returns for companies that exited the index."
        ],
        ground_truth_notes=(
            "Using current constituents for historical backtests is classic "
            "survivorship bias. The 2024 list excludes Lehman Brothers, Bear "
            "Stearns, Washington Mutual, and other failures during 2005-2015. "
            "This significantly overstates strategy returns."
        ),
        source_fields=SourceFields(
            backtest_start="2005-01-01",
            backtest_end="2015-12-31",
            extra={
                "universe_source": "current (2024) S&P 500 list",
                "excluded_examples": "Lehman, Bear Stearns, WaMu"
            },
        ),
        data_source="manual",
        case_tags=["multi_violation"],
        source_note="Classic survivorship bias example",
    ),
]


# =============================================================================
# Collect all calibration cases
# =============================================================================

CALIBRATION_CASES: list[BenchmarkCase] = (
    VALID_TRAP_CASES +
    AMBIGUOUS_CASES +
    HARD_INVALID_CASES
)


def get_calibration_cases() -> list[BenchmarkCase]:
    """Return all calibration benchmark cases."""
    return CALIBRATION_CASES


def get_valid_trap_cases() -> list[BenchmarkCase]:
    """Return valid trap cases (test overcaution)."""
    return VALID_TRAP_CASES


def get_ambiguous_cases() -> list[BenchmarkCase]:
    """Return ambiguous cases (test uncertainty expression)."""
    return AMBIGUOUS_CASES


def get_hard_invalid_cases() -> list[BenchmarkCase]:
    """Return hard invalid cases from calibration set."""
    return HARD_INVALID_CASES


def print_calibration_summary():
    """Print summary of calibration cases."""
    print("=" * 70)
    print("CALIBRATION CASES SUMMARY (V4)")
    print("=" * 70)
    
    print(f"\nValid Trap Cases: {len(VALID_TRAP_CASES)}")
    for case in VALID_TRAP_CASES:
        print(f"  [V] {case.id}")
    
    print(f"\nAmbiguous Cases: {len(AMBIGUOUS_CASES)}")
    for case in AMBIGUOUS_CASES:
        print(f"  [?] {case.id}")
    
    print(f"\nHard Invalid Cases: {len(HARD_INVALID_CASES)}")
    for case in HARD_INVALID_CASES:
        print(f"  [X] {case.id}")
    
    print(f"\n{'=' * 70}")
    print(f"TOTAL: {len(CALIBRATION_CASES)} cases")
    print("=" * 70)


if __name__ == "__main__":
    print_calibration_summary()
