"""
Benchmark case construction utilities.

Provides factory functions for creating benchmark cases and utilities
for generating the full benchmark dataset.
"""

from typing import Optional

import jsonlines
from pathlib import Path

from backtest_lie_detector.schemas import (
    BenchmarkCase,
    Difficulty,
    Module,
    SourceFields,
    Validity,
    ViolationType,
)


def create_ticker_time_machine_case(
    id: str,
    prompt: str,
    expected_validity: Validity,
    expected_violations: list[ViolationType],
    expected_repair: list[str],
    ground_truth_notes: str,
    difficulty: Difficulty = Difficulty.MEDIUM,
    company: Optional[str] = None,
    event_date: Optional[str] = None,
    ticker: Optional[str] = None,
    bad_ticker: Optional[str] = None,
    historical_ticker: Optional[str] = None,
    **extra_fields,
) -> BenchmarkCase:
    """Create a Ticker Time Machine benchmark case."""
    return BenchmarkCase(
        id=id,
        module=Module.TICKER_TIME_MACHINE,
        difficulty=difficulty,
        prompt=prompt,
        expected_validity=expected_validity,
        expected_violations=expected_violations,
        expected_repair=expected_repair,
        ground_truth_notes=ground_truth_notes,
        source_fields=SourceFields(
            company=company,
            event_date=event_date,
            ticker=ticker,
            bad_ticker=bad_ticker,
            historical_ticker=historical_ticker,
            extra=extra_fields if extra_fields else None,
        ),
        data_source="manual",
    )


def create_filing_clock_case(
    id: str,
    prompt: str,
    expected_validity: Validity,
    expected_violations: list[ViolationType],
    expected_repair: list[str],
    ground_truth_notes: str,
    difficulty: Difficulty = Difficulty.MEDIUM,
    decision_timestamp: Optional[str] = None,
    filing_timestamp: Optional[str] = None,
    **extra_fields,
) -> BenchmarkCase:
    """Create a Filing Clock Challenge benchmark case."""
    return BenchmarkCase(
        id=id,
        module=Module.FILING_CLOCK,
        difficulty=difficulty,
        prompt=prompt,
        expected_validity=expected_validity,
        expected_violations=expected_violations,
        expected_repair=expected_repair,
        ground_truth_notes=ground_truth_notes,
        source_fields=SourceFields(
            decision_timestamp=decision_timestamp,
            filing_timestamp=filing_timestamp,
            extra=extra_fields if extra_fields else None,
        ),
        data_source="manual",
    )


def create_accounting_availability_case(
    id: str,
    prompt: str,
    expected_validity: Validity,
    expected_violations: list[ViolationType],
    expected_repair: list[str],
    ground_truth_notes: str,
    difficulty: Difficulty = Difficulty.MEDIUM,
    portfolio_date: Optional[str] = None,
    fiscal_year_end: Optional[str] = None,
    filing_date: Optional[str] = None,
    **extra_fields,
) -> BenchmarkCase:
    """Create an Accounting Availability Trap benchmark case."""
    return BenchmarkCase(
        id=id,
        module=Module.ACCOUNTING_AVAILABILITY,
        difficulty=difficulty,
        prompt=prompt,
        expected_validity=expected_validity,
        expected_violations=expected_violations,
        expected_repair=expected_repair,
        ground_truth_notes=ground_truth_notes,
        source_fields=SourceFields(
            portfolio_date=portfolio_date,
            fiscal_year_end=fiscal_year_end,
            filing_date=filing_date,
            extra=extra_fields if extra_fields else None,
        ),
        data_source="manual",
    )


def create_survivorship_case(
    id: str,
    prompt: str,
    expected_validity: Validity,
    expected_violations: list[ViolationType],
    expected_repair: list[str],
    ground_truth_notes: str,
    difficulty: Difficulty = Difficulty.MEDIUM,
    backtest_start: Optional[str] = None,
    backtest_end: Optional[str] = None,
    universe_filter: Optional[str] = None,
    **extra_fields,
) -> BenchmarkCase:
    """Create a Survivorship and Delisting Trap benchmark case."""
    return BenchmarkCase(
        id=id,
        module=Module.SURVIVORSHIP_DELISTING,
        difficulty=difficulty,
        prompt=prompt,
        expected_validity=expected_validity,
        expected_violations=expected_violations,
        expected_repair=expected_repair,
        ground_truth_notes=ground_truth_notes,
        source_fields=SourceFields(
            backtest_start=backtest_start,
            backtest_end=backtest_end,
            universe_filter=universe_filter,
            extra=extra_fields if extra_fields else None,
        ),
        data_source="manual",
    )


def save_benchmark(cases: list[BenchmarkCase], path: str) -> None:
    """Save benchmark cases to a JSONL file."""
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    
    with jsonlines.open(path, mode="w") as writer:
        for case in cases:
            writer.write(case.model_dump(mode="json"))
    
    print(f"Saved {len(cases)} cases to {path}")


