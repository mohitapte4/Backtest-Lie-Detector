"""
False Valid Trap Cases for V5 Benchmark.

These 16 cases are designed to produce false valid errors. Each case:
- Sounds professional and methodologically sound
- Includes reassuring language about point-in-time validity
- Contains a subtle implementation-level bug that trained practitioners would catch

Purpose: Test whether models can detect subtle violations hidden inside
otherwise professional methodology descriptions.
"""

from backtest_lie_detector.schemas import (
    BenchmarkCase,
    Difficulty,
    Module,
    SourceFields,
    Validity,
    ViolationType,
)


FALSE_VALID_TRAP_CASES = [
    # =========================================================================
    # Case 1: CCM Link Date Ignored
    # =========================================================================
    BenchmarkCase(
        id="fvt_ccm_link_date_ignored",
        module=Module.TICKER_TIME_MACHINE,
        difficulty=Difficulty.HARD,
        prompt=(
            "A researcher builds a factor portfolio using CRSP returns merged with "
            "Compustat fundamentals. They resolve tickers to CRSP PERMNOs for point-in-time "
            "identifier validity, then join to Compustat using the CCM link table "
            "downloaded in 2026. The merge matches on GVKEY and PERMNO. The researcher "
            "states they use point-in-time identifiers via CRSP. Audit this workflow."
        ),
        expected_validity=Validity.INVALID,
        expected_violations=[ViolationType.LINK_DATE_LEAKAGE],
        expected_repair=[
            "Filter the CCM link table by linkdt and linkenddt for each observation date.",
            "Only use GVKEY-PERMNO links that were valid at the historical observation time.",
        ],
        ground_truth_notes=(
            "The CCM link table contains historical link validity periods (linkdt, linkenddt). "
            "A 2026 download includes links that may not have existed historically. Without "
            "filtering by link dates, the researcher may use GVKEY-PERMNO mappings that were "
            "not valid at the observation time. This is a subtle but real point-in-time error."
        ),
        source_fields=SourceFields(
            extra={"data_source": "WRDS CCM", "download_date": "2026"},
        ),
        data_source="manual",
        case_tags=["false_valid_trap", "near_miss", "requires_dataset_semantics"],
        source_note="WRDS CCM documentation on linkdt/linkenddt fields",
    ),

    # =========================================================================
    # Case 2: Six-Month Lag from Datadate Not Filing Date
    # =========================================================================
    BenchmarkCase(
        id="fvt_lag_from_datadate",
        module=Module.ACCOUNTING_AVAILABILITY,
        difficulty=Difficulty.HARD,
        prompt=(
            "A researcher forms monthly value portfolios using annual Compustat fundamentals. "
            "They lag all accounting data by exactly six months after datadate (fiscal period "
            "end) to ensure data availability. They state this conservative lag avoids "
            "look-ahead bias. The strategy rebalances on the first trading day of each month. "
            "Audit this workflow."
        ),
        expected_validity=Validity.INVALID,
        expected_violations=[ViolationType.ACCOUNTING_AVAILABILITY_LEAKAGE],
        expected_repair=[
            "Use actual SEC filing dates (rdq or filedate) rather than fixed lag from datadate.",
            "Alternatively, use point-in-time Compustat snapshots if available.",
            "If using fixed lag, document the assumption and test sensitivity to longer lags.",
        ],
        ground_truth_notes=(
            "A six-month lag from fiscal period end (datadate) is NOT sufficient for all firms. "
            "While most 10-Ks are filed within 60-90 days, some firms file later, and the "
            "lag varies by firm size and fiscal year end. Using a fixed lag from datadate "
            "rather than actual filing date can still introduce look-ahead bias for late filers. "
            "The correct approach is to use actual filing/report dates when available."
        ),
        source_fields=SourceFields(
            extra={"lag_method": "6 months from datadate"},
        ),
        data_source="manual",
        case_tags=["false_valid_trap", "near_miss", "requires_dataset_semantics"],
        source_note="Compustat RDQ field documentation; SEC filing deadlines",
    ),

    # =========================================================================
    # Case 3: DLRET Replaces RET Instead of Combining
    # =========================================================================
    BenchmarkCase(
        id="fvt_dlret_replaces_ret",
        module=Module.SURVIVORSHIP_DELISTING,
        difficulty=Difficulty.HARD,
        prompt=(
            "A researcher backtests a momentum strategy from 1990-2020. To properly handle "
            "delistings, they include CRSP delisting returns (DLRET). Their code replaces "
            "RET with DLRET whenever DLRET is non-missing. They state they include delisting "
            "returns following best practices. Audit this workflow."
        ),
        expected_validity=Validity.INVALID,
        expected_violations=[ViolationType.DELISTING_RETURN_CONSTRUCTION],
        expected_repair=[
            "Combine RET and DLRET appropriately: total_ret = (1+RET)*(1+DLRET) - 1 when both present.",
            "Do not blindly replace RET with DLRET; they may both contain information.",
            "Handle missing values carefully according to CRSP documentation.",
        ],
        ground_truth_notes=(
            "CRSP RET and DLRET can both be present for the same PERMNO-date. RET captures "
            "the return up to the last trading day, while DLRET captures the delisting event. "
            "Replacing RET with DLRET loses the last trading day return. The correct approach "
            "is to compound them: (1+RET)*(1+DLRET) - 1. This is a common implementation error "
            "even among researchers who know to include delisting returns."
        ),
        source_fields=SourceFields(
            extra={"delisting_handling": "replace RET with DLRET"},
        ),
        data_source="manual",
        case_tags=["false_valid_trap", "near_miss", "requires_dataset_semantics"],
        source_note="CRSP data definitions; Shumway (1997) methodology",
    ),

    # =========================================================================
    # Case 4: Filing Date Checked Without Acceptance Time
    # =========================================================================
    BenchmarkCase(
        id="fvt_filing_date_no_time",
        module=Module.FILING_CLOCK,
        difficulty=Difficulty.HARD,
        prompt=(
            "A same-day event study trades on SEC filing releases. The researcher checks "
            "that filing_date <= trade_date before using filing information. Trades occur "
            "at 3:50 PM ET. The researcher states they properly check filing dates. "
            "Audit this workflow."
        ),
        expected_validity=Validity.INVALID,
        expected_violations=[ViolationType.FILING_CLOCK_LEAKAGE],
        expected_repair=[
            "Use EDGAR acceptance timestamp, not just filing date.",
            "Filings accepted after 3:50 PM should not be used for 3:50 PM trades.",
            "Account for EDGAR dissemination rules (e.g., 5:30 PM cutoff for same-day).",
        ],
        ground_truth_notes=(
            "Filing date alone is insufficient for intraday timing. A filing submitted on "
            "the trade date could have been accepted at 4:30 PM, after the 3:50 PM trade. "
            "EDGAR acceptance timestamps are required for same-day trading strategies. "
            "The filing_date field only captures the calendar date, not the time."
        ),
        source_fields=SourceFields(
            decision_timestamp="3:50 PM ET",
            extra={"check": "filing_date <= trade_date"},
        ),
        data_source="manual",
        case_tags=["false_valid_trap", "near_miss", "requires_timestamp_reasoning"],
        source_note="SEC EDGAR filing documentation",
    ),

    # =========================================================================
    # Case 5: Adjusted Prices Used for Price-Level Trigger
    # =========================================================================
    BenchmarkCase(
        id="fvt_adjusted_price_level",
        module=Module.TICKER_TIME_MACHINE,
        difficulty=Difficulty.HARD,
        prompt=(
            "A researcher implements a penny stock filter that excludes stocks trading "
            "below $5. They use CRSP split-adjusted closing prices to avoid issues with "
            "stock splits. The researcher states they use split-adjusted prices to ensure "
            "historical comparability. Audit this workflow."
        ),
        expected_validity=Validity.INVALID,
        expected_violations=[ViolationType.ADJUSTED_PRICE_MISUSE],
        expected_repair=[
            "Use actual historical quoted prices (PRC) for price-level eligibility rules.",
            "Adjusted prices are appropriate for computing returns, not for price-level filters.",
            "A stock at $50 in 2010 may show as $5 adjusted due to subsequent 10:1 split.",
        ],
        ground_truth_notes=(
            "CRSP adjusted prices back-adjust historical prices for splits and dividends. "
            "A stock that traded at $50 in 2010 but later had a 10:1 split would show an "
            "adjusted price of $5 for 2010. Using adjusted prices for a $5 filter would "
            "incorrectly exclude this stock. Price-level rules should use actual quoted "
            "prices (PRC in CRSP), not adjusted prices."
        ),
        source_fields=SourceFields(
            extra={"filter": "adjusted_price < $5", "issue": "level vs return"},
        ),
        data_source="manual",
        case_tags=["false_valid_trap", "near_miss", "requires_dataset_semantics"],
        source_note="CRSP data definitions on adjusted vs raw prices",
    ),

    # =========================================================================
    # Case 6: Current Industry Classification Used Historically
    # =========================================================================
    BenchmarkCase(
        id="fvt_current_industry",
        module=Module.SURVIVORSHIP_DELISTING,
        difficulty=Difficulty.HARD,
        prompt=(
            "A researcher runs a 2000-2020 backtest that controls for industry fixed effects. "
            "Industry classifications are obtained from a 2026 Compustat download using each "
            "firm's GICS code. The researcher states they control for industry effects using "
            "standard classifications. Audit this workflow."
        ),
        expected_validity=Validity.INVALID,
        expected_violations=[ViolationType.CURRENT_METADATA_LEAKAGE],
        expected_repair=[
            "Use historical industry classifications valid at each observation date.",
            "GICS codes change over time as firms restructure or as GICS is revised.",
            "Use point-in-time industry data or document sensitivity to classification changes.",
        ],
        ground_truth_notes=(
            "Industry classifications (SIC, NAICS, GICS) change over time. A firm classified "
            "as 'Technology' in 2020 may have been 'Telecom' in 2000. Using 2026 classifications "
            "for a 2000-2020 backtest introduces look-ahead bias in the control variables. "
            "This can bias factor exposures and portfolio characteristics."
        ),
        source_fields=SourceFields(
            backtest_start="2000-01-01",
            backtest_end="2020-12-31",
            extra={"classification": "2026 GICS download"},
        ),
        data_source="manual",
        case_tags=["false_valid_trap", "near_miss", "requires_dataset_semantics"],
        source_note="GICS methodology; Compustat historical industry codes",
    ),

    # =========================================================================
    # Case 7: Index Announcement vs Effective Date Mismatch
    # =========================================================================
    BenchmarkCase(
        id="fvt_index_announce_vs_effective",
        module=Module.SURVIVORSHIP_DELISTING,
        difficulty=Difficulty.HARD,
        prompt=(
            "A researcher studies S&P 500 constituent returns from 2010-2020. They use "
            "index announcement data from S&P to identify additions. Firms are included "
            "in the S&P 500 universe starting on the announcement date. The researcher "
            "states they use official index announcement data. Audit this workflow."
        ),
        expected_validity=Validity.INVALID,
        expected_violations=[ViolationType.INDEX_TIMING_LEAKAGE],
        expected_repair=[
            "Distinguish between index announcement date and effective membership date.",
            "Firms become actual constituents on the effective date, not announcement date.",
            "Use announcement date for event studies of announcement effects only.",
        ],
        ground_truth_notes=(
            "S&P announces index changes typically 5 trading days before the effective date. "
            "A firm announced on Monday becomes a constituent the following Monday. Treating "
            "the firm as a constituent from announcement date gives an extra week of 'membership' "
            "that didn't exist. For constituent-based strategies, use effective date; for "
            "announcement effect studies, use announcement date."
        ),
        source_fields=SourceFields(
            extra={"timing": "announcement date used as membership"},
        ),
        data_source="manual",
        case_tags=["false_valid_trap", "near_miss", "requires_timestamp_reasoning"],
        source_note="S&P Index Methodology documentation",
    ),

    # =========================================================================
    # Case 8: IBES Forecast Timing Bug
    # =========================================================================
    BenchmarkCase(
        id="fvt_ibes_forecast_timing",
        module=Module.ACCOUNTING_AVAILABILITY,
        difficulty=Difficulty.HARD,
        prompt=(
            "A researcher forms portfolios on the first trading day of each month based on "
            "analyst earnings forecasts. They use all I/B/E/S forecast revisions dated within "
            "that calendar month to compute consensus estimates. The researcher states they "
            "use I/B/E/S consensus estimates. Audit this workflow."
        ),
        expected_validity=Validity.INVALID,
        expected_violations=[ViolationType.FORECAST_TIMING_LEAKAGE],
        expected_repair=[
            "Only use forecasts with ANNDATS (announcement date) before portfolio formation.",
            "Forecasts dated later in the month are not known at month start.",
            "Use point-in-time I/B/E/S data with ANNDATS_ACT for actual availability.",
        ],
        ground_truth_notes=(
            "I/B/E/S forecast dates (ANNDATS) indicate when the forecast was made. A forecast "
            "dated January 15 is not available on January 1. Using all January forecasts for "
            "a January 1 portfolio uses future information. Only forecasts with ANNDATS before "
            "the portfolio formation date should be included."
        ),
        source_fields=SourceFields(
            extra={"timing": "all month forecasts for month-start portfolio"},
        ),
        data_source="manual",
        case_tags=["false_valid_trap", "near_miss", "requires_timestamp_reasoning"],
        source_note="I/B/E/S timing field documentation",
    ),

    # =========================================================================
    # Case 9: Intraday Data Leakage
    # =========================================================================
    BenchmarkCase(
        id="fvt_intraday_leakage",
        module=Module.FILING_CLOCK,
        difficulty=Difficulty.HARD,
        prompt=(
            "A high-frequency strategy trades at 2:00 PM ET using same-day realized "
            "volatility as a signal. The volatility is computed from all trades in the "
            "current trading day. The researcher states they use intraday data for "
            "real-time signals. Audit this workflow."
        ),
        expected_validity=Validity.INVALID,
        expected_violations=[ViolationType.INTRADAY_DATA_LEAKAGE],
        expected_repair=[
            "Compute volatility only from trades before 2:00 PM (e.g., 9:30 AM to 1:59 PM).",
            "Using full-day volatility at 2:00 PM includes trades from 2:00-4:00 PM.",
            "Ensure all feature computation uses only data available at decision time.",
        ],
        ground_truth_notes=(
            "A 2:00 PM trading decision cannot use data from after 2:00 PM. Computing "
            "'same-day realized volatility' from all daily trades includes information from "
            "2:00-4:00 PM that would not be available at the 2:00 PM decision point. This is "
            "intraday look-ahead bias."
        ),
        source_fields=SourceFields(
            decision_timestamp="2:00 PM ET",
            extra={"signal": "same-day realized volatility"},
        ),
        data_source="manual",
        case_tags=["false_valid_trap", "near_miss", "requires_timestamp_reasoning"],
        source_note="Standard intraday backtesting methodology",
    ),

    # =========================================================================
    # Case 10: Share Class Interchange for Governance Study
    # =========================================================================
    BenchmarkCase(
        id="fvt_share_class_interchange",
        module=Module.TICKER_TIME_MACHINE,
        difficulty=Difficulty.HARD,
        prompt=(
            "A researcher studies corporate governance events related to shareholder voting "
            "rights at Alphabet from 2015-2023. They use whichever share class (GOOG or GOOGL) "
            "has more complete return data, treating them as interchangeable since they "
            "represent the same company. The researcher states they use high-quality equity "
            "data for their event study. Audit this workflow."
        ),
        expected_validity=Validity.INVALID,
        expected_violations=[ViolationType.ISSUER_SECURITY_CONFUSION],
        expected_repair=[
            "Use GOOGL (Class A) for voting-rights studies since only Class A has voting rights.",
            "GOOG (Class C) has no voting rights and may have different price dynamics.",
            "Match share class to the economic claim being tested.",
        ],
        ground_truth_notes=(
            "Alphabet's Class A (GOOGL) shares have voting rights; Class C (GOOG) shares do not. "
            "For a governance/voting study, using Class C returns is inappropriate since those "
            "shares have no governance participation. The share classes are NOT interchangeable "
            "for voting-related research, even though they represent the same company."
        ),
        source_fields=SourceFields(
            ticker="GOOG/GOOGL",
            extra={"study": "voting rights governance"},
        ),
        data_source="manual",
        case_tags=["false_valid_trap", "near_miss", "requires_corporate_action_reasoning"],
        source_note="Alphabet proxy statement; share class documentation",
    ),

    # =========================================================================
    # Case 11: Restated Values Despite Conservative Lag
    # =========================================================================
    BenchmarkCase(
        id="fvt_restated_despite_lag",
        module=Module.ACCOUNTING_AVAILABILITY,
        difficulty=Difficulty.HARD,
        prompt=(
            "A researcher backtests a quality factor from 2005-2015 using Compustat "
            "fundamentals. They apply a conservative 6-month lag after fiscal year end "
            "before using the data. The Compustat annual file was downloaded in 2026. "
            "The researcher states they lag fundamentals conservatively. Audit this workflow."
        ),
        expected_validity=Validity.INVALID,
        expected_violations=[ViolationType.RESTATEMENT_LEAKAGE],
        expected_repair=[
            "Use point-in-time Compustat snapshots to avoid restatement and restandardization bias.",
            "A 2026 download contains restated values that weren't available in 2005-2015.",
            "Alternatively, use as-filed data from SEC EDGAR XBRL.",
        ],
        ground_truth_notes=(
            "Compustat data is restated when companies amend filings and restandardized when "
            "Compustat updates its data definitions. A 2026 download for a 2005-2015 backtest "
            "contains values that were not available during the backtest period. The 6-month "
            "lag only addresses filing timing, not restatement/restandardization bias."
        ),
        source_fields=SourceFields(
            backtest_start="2005-01-01",
            backtest_end="2015-12-31",
            extra={"download": "2026 Compustat"},
        ),
        data_source="manual",
        case_tags=["false_valid_trap", "near_miss", "requires_dataset_semantics"],
        source_note="WRDS Compustat point-in-time documentation",
    ),

    # =========================================================================
    # Case 12: Current ETF Holdings Applied Historically
    # =========================================================================
    BenchmarkCase(
        id="fvt_current_etf_holdings",
        module=Module.SURVIVORSHIP_DELISTING,
        difficulty=Difficulty.HARD,
        prompt=(
            "A researcher studies sector ETF performance from 2010-2020. They obtain "
            "current ETF holdings from a 2026 download and apply these as the historical "
            "constituent list for the backtest period. The researcher states they use "
            "sector ETF constituents for their analysis. Audit this workflow."
        ),
        expected_validity=Validity.INVALID,
        expected_violations=[ViolationType.SURVIVORSHIP_BIAS, ViolationType.CURRENT_METADATA_LEAKAGE],
        expected_repair=[
            "Use historical ETF holdings data for each rebalance date.",
            "Current holdings exclude firms that were constituents but later removed.",
            "ETF holdings change frequently due to index reconstitution.",
        ],
        ground_truth_notes=(
            "ETF holdings change over time as the underlying index is reconstituted. Using "
            "2026 holdings for a 2010-2020 study excludes companies that were in the ETF "
            "during that period but later removed (e.g., due to M&A, sector reclassification, "
            "or poor performance). This introduces survivorship bias."
        ),
        source_fields=SourceFields(
            backtest_start="2010-01-01",
            backtest_end="2020-12-31",
            extra={"holdings": "2026 download"},
        ),
        data_source="manual",
        case_tags=["false_valid_trap", "near_miss", "requires_dataset_semantics"],
        source_note="ETF holdings methodology; index reconstitution rules",
    ),

    # =========================================================================
    # Case 13: Macro Release Before Release Time
    # =========================================================================
    BenchmarkCase(
        id="fvt_macro_before_release",
        module=Module.FILING_CLOCK,
        difficulty=Difficulty.HARD,
        prompt=(
            "A macro trading strategy trades at 8:00 AM ET on CPI release days, using that "
            "day's CPI surprise as a signal. The data is from the official BLS release with "
            "correct release dates. CPI is released at 8:30 AM ET. The researcher states "
            "they use official macro releases from a reputable data vendor. Audit this workflow."
        ),
        expected_validity=Validity.INVALID,
        expected_violations=[ViolationType.FILING_CLOCK_LEAKAGE],
        expected_repair=[
            "Trade after 8:30 AM ET when CPI is actually released, not at 8:00 AM.",
            "The CPI value is not public until 8:30 AM on release day.",
            "Account for exact release times, not just release dates.",
        ],
        ground_truth_notes=(
            "CPI is released at 8:30 AM ET. Trading at 8:00 AM using that day's CPI surprise "
            "is impossible - the information is not yet public. Having the correct release "
            "date is not sufficient; the exact release time matters for same-day strategies."
        ),
        source_fields=SourceFields(
            decision_timestamp="8:00 AM ET",
            filing_timestamp="8:30 AM ET (CPI release)",
            extra={"data": "BLS CPI"},
        ),
        data_source="manual",
        case_tags=["false_valid_trap", "near_miss", "requires_timestamp_reasoning"],
        source_note="BLS release schedule documentation",
    ),

    # =========================================================================
    # Case 14: Event Window Mismatch for Earnings
    # =========================================================================
    BenchmarkCase(
        id="fvt_event_window_mismatch",
        module=Module.FILING_CLOCK,
        difficulty=Difficulty.HARD,
        prompt=(
            "A researcher studies earnings announcement returns. They compute a standard "
            "[0,1] close-to-close event window for all announcements, measuring the return "
            "from close on day 0 to close on day 1. This window is applied uniformly to "
            "all earnings announcements regardless of timing. The researcher states they "
            "use standard event windows. Audit this workflow."
        ),
        expected_validity=Validity.INVALID,
        expected_violations=[ViolationType.WRONG_EVENT_WINDOW],
        expected_repair=[
            "Align event windows based on announcement timestamp (pre-market vs after-close).",
            "After-close announcements: [0,1] captures day 1 reaction appropriately.",
            "Pre-market announcements: [−1,0] may be more appropriate to capture day 0 reaction.",
        ],
        ground_truth_notes=(
            "Earnings announced after market close on day 0 are reflected in day 1 prices. "
            "Earnings announced before market open on day 0 are reflected in day 0 prices. "
            "Using the same [0,1] window for both creates measurement error: pre-market "
            "announcements would have day 1 return that includes a full day of non-event noise."
        ),
        source_fields=SourceFields(
            extra={"event_window": "[0,1] close-to-close for all"},
        ),
        data_source="manual",
        case_tags=["false_valid_trap", "near_miss", "requires_timestamp_reasoning"],
        source_note="Event study methodology; I/B/E/S timing flags",
    ),

    # =========================================================================
    # Case 15: Current Exchange/Share Code Filter
    # =========================================================================
    BenchmarkCase(
        id="fvt_current_exchange_filter",
        module=Module.SURVIVORSHIP_DELISTING,
        difficulty=Difficulty.HARD,
        prompt=(
            "A researcher uses CRSP returns from 1990-2020. They filter to include only "
            "NYSE and NASDAQ listed firms using each firm's current exchange code from "
            "a 2026 CRSP download. Share codes are also filtered using 2026 values. "
            "The researcher states they use CRSP data with standard exchange filters. "
            "Audit this workflow."
        ),
        expected_validity=Validity.INVALID,
        expected_violations=[ViolationType.CURRENT_METADATA_LEAKAGE],
        expected_repair=[
            "Use exchange codes (EXCHCD) and share codes (SHRCD) valid at each historical date.",
            "Firms change exchanges over time (e.g., AMEX to NYSE upgrades).",
            "Historical CRSP files contain time-varying exchange assignments.",
        ],
        ground_truth_notes=(
            "Exchange listings change over time. A firm currently on NYSE may have been on "
            "AMEX or NASDAQ in 1990. Using 2026 exchange codes for 1990-2020 data excludes "
            "firms that were on NYSE/NASDAQ historically but later delisted, and includes "
            "firms that were on other exchanges but later moved to NYSE/NASDAQ."
        ),
        source_fields=SourceFields(
            backtest_start="1990-01-01",
            backtest_end="2020-12-31",
            extra={"filter": "2026 exchange codes"},
        ),
        data_source="manual",
        case_tags=["false_valid_trap", "near_miss", "requires_dataset_semantics"],
        source_note="CRSP exchange code documentation",
    ),

    # =========================================================================
    # Case 16: M&A Announcement vs Completion Date
    # =========================================================================
    BenchmarkCase(
        id="fvt_ma_announce_vs_complete",
        module=Module.SURVIVORSHIP_DELISTING,
        difficulty=Difficulty.HARD,
        prompt=(
            "A researcher maintains a monthly investable universe, removing acquisition "
            "targets from the portfolio. When a merger is announced, they immediately "
            "remove the target company from the investable universe starting that month. "
            "The researcher states they properly account for M&A activity. Audit this workflow."
        ),
        expected_validity=Validity.INVALID,
        expected_violations=[ViolationType.CORPORATE_ACTION_TIMING],
        expected_repair=[
            "Keep target in universe until merger completion/effective date, not announcement.",
            "Targets remain tradeable between announcement and completion (often 3-6 months).",
            "Use CRSP delisting date or actual completion date to remove from universe.",
        ],
        ground_truth_notes=(
            "Merger announcements typically precede completion by 3-6 months. The target "
            "company remains publicly traded and investable during this period. Removing "
            "at announcement excludes returns (often positive arbitrage spreads) that were "
            "actually available to investors. This also misses deals that are announced but "
            "never completed."
        ),
        source_fields=SourceFields(
            extra={"removal_timing": "announcement date"},
        ),
        data_source="manual",
        case_tags=["false_valid_trap", "near_miss", "requires_corporate_action_reasoning"],
        source_note="SDC M&A data; CRSP delisting documentation",
    ),
]


def get_false_valid_trap_cases() -> list[BenchmarkCase]:
    """Return all false valid trap cases."""
    return FALSE_VALID_TRAP_CASES


def get_case_ids() -> list[str]:
    """Return all false valid trap case IDs."""
    return [case.id for case in FALSE_VALID_TRAP_CASES]
