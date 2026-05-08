"""
Adversarial benchmark cases for the Backtest Lie Detector.

These cases are designed to be genuinely challenging:
1. "Trap" valid cases - look suspicious but are actually correct
2. Subtle invalid cases - non-obvious violations
3. Multi-violation cases - multiple interacting issues

Goal: Reduce model accuracy from 97.6% to 85-90% with harder cases.
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
# TRAP VALID CASES - Look suspicious but are actually correct
# Tests if model is overly cautious (false invalid rate)
# =============================================================================

TRAP_VALID_CASES = [
    # Filing Clock - Near-miss timing (valid)
    BenchmarkCase(
        id="trap_filing_5min_margin",
        module=Module.FILING_CLOCK,
        difficulty=Difficulty.HARD,
        prompt=(
            "An 8-K is accepted by EDGAR at 3:55 PM ET on March 15, 2023. "
            "A trading algorithm executes a trade at 4:00 PM ET the same day "
            "using information from that 8-K. Audit this workflow."
        ),
        expected_validity=Validity.VALID,
        expected_violations=[],
        expected_repair=[],
        ground_truth_notes=(
            "The filing was accepted at 3:55 PM, and the trade occurred at 4:00 PM. "
            "The 5-minute gap is sufficient - the filing was publicly available. "
            "This is valid despite the tight timing."
        ),
        source_fields=SourceFields(
            filing_timestamp="2023-03-15 15:55:00 America/New_York",
            decision_timestamp="2023-03-15 16:00:00 America/New_York",
        ),
    ),
    
    # Ticker - Day-of change but using correct historical ticker
    BenchmarkCase(
        id="trap_ticker_change_day_correct",
        module=Module.TICKER_TIME_MACHINE,
        difficulty=Difficulty.HARD,
        prompt=(
            "On June 9, 2022, Meta Platforms changed its ticker from FB to META. "
            "A researcher studies Meta's stock return on June 9, 2022 using ticker FB "
            "for the morning session data. Audit this workflow."
        ),
        expected_validity=Validity.VALID,
        expected_violations=[],
        expected_repair=[],
        ground_truth_notes=(
            "The ticker change occurred during the trading day. Using FB for morning "
            "data on June 9, 2022 is correct - that was the valid ticker at that time. "
            "The researcher correctly used the historical ticker."
        ),
        source_fields=SourceFields(
            company="Meta Platforms",
            event_date="2022-06-09",
            ticker="FB",
            extra={"change_date": "2022-06-09", "new_ticker": "META"},
        ),
    ),
    
    # Accounting - Complex but correct fiscal year lag
    BenchmarkCase(
        id="trap_fiscal_year_complex_valid",
        module=Module.ACCOUNTING_AVAILABILITY,
        difficulty=Difficulty.HARD,
        prompt=(
            "Walmart's fiscal year ends January 31. Their FY2023 10-K (ending Jan 31, 2023) "
            "was filed on March 24, 2023. A portfolio is formed on April 1, 2023 using "
            "Walmart's FY2023 net income. Audit this workflow."
        ),
        expected_validity=Validity.VALID,
        expected_violations=[],
        expected_repair=[],
        ground_truth_notes=(
            "Walmart's non-calendar fiscal year ends Jan 31. The FY2023 10-K was filed "
            "March 24, 2023. Using this data on April 1, 2023 is valid - the filing "
            "was publicly available for a week before portfolio formation."
        ),
        source_fields=SourceFields(
            company="Walmart",
            fiscal_year_end="2023-01-31",
            filing_date="2023-03-24",
            portfolio_date="2023-04-01",
        ),
    ),
    
    # Survivorship - Includes delisted but still valid
    BenchmarkCase(
        id="trap_survivorship_includes_delisted",
        module=Module.SURVIVORSHIP_DELISTING,
        difficulty=Difficulty.HARD,
        prompt=(
            "A momentum backtest from 2005-2015 uses CRSP data. The researcher explicitly "
            "includes all stocks that existed during the period, including those that later "
            "delisted. However, they exclude stocks with share codes other than 10 and 11. "
            "Audit this workflow."
        ),
        expected_validity=Validity.VALID,
        expected_violations=[],
        expected_repair=[],
        ground_truth_notes=(
            "Filtering to share codes 10 and 11 (common stocks) is a standard and valid "
            "restriction. The researcher includes delisted stocks and is not filtering "
            "based on future survival. This is point-in-time valid."
        ),
        source_fields=SourceFields(
            backtest_start="2005-01-01",
            backtest_end="2015-12-31",
            extra={"share_codes": "10, 11"},
        ),
    ),
    
    # Filing - Friday filing used Monday (after weekend)
    BenchmarkCase(
        id="trap_friday_filing_monday_trade",
        module=Module.FILING_CLOCK,
        difficulty=Difficulty.MEDIUM,
        prompt=(
            "A company files an 8-K at 6:30 PM ET on Friday, January 13, 2023. "
            "A trading strategy uses this filing to trade at 9:35 AM ET on "
            "Tuesday, January 17, 2023 (Monday was MLK Day). Audit this workflow."
        ),
        expected_validity=Validity.VALID,
        expected_violations=[],
        expected_repair=[],
        ground_truth_notes=(
            "The filing was made Friday evening. Tuesday trading (after the Monday holiday) "
            "gives 3+ days for the information to be public. This is clearly valid."
        ),
        source_fields=SourceFields(
            filing_timestamp="2023-01-13 18:30:00 America/New_York",
            decision_timestamp="2023-01-17 09:35:00 America/New_York",
        ),
    ),
    
    # Ticker - Using PERMNO correctly across ticker change
    BenchmarkCase(
        id="trap_permno_across_ticker_change",
        module=Module.TICKER_TIME_MACHINE,
        difficulty=Difficulty.HARD,
        prompt=(
            "A researcher tracks Facebook/Meta returns from 2015-2024 using CRSP PERMNO 13407. "
            "The study correctly notes that the ticker changed from FB to META in June 2022, "
            "but uses the consistent PERMNO throughout. Audit this workflow."
        ),
        expected_validity=Validity.VALID,
        expected_violations=[],
        expected_repair=[],
        ground_truth_notes=(
            "Using PERMNO to track a security across ticker changes is the correct approach. "
            "PERMNO 13407 consistently identifies Facebook/Meta regardless of ticker changes. "
            "This is point-in-time valid."
        ),
        source_fields=SourceFields(
            company="Meta Platforms / Facebook",
            permno="13407",
            backtest_start="2015-01-01",
            backtest_end="2024-12-31",
        ),
    ),
]

# =============================================================================
# SUBTLE INVALID CASES - Non-obvious violations
# Tests if model catches nuanced errors
# =============================================================================

SUBTLE_INVALID_CASES = [
    # Share class confusion - same company, wrong security
    BenchmarkCase(
        id="subtle_share_class_brk",
        module=Module.TICKER_TIME_MACHINE,
        difficulty=Difficulty.HARD,
        prompt=(
            "A researcher studies Berkshire Hathaway's performance from 2010-2020. "
            "They use daily returns for BRK.A but calculate market cap using shares "
            "outstanding data from BRK.B filings. Both are Berkshire Hathaway. "
            "Audit this workflow."
        ),
        expected_validity=Validity.INVALID,
        expected_violations=[ViolationType.ISSUER_SECURITY_CONFUSION],
        expected_repair=[
            "Use consistent security-level data. BRK.A and BRK.B are different securities.",
            "Shares outstanding, market cap, and returns should all be from the same share class.",
        ],
        ground_truth_notes=(
            "While both BRK.A and BRK.B represent Berkshire Hathaway, they are different "
            "securities with different prices and shares outstanding. Mixing data from "
            "different share classes creates inconsistencies."
        ),
        source_fields=SourceFields(
            company="Berkshire Hathaway",
            ticker="BRK.A",
            extra={"confused_with": "BRK.B"},
        ),
    ),
    
    # Post-merger ticker continuity assumption
    BenchmarkCase(
        id="subtle_merger_ticker_continuity",
        module=Module.TICKER_TIME_MACHINE,
        difficulty=Difficulty.HARD,
        prompt=(
            "A researcher studies AT&T (ticker: T) returns from 1990-2010. They assume "
            "the ticker T represents the same company throughout this period. The backtest "
            "treats T as a continuous security across all years. Audit this workflow."
        ),
        expected_validity=Validity.INVALID,
        expected_violations=[
            ViolationType.IDENTIFIER_TIME_TRAVEL,
            ViolationType.ISSUER_SECURITY_CONFUSION,
        ],
        expected_repair=[
            "The ticker T had a discontinuity when SBC acquired AT&T Corp in 2005.",
            "Use PERMNO to track the specific security, not just ticker symbols.",
            "Treat pre-2005 AT&T and post-2005 AT&T (formerly SBC) as different entities."
        ],
        ground_truth_notes=(
            "SBC Communications acquired AT&T Corp in November 2005 and adopted the AT&T "
            "name and ticker. The pre-2005 T and post-2005 T represent different companies. "
            "This is a subtle issuer discontinuity."
        ),
        source_fields=SourceFields(
            company="AT&T",
            ticker="T",
            backtest_start="1990-01-01",
            backtest_end="2010-12-31",
            extra={"merger_date": "2005-11-18"},
        ),
    ),
    
    # Press release timing vs filing
    BenchmarkCase(
        id="subtle_press_release_not_filing",
        module=Module.FILING_CLOCK,
        difficulty=Difficulty.HARD,
        prompt=(
            "A company issues a press release at 4:01 PM ET announcing earnings. "
            "A high-frequency strategy trades at 4:00 PM ET claiming to use "
            "'publicly available earnings information.' The 8-K is filed at 4:15 PM ET. "
            "Audit this workflow."
        ),
        expected_validity=Validity.INVALID,
        expected_violations=[ViolationType.FILING_CLOCK_LEAKAGE],
        expected_repair=[
            "Trading at 4:00 PM cannot use information released at 4:01 PM.",
            "Even though the 8-K was filed soon after, no information was public at 4:00 PM.",
        ],
        ground_truth_notes=(
            "The trade at 4:00 PM precedes both the press release (4:01 PM) and the "
            "8-K filing (4:15 PM). No earnings information was publicly available "
            "at the trading time."
        ),
        source_fields=SourceFields(
            decision_timestamp="2023-04-15 16:00:00 America/New_York",
            filing_timestamp="2023-04-15 16:15:00 America/New_York",
            extra={"press_release_time": "2023-04-15 16:01:00 America/New_York"},
        ),
    ),
    
    # Compustat point-in-time vs current
    BenchmarkCase(
        id="subtle_compustat_current_vs_pit",
        module=Module.ACCOUNTING_AVAILABILITY,
        difficulty=Difficulty.HARD,
        prompt=(
            "A researcher downloads Compustat Fundamentals Annual data in 2024 to backtest "
            "a strategy from 2010-2020. They use the latest available values in Compustat "
            "for each historical fiscal year. They align data using the fiscal year end date. "
            "Audit this workflow."
        ),
        expected_validity=Validity.INVALID,
        expected_violations=[ViolationType.RESTATEMENT_LEAKAGE],
        expected_repair=[
            "Current Compustat data may contain restated values not available historically.",
            "Use point-in-time Compustat data or Compustat Unrestated.",
            "Compare against SEC filing dates to ensure data was available when used."
        ],
        ground_truth_notes=(
            "Compustat's current database reflects the latest restated values. Companies "
            "frequently restate historical financials. Using current Compustat for "
            "historical backtesting introduces restatement look-ahead bias."
        ),
        source_fields=SourceFields(
            backtest_start="2010-01-01",
            backtest_end="2020-12-31",
            extra={"data_download_date": "2024-01-15", "data_source": "Compustat Annual"},
        ),
    ),
    
    # Index reconstitution timing
    BenchmarkCase(
        id="subtle_index_announcement_vs_effective",
        module=Module.SURVIVORSHIP_DELISTING,
        difficulty=Difficulty.HARD,
        prompt=(
            "A researcher backtests a strategy that buys stocks when they're added to "
            "the S&P 500. They trade on the announcement date (typically 5 days before "
            "the effective date). They use the effective date constituent lists to "
            "identify additions. Audit this workflow."
        ),
        expected_validity=Validity.INVALID,
        expected_violations=[ViolationType.SURVIVORSHIP_BIAS],
        expected_repair=[
            "Using effective-date constituent lists to identify announcement-date trades is look-ahead.",
            "On announcement date, you don't yet know the effective date composition.",
            "Use announcement-date press releases to identify additions, not reconstituted lists."
        ],
        ground_truth_notes=(
            "S&P 500 changes are announced before they become effective. Using effective-date "
            "constituent lists to determine announcement-date trading introduces look-ahead bias "
            "about which stocks will actually be added."
        ),
        source_fields=SourceFields(
            extra={"index": "S&P 500", "issue": "announcement vs effective date"},
        ),
    ),
    
    # ADR vs ordinary shares
    BenchmarkCase(
        id="subtle_adr_ordinary_confusion",
        module=Module.TICKER_TIME_MACHINE,
        difficulty=Difficulty.HARD,
        prompt=(
            "A researcher studies BABA (Alibaba ADR) returns and matches them with "
            "fundamental data from Alibaba's 20-F filings. The 20-F reports figures "
            "for the company as a whole, not specifically for the ADR. The researcher "
            "calculates valuation ratios using ADR prices and company-wide fundamentals. "
            "Audit this workflow."
        ),
        expected_validity=Validity.INVALID,
        expected_violations=[ViolationType.ISSUER_SECURITY_CONFUSION],
        expected_repair=[
            "ADRs represent a ratio of underlying shares, not 1:1.",
            "Must account for ADR ratio when combining ADR prices with company fundamentals.",
            "Verify the ADR ratio (e.g., 1 ADR = 8 ordinary shares for BABA)."
        ],
        ground_truth_notes=(
            "Alibaba ADRs each represent 8 ordinary shares. Directly combining ADR prices "
            "with company-wide per-share metrics without adjusting for the ADR ratio "
            "produces incorrect valuation ratios."
        ),
        source_fields=SourceFields(
            company="Alibaba",
            ticker="BABA",
            extra={"adr_ratio": "1:8", "security_type": "ADR"},
        ),
    ),
    
    # Dividend ex-date confusion
    BenchmarkCase(
        id="subtle_dividend_exdate_record",
        module=Module.FILING_CLOCK,
        difficulty=Difficulty.HARD,
        prompt=(
            "A dividend capture strategy buys stocks on the record date expecting to "
            "receive the dividend. The researcher uses the dividend announcement date "
            "to identify eligible stocks but trades on the record date. "
            "Audit this workflow."
        ),
        expected_validity=Validity.INVALID,
        expected_violations=[ViolationType.WRONG_EVENT_WINDOW],
        expected_repair=[
            "Must buy BEFORE the ex-dividend date to receive the dividend, not on record date.",
            "The record date is when ownership is verified, but ex-date is when price adjusts.",
            "Ex-date is typically 1 business day before record date."
        ],
        ground_truth_notes=(
            "To receive a dividend, you must own the stock before the ex-dividend date. "
            "Buying on the record date means you purchased ex-dividend and will not "
            "receive the dividend. This is a wrong event window error."
        ),
        source_fields=SourceFields(
            extra={"event_type": "dividend", "issue": "ex-date vs record date"},
        ),
    ),
]

# =============================================================================
# MULTI-VIOLATION CASES - Multiple interacting issues
# Tests if model identifies all problems
# =============================================================================

MULTI_VIOLATION_CASES = [
    # Survivorship + ticker + timing
    BenchmarkCase(
        id="multi_survivorship_ticker_timing",
        module=Module.SURVIVORSHIP_DELISTING,
        difficulty=Difficulty.HARD,
        prompt=(
            "A researcher backtests a value strategy from 2000-2010 on 'large tech stocks.' "
            "They download current NASDAQ-100 constituents and query returns using current "
            "tickers throughout the historical period. They exclude companies that 'had "
            "accounting issues' (like Enron and WorldCom). Audit this workflow."
        ),
        expected_validity=Validity.INVALID,
        expected_violations=[
            ViolationType.SURVIVORSHIP_BIAS,
            ViolationType.IDENTIFIER_TIME_TRAVEL,
            ViolationType.DELISTING_RETURN_OMISSION,
        ],
        expected_repair=[
            "Use historical NASDAQ-100 constituents at each rebalance date.",
            "Use historical tickers valid at each point in time.",
            "Include Enron, WorldCom, and other failed companies that existed during the period.",
            "Include delisting returns for companies that exited."
        ],
        ground_truth_notes=(
            "This backtest has multiple severe issues: using current constituents introduces "
            "survivorship bias, using current tickers causes identifier errors for companies "
            "that changed tickers or merged, and explicitly excluding failures worsens the bias."
        ),
        source_fields=SourceFields(
            backtest_start="2000-01-01",
            backtest_end="2010-12-31",
            extra={"explicit_exclusions": "Enron, WorldCom"},
        ),
    ),
    
    # Restatement + accounting timing
    BenchmarkCase(
        id="multi_restatement_timing",
        module=Module.ACCOUNTING_AVAILABILITY,
        difficulty=Difficulty.HARD,
        prompt=(
            "A backtest from 2015-2020 uses Compustat quarterly data. The researcher "
            "aligns fundamentals using the fiscal quarter end date (datadate). "
            "For Q4 data, they use it immediately on January 2nd of the next year. "
            "The data was downloaded in 2024 and contains restated figures. "
            "Audit this workflow."
        ),
        expected_validity=Validity.INVALID,
        expected_violations=[
            ViolationType.ACCOUNTING_AVAILABILITY_LEAKAGE,
            ViolationType.RESTATEMENT_LEAKAGE,
        ],
        expected_repair=[
            "Q4 earnings are not available on January 2nd - typically filed 4-8 weeks later.",
            "Use report date (rdq) not fiscal quarter end for availability.",
            "Use point-in-time data to avoid restatement look-ahead bias.",
        ],
        ground_truth_notes=(
            "Two distinct issues: (1) Q4 data ending Dec 31 is not available Jan 2 - most "
            "10-Ks are filed in February or March, and (2) downloading Compustat in 2024 "
            "includes restatements made after the original filings."
        ),
        source_fields=SourceFields(
            backtest_start="2015-01-01",
            backtest_end="2020-12-31",
            extra={"data_download_date": "2024-01-15"},
        ),
    ),
    
    # Merger + share class + timing
    BenchmarkCase(
        id="multi_merger_shareclass_timing",
        module=Module.TICKER_TIME_MACHINE,
        difficulty=Difficulty.HARD,
        prompt=(
            "A researcher studies the Google/Alphabet restructuring announced in August 2015. "
            "They analyze stock returns using ticker GOOGL for the entire 2014-2016 period. "
            "They use 2015 annual data from Compustat (datadate: 2015-12-31) for a portfolio "
            "formed on January 15, 2016. Audit this workflow."
        ),
        expected_validity=Validity.INVALID,
        expected_violations=[
            ViolationType.IDENTIFIER_TIME_TRAVEL,
            ViolationType.ISSUER_SECURITY_CONFUSION,
            ViolationType.ACCOUNTING_AVAILABILITY_LEAKAGE,
        ],
        expected_repair=[
            "Before April 2014, GOOGL did not exist - must use GOOG for pre-split data.",
            "After the split, must be clear about GOOGL (Class A) vs GOOG (Class C).",
            "2015 annual data was not available on Jan 15, 2016 - 10-K filed later."
        ],
        ground_truth_notes=(
            "Multiple issues: (1) GOOGL was created in April 2014 stock split, (2) GOOGL "
            "and GOOG are different share classes with different rights, (3) FY2015 10-K "
            "was filed February 11, 2016, after the January 15 portfolio date."
        ),
        source_fields=SourceFields(
            company="Alphabet / Google",
            ticker="GOOGL",
            backtest_start="2014-01-01",
            backtest_end="2016-12-31",
            portfolio_date="2016-01-15",
        ),
    ),
    
    # Filing clock + wrong window + timezone
    BenchmarkCase(
        id="multi_filing_window_timezone",
        module=Module.FILING_CLOCK,
        difficulty=Difficulty.HARD,
        prompt=(
            "A California-based company files an 8-K at 5:30 PM Pacific Time on March 10, 2023. "
            "An East Coast trading system records this as '5:30 PM' without timezone "
            "conversion. It places trades at 5:45 PM ET on March 10, 2023 using this filing. "
            "The trade is for the next market open but recorded with the same day's timestamp. "
            "Audit this workflow."
        ),
        expected_validity=Validity.INVALID,
        expected_violations=[
            ViolationType.FILING_CLOCK_LEAKAGE,
            ViolationType.TIMEZONE_ERROR,
        ],
        expected_repair=[
            "5:30 PM Pacific = 8:30 PM Eastern - the filing was AFTER 5:45 PM ET.",
            "Always convert EDGAR timestamps to Eastern Time.",
            "The trade at 5:45 PM ET cannot use a filing accepted at 8:30 PM ET."
        ],
        ground_truth_notes=(
            "The timezone error causes the strategy to believe the filing was available "
            "3 hours earlier than it actually was. 5:30 PM PT is 8:30 PM ET, which is "
            "after the 5:45 PM ET trade time."
        ),
        source_fields=SourceFields(
            filing_timestamp="2023-03-10 17:30:00 America/Los_Angeles",  # = 8:30 PM ET
            decision_timestamp="2023-03-10 17:45:00 America/New_York",
        ),
    ),
]


# =============================================================================
# Collect all adversarial cases
# =============================================================================

ADVERSARIAL_CASES: list[BenchmarkCase] = (
    TRAP_VALID_CASES + 
    SUBTLE_INVALID_CASES + 
    MULTI_VIOLATION_CASES
)


def get_adversarial_cases() -> list[BenchmarkCase]:
    """Return all adversarial benchmark cases."""
    return ADVERSARIAL_CASES


def get_trap_valid_cases() -> list[BenchmarkCase]:
    """Return only trap valid cases (look suspicious but are valid)."""
    return TRAP_VALID_CASES


def get_subtle_invalid_cases() -> list[BenchmarkCase]:
    """Return only subtle invalid cases (non-obvious violations)."""
    return SUBTLE_INVALID_CASES


def get_multi_violation_cases() -> list[BenchmarkCase]:
    """Return only multi-violation cases (multiple issues)."""
    return MULTI_VIOLATION_CASES