def load_benchmark(path: str) -> list[BenchmarkCase]:
    """Load benchmark cases from a JSONL file."""
    cases = []
    with jsonlines.open(path, mode="r") as reader:
        for obj in reader:
            cases.append(BenchmarkCase.model_validate(obj))
    return cases


# =============================================================================
# Additional benchmark cases beyond the seed cases
# =============================================================================

ADDITIONAL_TICKER_CASES = [
    create_ticker_time_machine_case(
        id="ttm_twitter_x_2020",
        prompt=(
            "A researcher studies Twitter's earnings announcement on October 29, 2020 "
            "and queries stock returns using ticker X. Audit this workflow."
        ),
        expected_validity=Validity.INVALID,
        expected_violations=[ViolationType.IDENTIFIER_TIME_TRAVEL],
        expected_repair=[
            "Twitter traded under ticker TWTR until the company was acquired in 2022.",
            "X as a ticker for Twitter/X Corp did not exist in 2020.",
            "Use TWTR for events before the October 2022 acquisition."
        ],
        ground_truth_notes=(
            "Twitter traded under ticker TWTR from its IPO in 2013 until October 2022 "
            "when Elon Musk acquired the company and took it private. The ticker X "
            "did not exist for this company in 2020."
        ),
        difficulty=Difficulty.EASY,
        company="Twitter / X Corp",
        event_date="2020-10-29",
        bad_ticker="X",
        historical_ticker="TWTR",
    ),
    create_ticker_time_machine_case(
        id="ttm_kraft_mondelez_2010",
        prompt=(
            "A researcher analyzes Kraft Foods' financial performance in 2010 using "
            "ticker MDLZ. Audit this workflow for point-in-time validity."
        ),
        expected_validity=Validity.INVALID,
        expected_violations=[ViolationType.IDENTIFIER_TIME_TRAVEL, ViolationType.ISSUER_SECURITY_CONFUSION],
        expected_repair=[
            "Kraft Foods traded under ticker KFT until the 2012 spinoff.",
            "MDLZ (Mondelez) was created in the October 2012 spinoff.",
            "Track the specific security through the corporate action using CUSIP or PERMNO."
        ],
        ground_truth_notes=(
            "Kraft Foods split into two companies in October 2012: Kraft Foods Group (KRFT) "
            "and Mondelez International (MDLZ). In 2010, only KFT existed."
        ),
        difficulty=Difficulty.MEDIUM,
        company="Kraft Foods / Mondelez",
        event_date="2010-12-31",
        bad_ticker="MDLZ",
        historical_ticker="KFT",
    ),
    create_ticker_time_machine_case(
        id="ttm_valid_microsoft",
        prompt=(
            "A researcher studies Microsoft's antitrust ruling on April 3, 2000 and "
            "queries daily returns using ticker MSFT. Audit this workflow."
        ),
        expected_validity=Validity.VALID,
        expected_violations=[],
        expected_repair=[],
        ground_truth_notes=(
            "Microsoft has traded under ticker MSFT continuously since its IPO in 1986. "
            "Using MSFT for the year 2000 antitrust event is point-in-time valid."
        ),
        difficulty=Difficulty.EASY,
        company="Microsoft Corporation",
        event_date="2000-04-03",
        ticker="MSFT",
    ),
    create_ticker_time_machine_case(
        id="ttm_ge_spinoffs_2021",
        prompt=(
            "A researcher backtests a conglomerate strategy from 2015-2023 using ticker GE "
            "to represent General Electric throughout the entire period. The backtest treats "
            "GE as a single continuous security. Audit this workflow."
        ),
        expected_validity=Validity.INVALID,
        expected_violations=[ViolationType.ISSUER_SECURITY_CONFUSION],
        expected_repair=[
            "GE underwent major spinoffs: GE Healthcare (GEHC) in 2023 and GE Vernova in 2024.",
            "The current GE (now GE Aerospace) is a different business than historical GE.",
            "Properly account for spinoff distributions and track each resulting security."
        ],
        ground_truth_notes=(
            "General Electric spun off GE Healthcare in January 2023 and GE Vernova in April 2024. "
            "The remaining company became GE Aerospace. Treating GE as continuous ignores these "
            "corporate actions and the value distributed to shareholders."
        ),
        difficulty=Difficulty.HARD,
        company="General Electric",
        backtest_start="2015-01-01",
        backtest_end="2023-12-31",
        ticker="GE",
    ),
    create_ticker_time_machine_case(
        id="ttm_worldcom_mci_2000",
        prompt=(
            "A researcher studies returns for telecommunications companies in 2000 and "
            "includes WorldCom using ticker WCOM. The backtest extends through 2010. "
            "Audit this workflow."
        ),
        expected_validity=Validity.INVALID,
        expected_violations=[ViolationType.IDENTIFIER_TIME_TRAVEL, ViolationType.SURVIVORSHIP_BIAS],
        expected_repair=[
            "WorldCom filed for bankruptcy in July 2002 and was delisted.",
            "The company emerged as MCI Inc. before being acquired by Verizon in 2006.",
            "Handle the delisting properly and do not extend WCOM beyond its trading period."
        ],
        ground_truth_notes=(
            "WorldCom collapsed in the accounting scandal of 2002. It was delisted after "
            "bankruptcy and eventually merged into Verizon. WCOM cannot be queried for 2010."
        ),
        difficulty=Difficulty.HARD,
        company="WorldCom / MCI",
        event_date="2000-06-30",
        backtest_end="2010-12-31",
        ticker="WCOM",
    ),
    create_ticker_time_machine_case(
        id="ttm_berkshire_share_class",
        prompt=(
            "A researcher queries Berkshire Hathaway returns from 1990-2020 using only "
            "ticker BRK.B throughout. Audit this workflow."
        ),
        expected_validity=Validity.INVALID,
        expected_violations=[ViolationType.IDENTIFIER_TIME_TRAVEL],
        expected_repair=[
            "BRK.B (Class B shares) was created in 1996.",
            "For pre-1996 data, use BRK.A or BRK (the original single class).",
            "Be explicit about which share class is being studied."
        ],
        ground_truth_notes=(
            "Berkshire Hathaway Class B shares (BRK.B) were created in May 1996. "
            "Before that date, only Class A shares (BRK or BRK.A) existed."
        ),
        difficulty=Difficulty.MEDIUM,
        company="Berkshire Hathaway",
        backtest_start="1990-01-01",
        backtest_end="2020-12-31",
        ticker="BRK.B",
    ),
    create_ticker_time_machine_case(
        id="ttm_aol_time_warner",
        prompt=(
            "A researcher studies the AOL Time Warner merger announced January 10, 2000 "
            "and tracks returns for ticker TWX from 1998 through 2005. Audit this workflow."
        ),
        expected_validity=Validity.INVALID,
        expected_violations=[ViolationType.ISSUER_SECURITY_CONFUSION],
        expected_repair=[
            "TWX represented Time Warner before the merger but AOL Time Warner after.",
            "Track the merger carefully: AOL (AOL) and Time Warner (TWX) merged in 2001.",
            "Consider whether you're tracking the acquirer, target, or combined entity."
        ],
        ground_truth_notes=(
            "The AOL Time Warner merger was one of the largest and most disastrous in history. "
            "After the merger in 2001, the combined company traded under AOL/TWX. "
            "Time Warner later spun off AOL in 2009. The security representation changed."
        ),
        difficulty=Difficulty.HARD,
        company="AOL Time Warner",
        event_date="2000-01-10",
        ticker="TWX",
    ),
]

ADDITIONAL_FILING_CASES = [
    create_filing_clock_case(
        id="filing_clock_10q_same_day",
        prompt=(
            "A company files its 10-Q at 8:45 AM ET on May 5, 2022. A trading algorithm "
            "processes this filing and places a trade at 9:35 AM ET the same day. "
            "Audit this workflow."
        ),
        expected_validity=Validity.VALID,
        expected_violations=[],
        expected_repair=[],
        ground_truth_notes=(
            "The 10-Q was filed at 8:45 AM, and the trade occurs at 9:35 AM, "
            "50 minutes after the filing. The filing was publicly available. Valid."
        ),
        difficulty=Difficulty.EASY,
        decision_timestamp="2022-05-05 09:35:00 America/New_York",
        filing_timestamp="2022-05-05 08:45:00 America/New_York",
        filing_type="10-Q",
    ),
    create_filing_clock_case(
        id="filing_clock_8k_5pm",
        prompt=(
            "An 8-K announcing material news is accepted by EDGAR at 5:15 PM ET on "
            "Tuesday, March 14, 2023. A trading strategy uses this news to trade at "
            "9:30 AM ET on Wednesday, March 15, 2023. Audit this workflow."
        ),
        expected_validity=Validity.VALID,
        expected_violations=[],
        expected_repair=[],
        ground_truth_notes=(
            "The 8-K was filed after market close on Tuesday. Trading at Wednesday's "
            "open gives adequate time for the information to be processed. Valid."
        ),
        difficulty=Difficulty.EASY,
        decision_timestamp="2023-03-15 09:30:00 America/New_York",
        filing_timestamp="2023-03-14 17:15:00 America/New_York",
        filing_type="8-K",
    ),
    create_filing_clock_case(
        id="filing_clock_press_release_before_filing",
        prompt=(
            "A company issues a press release at 4:05 PM ET announcing earnings. The "
            "corresponding 8-K is filed at 4:45 PM ET. A strategy trades at 4:20 PM "
            "based on the 8-K filing content. Audit this workflow."
        ),
        expected_validity=Validity.INVALID,
        expected_violations=[ViolationType.FILING_CLOCK_LEAKAGE],
        expected_repair=[
            "The strategy cannot use the 8-K content at 4:20 PM if it was filed at 4:45 PM.",
            "Either use the press release (if that's the actual source) or wait for the filing.",
            "Clearly distinguish between press release timing and EDGAR filing timing."
        ],
        ground_truth_notes=(
            "While the press release was out at 4:05 PM, the workflow claims to use "
            "the 8-K which wasn't filed until 4:45 PM. This is filing clock leakage."
        ),
        difficulty=Difficulty.MEDIUM,
        decision_timestamp="2023-02-01 16:20:00 America/New_York",
        filing_timestamp="2023-02-01 16:45:00 America/New_York",
        filing_type="8-K",
        press_release_time="2023-02-01 16:05:00 America/New_York",
    ),
    create_filing_clock_case(
        id="filing_clock_amended_10k",
        prompt=(
            "A researcher uses data from a 10-K/A (amended 10-K) filed on April 30, 2022 "
            "for a portfolio formed on March 15, 2022. The original 10-K was filed on "
            "February 28, 2022. Audit this workflow."
        ),
        expected_validity=Validity.INVALID,
        expected_violations=[ViolationType.FILING_CLOCK_LEAKAGE],
        expected_repair=[
            "Amended filing (10-K/A) data was not available until April 30, 2022.",
            "For March 15, 2022 portfolio, only the original 10-K data from Feb 28 was available.",
            "Use the original filing for point-in-time accuracy."
        ],
        ground_truth_notes=(
            "Amended filings contain corrections or additional information added after "
            "the original filing. Using 10-K/A data from April for a March portfolio is "
            "look-ahead bias."
        ),
        difficulty=Difficulty.MEDIUM,
        decision_timestamp="2022-03-15",
        filing_timestamp="2022-04-30",
        original_filing_date="2022-02-28",
        filing_type="10-K/A",
    ),
    create_filing_clock_case(
        id="filing_clock_foreign_issuer_20f",
        prompt=(
            "A researcher uses annual financial data from Alibaba's 20-F filed on "
            "July 22, 2022 for a portfolio formed on April 15, 2022. Alibaba's fiscal year "
            "ends March 31. Audit this workflow."
        ),
        expected_validity=Validity.INVALID,
        expected_violations=[ViolationType.FILING_CLOCK_LEAKAGE, ViolationType.ACCOUNTING_AVAILABILITY_LEAKAGE],
        expected_repair=[
            "Foreign private issuers file 20-F up to 4 months after fiscal year end.",
            "FY2022 (ending March 31) 20-F wasn't filed until July 2022.",
            "Use only data from the previous year's 20-F for the April portfolio."
        ],
        ground_truth_notes=(
            "Alibaba's fiscal year 2022 ended March 31, 2022. The 20-F with this data "
            "wasn't filed until July 22, 2022. April 15 is before this filing."
        ),
        difficulty=Difficulty.HARD,
        decision_timestamp="2022-04-15",
        filing_timestamp="2022-07-22",
        fiscal_year_end="2022-03-31",
        filing_type="20-F",
        company="Alibaba",
    ),
    create_filing_clock_case(
        id="filing_clock_intraday_noon",
        prompt=(
            "An 8-K is filed at 12:15 PM ET. A high-frequency strategy places a trade "
            "at 12:14 PM ET on the same day using information it claims is from that 8-K. "
            "Audit this workflow."
        ),
        expected_validity=Validity.INVALID,
        expected_violations=[ViolationType.FILING_CLOCK_LEAKAGE],
        expected_repair=[
            "Cannot use 8-K information before it is filed.",
            "The trade at 12:14 PM precedes the 12:15 PM filing by one minute.",
            "Wait for EDGAR acceptance timestamp before trading on filing content."
        ],
        ground_truth_notes=(
            "One minute before filing acceptance, the information was not publicly available. "
            "This is a clear case of filing clock leakage, even if by only one minute."
        ),
        difficulty=Difficulty.EASY,
        decision_timestamp="2023-06-15 12:14:00 America/New_York",
        filing_timestamp="2023-06-15 12:15:00 America/New_York",
        filing_type="8-K",
    ),
    create_filing_clock_case(
        id="filing_clock_timezone_confusion",
        prompt=(
            "A company based in California files an 8-K at 3:30 PM PT (6:30 PM ET) on "
            "December 10, 2021. A strategy on the East Coast trades at 5:00 PM ET the same day, "
            "claiming the filing was already available. Audit this workflow."
        ),
        expected_validity=Validity.INVALID,
        expected_violations=[ViolationType.FILING_CLOCK_LEAKAGE, ViolationType.TIMEZONE_ERROR],
        expected_repair=[
            "EDGAR timestamps are in Eastern Time.",
            "A filing at 3:30 PM PT is 6:30 PM ET.",
            "A trade at 5:00 PM ET cannot use a filing that wasn't accepted until 6:30 PM ET."
        ],
        ground_truth_notes=(
            "Timezone confusion between Pacific and Eastern time causes a 3-hour error. "
            "The filing at 6:30 PM ET was not available for a 5:00 PM ET trade."
        ),
        difficulty=Difficulty.MEDIUM,
        decision_timestamp="2021-12-10 17:00:00 America/New_York",
        filing_timestamp="2021-12-10 18:30:00 America/New_York",
        filing_type="8-K",
    ),
]

ADDITIONAL_ACCOUNTING_CASES = [
    create_accounting_availability_case(
        id="acct_q4_earnings_january",
        prompt=(
            "A momentum strategy rebalances on January 2, 2023 using Q4 2022 earnings "
            "to rank stocks. Most companies have December fiscal year ends and report "
            "Q4 earnings in late January or February. Audit this workflow."
        ),
        expected_validity=Validity.INVALID,
        expected_violations=[ViolationType.ACCOUNTING_AVAILABILITY_LEAKAGE],
        expected_repair=[
            "Q4 earnings are typically reported 4-8 weeks after quarter end.",
            "On January 2, Q4 2022 earnings would not yet be available for most companies.",
            "Use Q3 2022 earnings (reported in October/November) for January rebalancing."
        ],
        ground_truth_notes=(
            "December quarter-end earnings are typically reported in late January "
            "through early March. Using Q4 earnings on January 2 is look-ahead bias."
        ),
        difficulty=Difficulty.EASY,
        portfolio_date="2023-01-02",
        fiscal_year_end="2022-12-31",
        filing_date="2023-02-15",
        quarter="Q4 2022",
    ),
    create_accounting_availability_case(
        id="acct_valid_6month_lag",
        prompt=(
            "A value strategy forms portfolios on July 1, 2023 using fiscal year 2022 "
            "book value data. All companies in the universe have December fiscal years "
            "and filed their 10-Ks by March 31, 2023. Audit this workflow."
        ),
        expected_validity=Validity.VALID,
        expected_violations=[],
        expected_repair=[],
        ground_truth_notes=(
            "With a July 1 portfolio date and all 10-Ks filed by March 31, there is a "
            "full 3-month buffer. The data was publicly available. Valid."
        ),
        difficulty=Difficulty.EASY,
        portfolio_date="2023-07-01",
        fiscal_year_end="2022-12-31",
        filing_date="2023-03-31",
    ),
    create_accounting_availability_case(
        id="acct_compustat_point_in_time",
        prompt=(
            "A researcher downloads Compustat annual data today and uses it to backtest "
            "a strategy from 2010-2020. The researcher uses the 'datadate' field (fiscal "
            "period end date) to determine when data was available. Audit this workflow."
        ),
        expected_validity=Validity.INVALID,
        expected_violations=[ViolationType.ACCOUNTING_AVAILABILITY_LEAKAGE],
        expected_repair=[
            "Compustat 'datadate' is fiscal period end, not information availability.",
            "Use 'rdq' (report date of quarterly) or compare to SEC filing dates.",
            "Consider using Compustat point-in-time snapshot data if available."
        ],
        ground_truth_notes=(
            "The 'datadate' field in Compustat represents fiscal period end date, not "
            "when the data became available. Typical lag is 4-8 weeks for quarterly, "
            "2-3 months for annual data."
        ),
        difficulty=Difficulty.MEDIUM,
        portfolio_date="various",
        backtest_start="2010-01-01",
        backtest_end="2020-12-31",
    ),
    create_accounting_availability_case(
        id="acct_preliminary_vs_final",
        prompt=(
            "A company announces preliminary Q3 earnings of $1.50 EPS on October 15. "
            "The final 10-Q filed November 5 shows $1.45 EPS due to adjustments. "
            "A strategy uses $1.50 for October 20 trading. Audit this workflow."
        ),
        expected_validity=Validity.VALID,
        expected_violations=[],
        expected_repair=[],
        ground_truth_notes=(
            "Using the preliminary earnings figure that was publicly announced on "
            "October 15 for October 20 trading is valid. The preliminary number was "
            "public information, even if it was later revised."
        ),
        difficulty=Difficulty.MEDIUM,
        portfolio_date="2023-10-20",
        preliminary_date="2023-10-15",
        filing_date="2023-11-05",
        preliminary_eps="1.50",
        final_eps="1.45",
    ),
    create_accounting_availability_case(
        id="acct_non_calendar_fiscal_year",
        prompt=(
            "A portfolio is formed on October 1, 2022 using fiscal year 2022 data for "
            "Apple Inc. Apple's fiscal year ends in late September. The 10-K for FY2022 "
            "was filed on October 28, 2022. Audit this workflow."
        ),
        expected_validity=Validity.INVALID,
        expected_violations=[ViolationType.ACCOUNTING_AVAILABILITY_LEAKAGE],
        expected_repair=[
            "Apple's FY2022 ended September 24, 2022.",
            "The 10-K was filed October 28, 2022.",
            "On October 1, use FY2021 data (filed October 2021) instead."
        ],
        ground_truth_notes=(
            "Apple has a non-calendar fiscal year ending in late September. "
            "FY2022 data wasn't available until the 10-K filing in late October."
        ),
        difficulty=Difficulty.MEDIUM,
        portfolio_date="2022-10-01",
        fiscal_year_end="2022-09-24",
        filing_date="2022-10-28",
        company="Apple Inc.",
    ),
    create_accounting_availability_case(
        id="acct_pro_forma_gaap",
        prompt=(
            "A strategy uses non-GAAP 'adjusted earnings' from an 8-K filed January 15 "
            "for portfolio formation on January 10. The company issued a press release "
            "with these non-GAAP figures on January 8. Audit this workflow."
        ),
        expected_validity=Validity.INVALID,
        expected_violations=[ViolationType.FILING_CLOCK_LEAKAGE],
        expected_repair=[
            "If using data from the 8-K, cannot use before January 15 filing.",
            "If using press release data, January 10 is valid (released January 8).",
            "Clarify the actual data source: press release vs. 8-K."
        ],
        ground_truth_notes=(
            "The workflow claims to use 8-K data but the 8-K wasn't filed until January 15. "
            "For January 10, could use press release data but not 8-K data."
        ),
        difficulty=Difficulty.HARD,
        portfolio_date="2023-01-10",
        filing_date="2023-01-15",
        press_release="2023-01-08",
    ),
    create_accounting_availability_case(
        id="acct_ma_target_financials",
        prompt=(
            "A researcher studies M&A returns and uses the target company's financials "
            "from their final 10-K filed 6 months before the merger announcement. "
            "The merger was announced April 1, 2022 and the 10-K was filed October 2021. "
            "Audit this workflow."
        ),
        expected_validity=Validity.VALID,
        expected_violations=[],
        expected_repair=[],
        ground_truth_notes=(
            "Using financials from a 10-K filed 6 months before the merger announcement "
            "is point-in-time valid. The data was publicly available before the event."
        ),
        difficulty=Difficulty.MEDIUM,
        event_date="2022-04-01",
        filing_date="2021-10-15",
    ),
]

ADDITIONAL_SURVIVORSHIP_CASES = [
    create_survivorship_case(
        id="survivorship_lehman_2007",
        prompt=(
            "A researcher backtests a financial sector strategy from 2005-2015 and "
            "downloads data for current financial stocks. The backtest does not include "
            "Lehman Brothers, Bear Stearns, or Washington Mutual. Audit this workflow."
        ),
        expected_validity=Validity.INVALID,
        expected_violations=[ViolationType.SURVIVORSHIP_BIAS, ViolationType.DELISTING_RETURN_OMISSION],
        expected_repair=[
            "Include Lehman Brothers (bankrupt 2008), Bear Stearns (acquired 2008), WaMu (seized 2008).",
            "Use point-in-time universe for each period.",
            "Properly account for delisting and acquisition returns."
        ],
        ground_truth_notes=(
            "Major financial institutions that failed in 2008 would have been in any "
            "2005-2007 financial sector portfolio. Excluding them introduces severe "
            "survivorship bias."
        ),
        difficulty=Difficulty.EASY,
        backtest_start="2005-01-01",
        backtest_end="2015-12-31",
        excluded_companies="Lehman Brothers, Bear Stearns, Washington Mutual",
    ),
    create_survivorship_case(
        id="survivorship_valid_pit_universe",
        prompt=(
            "A researcher backtests from 2000-2010 using CRSP monthly data. Each month, "
            "they use the share code to identify common stocks and include all stocks "
            "with valid price data for that month. Delisting returns are included. "
            "Audit this workflow."
        ),
        expected_validity=Validity.VALID,
        expected_violations=[],
        expected_repair=[],
        ground_truth_notes=(
            "Using CRSP share codes to identify securities each month and including "
            "all valid securities regardless of future status is point-in-time correct. "
            "Including delisting returns handles exits properly."
        ),
        difficulty=Difficulty.EASY,
        backtest_start="2000-01-01",
        backtest_end="2010-12-31",
        data_source="CRSP monthly",
    ),
    create_survivorship_case(
        id="survivorship_nasdaq_100",
        prompt=(
            "A researcher backtests a strategy on NASDAQ-100 stocks from 2000-2020 "
            "using the 2025 NASDAQ-100 constituents for the entire period. "
            "Audit this workflow."
        ),
        expected_validity=Validity.INVALID,
        expected_violations=[ViolationType.SURVIVORSHIP_BIAS],
        expected_repair=[
            "NASDAQ-100 composition changes quarterly.",
            "Use historical constituent lists for each period.",
            "Companies like Yahoo, Sun Microsystems were in 2000 NASDAQ-100 but not today."
        ],
        ground_truth_notes=(
            "The NASDAQ-100 has changed dramatically since 2000. Many dot-com era "
            "companies were removed. Using 2025 constituents for 2000 data excludes "
            "these companies and their returns."
        ),
        difficulty=Difficulty.MEDIUM,
        backtest_start="2000-01-01",
        backtest_end="2020-12-31",
        index="NASDAQ-100",
    ),
    create_survivorship_case(
        id="survivorship_delisting_code_handling",
        prompt=(
            "A backtest applies CRSP delisting returns but only includes returns for "
            "delisting codes 200-299 (mergers). It ignores delisting codes 400-499 "
            "(liquidation) and 500-599 (dropped). Audit this workflow."
        ),
        expected_validity=Validity.INVALID,
        expected_violations=[ViolationType.DELISTING_RETURN_OMISSION],
        expected_repair=[
            "Include delisting returns for all delisting types.",
            "Codes 400-499 (liquidation) often have large negative returns.",
            "Codes 500-599 (dropped) should also be handled appropriately."
        ],
        ground_truth_notes=(
            "Selectively applying delisting returns only to mergers while ignoring "
            "liquidations and other delistings biases results. Distressed delistings "
            "often have large negative returns that should not be ignored."
        ),
        difficulty=Difficulty.HARD,
        backtest_start="2000-01-01",
        backtest_end="2015-12-31",
        delisting_handling="only codes 200-299",
    ),
    create_survivorship_case(
        id="survivorship_penny_stock_filter",
        prompt=(
            "A researcher applies a $5 minimum price filter for a backtest from 1995-2020. "
            "The filter is applied retrospectively: if a stock ever traded below $5 during "
            "the backtest period, it is excluded from the entire backtest. "
            "Audit this workflow."
        ),
        expected_validity=Validity.INVALID,
        expected_violations=[ViolationType.SURVIVORSHIP_BIAS],
        expected_repair=[
            "Apply price filter at each rebalance date, not retrospectively.",
            "A stock at $10 in 1995 that fell to $3 by 2000 was tradeable in 1995.",
            "Retrospective filtering removes stocks based on future information."
        ],
        ground_truth_notes=(
            "Applying filters based on future price information is a form of look-ahead "
            "bias. A stock should be included when it meets criteria at each point in time."
        ),
        difficulty=Difficulty.MEDIUM,
        backtest_start="1995-01-01",
        backtest_end="2020-12-31",
        filter_type="retrospective $5 price filter",
    ),
    create_survivorship_case(
        id="survivorship_spac_lifecycle",
        prompt=(
            "A researcher studies SPAC returns from 2018-2023. The study includes only "
            "SPACs that completed a merger and are still trading as of 2025. "
            "Failed SPACs that returned capital or liquidated are excluded. "
            "Audit this workflow."
        ),
        expected_validity=Validity.INVALID,
        expected_violations=[ViolationType.SURVIVORSHIP_BIAS],
        expected_repair=[
            "Include SPACs that failed to complete mergers.",
            "Include SPACs that completed mergers but subsequently delisted.",
            "Track the full SPAC lifecycle including redemptions and liquidations."
        ],
        ground_truth_notes=(
            "Many SPACs fail to complete mergers or complete mergers that later fail. "
            "Studying only successful, surviving SPACs severely overstates SPAC returns."
        ),
        difficulty=Difficulty.HARD,
        backtest_start="2018-01-01",
        backtest_end="2023-12-31",
        universe_filter="completed merger and still trading",
    ),
    create_survivorship_case(
        id="survivorship_sector_etf_constituents",
        prompt=(
            "A researcher backtests a sector rotation strategy from 2010-2020 using "
            "holdings of current sector ETFs (XLF, XLK, etc.) to define sector membership "
            "throughout the backtest. Audit this workflow."
        ),
        expected_validity=Validity.INVALID,
        expected_violations=[ViolationType.SURVIVORSHIP_BIAS],
        expected_repair=[
            "ETF holdings change over time.",
            "Use historical ETF holdings or GICS sector classifications at each date.",
            "Account for sector reclassifications (e.g., FB moved from Tech to Communications)."
        ],
        ground_truth_notes=(
            "Using current ETF holdings for historical backtests introduces survivorship "
            "bias. Companies are added/removed from ETFs, and sector classifications change."
        ),
        difficulty=Difficulty.MEDIUM,
        backtest_start="2010-01-01",
        backtest_end="2020-12-31",
        universe_filter="current sector ETF holdings",
    ),
]


def generate_all_cases(
    include_adversarial: bool = True,
    include_wrds: bool = True,
    include_hard: bool = False
) -> list[BenchmarkCase]:
    """
    Generate the complete benchmark dataset.
    
    Combines seed cases with additional cases for each module,
    plus adversarial, WRDS-backed, and hard cases.
    
    Args:
        include_adversarial: Include adversarial cases (v2).
        include_wrds: Include WRDS data-backed cases (v2).
        include_hard: Include genuinely hard source-backed cases (v3).
    
    Returns:
        List of all benchmark cases.
    """
    from backtest_lie_detector.benchmark.examples import SEED_CASES
    
    all_cases = list(SEED_CASES)
    all_cases.extend(ADDITIONAL_TICKER_CASES)
    all_cases.extend(ADDITIONAL_FILING_CASES)
    all_cases.extend(ADDITIONAL_ACCOUNTING_CASES)
    all_cases.extend(ADDITIONAL_SURVIVORSHIP_CASES)
    
    # Add adversarial cases (v2)
    if include_adversarial:
        try:
            from backtest_lie_detector.benchmark.adversarial_cases import ADVERSARIAL_CASES
            all_cases.extend(ADVERSARIAL_CASES)
        except ImportError:
            pass
    
    # Add WRDS-backed cases (v2)
    if include_wrds:
        try:
            from backtest_lie_detector.benchmark.wrds_cases import WRDS_BACKED_CASES
            all_cases.extend(WRDS_BACKED_CASES)
        except ImportError:
            pass
    
    # Add hard source-backed cases (v3)
    if include_hard:
        try:
            from backtest_lie_detector.benchmark.hard_cases import HARD_CASES
            all_cases.extend(HARD_CASES)
        except ImportError:
            pass
    
    # Ensure unique IDs
    ids = [c.id for c in all_cases]
    if len(ids) != len(set(ids)):
        duplicates = [id for id in ids if ids.count(id) > 1]
        raise ValueError(f"Duplicate case IDs found: {set(duplicates)}")
    
    return all_cases


def generate_v1_cases() -> list[BenchmarkCase]:
    """Generate original v1 benchmark (42 cases)."""
    return generate_all_cases(include_adversarial=False, include_wrds=False, include_hard=False)


def generate_v2_cases() -> list[BenchmarkCase]:
    """Generate enhanced v2 benchmark with adversarial and WRDS cases."""
    return generate_all_cases(include_adversarial=True, include_wrds=True, include_hard=False)


def generate_v3_cases() -> list[BenchmarkCase]:
    """Generate v3 benchmark with all case types including hard source-backed cases."""
    return generate_all_cases(include_adversarial=True, include_wrds=True, include_hard=True)


def print_benchmark_summary(cases: list[BenchmarkCase]) -> None:
    """Print summary statistics for the benchmark."""
    print(f"\nBenchmark Summary")
    print(f"=" * 50)
    print(f"Total cases: {len(cases)}")
    
    # By module
    print(f"\nBy Module:")
    for module in Module:
        count = len([c for c in cases if c.module == module])
        print(f"  {module.value}: {count}")
    
    # By difficulty
    print(f"\nBy Difficulty:")
    for diff in Difficulty:
        count = len([c for c in cases if c.difficulty == diff])
        print(f"  {diff.value}: {count}")
    
    # By validity
    print(f"\nBy Expected Validity:")
    for val in Validity:
        count = len([c for c in cases if c.expected_validity == val])
        print(f"  {val.value}: {count}")
    
    # Violation type coverage
    print(f"\nViolation Type Coverage:")
    for vtype in ViolationType:
        count = len([c for c in cases if vtype in c.expected_violations])
        print(f"  {vtype.value}: {count}")


if __name__ == "__main__":
    import sys
    
    # Determine which version to generate
    if len(sys.argv) > 1 and sys.argv[1] == "v1":
        print("Generating v1 benchmark (original 42 cases)...")
        cases = generate_v1_cases()
        output_path = "data/benchmark/benchmark_v1.jsonl"
    else:
        print("Generating v2 benchmark (with adversarial + WRDS cases)...")
        cases = generate_v2_cases()
        output_path = "data/benchmark/benchmark_v2.jsonl"
    
    print_benchmark_summary(cases)
    save_benchmark(cases, output_path)
    
    # Also save a sample
    sample_path = output_path.replace(".jsonl", "_sample.jsonl")
    save_benchmark(cases[:25], sample_path)
