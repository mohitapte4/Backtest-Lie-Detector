"""
Hard benchmark cases based on real-world finance traps.

These cases are designed to be genuinely challenging, with surface-level
answers that are tempting but wrong. Each case is source-backed and
tests the model's ability to audit financial research workflows.

Case families:
1. Ticker reassignment (Sears S → Sprint S)
2. Security reorganization (Manville PERMNO discontinuity)
3. FB-to-META timing traps
4. GOOG vs GOOGL share class
5. IBM/Kyndryl spin-off
6. SEC filing clock nuances
7. S&P index announcement vs effective
8. Erroneous index announcements
9. Compustat current vs point-in-time
10. As-filed vs standardized financials
11. Adjusted price traps
12. Delisting return omission
13. Earnings timing windows
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
# 1. TICKER REASSIGNMENT CASES
# Ticker S: Sears Roebuck → Sprint Nextel (2005)
# =============================================================================

TICKER_REASSIGNMENT_CASES = [
    BenchmarkCase(
        id="hard_ticker_s_continuous_2004_2006",
        module=Module.TICKER_TIME_MACHINE,
        difficulty=Difficulty.HARD,
        prompt=(
            "A researcher studies retail sector momentum from 2003-2007. They query "
            "CRSP daily returns using ticker 'S' throughout the period and treat it "
            "as one continuous security. They calculate cumulative returns and Sharpe "
            "ratios for ticker S across this entire period. Audit this workflow."
        ),
        expected_validity=Validity.INVALID,
        expected_violations=[
            ViolationType.IDENTIFIER_TIME_TRAVEL,
            ViolationType.ISSUER_SECURITY_CONFUSION,
        ],
        expected_repair=[
            "Ticker S was Sears Roebuck (PERMNO 11850) until 2005.",
            "Ticker S became Sprint Nextel (PERMNO 87447) in 2005.",
            "These are completely different companies in different sectors.",
            "Use PERMNO to track securities, not tickers.",
            "Treat pre-2005 and post-2005 ticker S as separate securities."
        ],
        ground_truth_notes=(
            "Ticker S was reassigned from Sears Roebuck (retail) to Sprint Nextel "
            "(telecom) in 2005. A study treating ticker S as continuous across "
            "2004-2006 would splice together returns from two unrelated companies, "
            "making any analysis meaningless."
        ),
        source_fields=SourceFields(
            ticker="S",
            backtest_start="2003-01-01",
            backtest_end="2007-12-31",
            extra={
                "source": "CRSP stocknames",
                "sears_permno": "11850",
                "sprint_permno": "87447",
                "reassignment_year": "2005"
            },
        ),
    ),
    
    BenchmarkCase(
        id="hard_ticker_s_permno_resolved",
        module=Module.TICKER_TIME_MACHINE,
        difficulty=Difficulty.HARD,
        prompt=(
            "A researcher studies Sears Roebuck from 2000-2004. They first query CRSP "
            "to get PERMNO 11850 for Sears, then retrieve all returns using that PERMNO. "
            "They never use the ticker symbol directly in their return queries. "
            "Audit this workflow."
        ),
        expected_validity=Validity.VALID,
        expected_violations=[],
        expected_repair=[],
        ground_truth_notes=(
            "Using PERMNO rather than ticker is the correct approach. PERMNO 11850 "
            "consistently identifies Sears Roebuck regardless of ticker changes or "
            "reassignments. This workflow avoids the ticker reassignment trap."
        ),
        source_fields=SourceFields(
            permno="11850",
            company="Sears Roebuck",
            backtest_start="2000-01-01",
            backtest_end="2004-12-31",
            extra={"source": "CRSP stocknames"},
        ),
    ),
    
    BenchmarkCase(
        id="hard_ticker_c_citi_2009",
        module=Module.TICKER_TIME_MACHINE,
        difficulty=Difficulty.HARD,
        prompt=(
            "A researcher studies Citigroup's recovery from 2008-2012 using ticker C. "
            "They note the stock underwent a 1-for-10 reverse split in May 2011. "
            "They query returns using ticker C throughout and adjust for the split. "
            "Audit this workflow."
        ),
        expected_validity=Validity.VALID,
        expected_violations=[],
        expected_repair=[],
        ground_truth_notes=(
            "Citigroup maintained ticker C throughout this period. The reverse split "
            "is a corporate action that affects price levels but not security identity. "
            "Using ticker C continuously is valid here, and adjusting for the split "
            "is the correct approach."
        ),
        source_fields=SourceFields(
            ticker="C",
            company="Citigroup",
            backtest_start="2008-01-01",
            backtest_end="2012-12-31",
            extra={"reverse_split": "2011-05-06", "ratio": "1:10"},
        ),
    ),
]


# =============================================================================
# 2. SECURITY REORGANIZATION CASES
# Manville Corp: PERMNO 16707 → PERMNO 90100 after 1988 reorganization
# =============================================================================

SECURITY_REORGANIZATION_CASES = [
    BenchmarkCase(
        id="hard_manville_permno_stitch",
        module=Module.SURVIVORSHIP_DELISTING,
        difficulty=Difficulty.HARD,
        prompt=(
            "A researcher studies asbestos liability firms from 1980-1995. For Manville "
            "Corporation, they find PERMNO 16707 (Manville Corp, ended late 1988) and "
            "PERMNO 90100 (Johns Manville Corp New, started late 1988). They stitch "
            "the returns together, arguing it's 'essentially the same company' after "
            "bankruptcy reorganization. Audit this workflow."
        ),
        expected_validity=Validity.INVALID,
        expected_violations=[
            ViolationType.ISSUER_SECURITY_CONFUSION,
            ViolationType.DELISTING_RETURN_OMISSION,
        ],
        expected_repair=[
            "PERMNO 16707 and PERMNO 90100 are different securities.",
            "The old equity was cancelled in bankruptcy; new equity was issued.",
            "Original shareholders received different consideration in reorganization.",
            "Must treat these as separate securities with a discontinuity.",
            "Include delisting treatment for PERMNO 16707 at reorganization."
        ],
        ground_truth_notes=(
            "Manville Corp (PERMNO 16707) filed for bankruptcy in 1982 and emerged "
            "in late 1988. The reorganization created Johns Manville Corp New "
            "(PERMNO 90100). These are different securities - the old equity was "
            "cancelled and new equity issued. Stitching returns ignores the "
            "discontinuity and treatment of original shareholders."
        ),
        source_fields=SourceFields(
            company="Manville Corporation",
            backtest_start="1980-01-01",
            backtest_end="1995-12-31",
            extra={
                "source": "CRSP dsedelist, stocknames",
                "old_permno": "16707",
                "new_permno": "90100",
                "reorg_date": "1988-11"
            },
        ),
    ),
    
    BenchmarkCase(
        id="hard_gm_old_new_2009",
        module=Module.SURVIVORSHIP_DELISTING,
        difficulty=Difficulty.HARD,
        prompt=(
            "A researcher studies GM from 2005-2015. They identify 'old GM' (PERMNO "
            "12079, delisted 2009) and 'new GM' (PERMNO 93436, IPO 2010). They create "
            "a continuous GM return series by stitching these together at zero return "
            "for the gap period. Audit this workflow."
        ),
        expected_validity=Validity.INVALID,
        expected_violations=[
            ViolationType.ISSUER_SECURITY_CONFUSION,
            ViolationType.DELISTING_RETURN_OMISSION,
        ],
        expected_repair=[
            "Old GM equity was cancelled in bankruptcy - shareholders received nothing.",
            "New GM is a completely different security with different shareholders.",
            "Old GM delisting return was approximately -100%.",
            "Cannot stitch these as continuous; they are economically unrelated securities.",
            "Any investment in old GM ended at bankruptcy with total loss."
        ],
        ground_truth_notes=(
            "General Motors filed for bankruptcy in June 2009. Old GM shareholders "
            "were wiped out. The 'new GM' that IPO'd in November 2010 was a different "
            "company with different equity. Stitching these series together implies "
            "continuity that didn't exist for investors."
        ),
        source_fields=SourceFields(
            company="General Motors",
            backtest_start="2005-01-01",
            backtest_end="2015-12-31",
            extra={
                "old_permno": "12079",
                "new_permno": "93436",
                "bankruptcy": "2009-06",
                "new_ipo": "2010-11"
            },
        ),
    ),
]


# =============================================================================
# 3. FB-TO-META TIMING TRAPS
# Rebrand announced Oct 2021, ticker change June 9, 2022
# =============================================================================

FB_META_TIMING_CASES = [
    BenchmarkCase(
        id="hard_meta_rebrand_dec2021",
        module=Module.TICKER_TIME_MACHINE,
        difficulty=Difficulty.HARD,
        prompt=(
            "A researcher studies the market reaction to Meta's rebrand announcement "
            "in late October 2021. They query stock returns using ticker META for "
            "November and December 2021, reasoning that 'the company was already Meta "
            "by then.' Audit this workflow."
        ),
        expected_validity=Validity.INVALID,
        expected_violations=[ViolationType.IDENTIFIER_TIME_TRAVEL],
        expected_repair=[
            "The company rebranded to Meta on October 28, 2021.",
            "However, the stock ticker remained FB until June 9, 2022.",
            "Use ticker FB for any trading data before June 9, 2022.",
            "META ticker queries for Dec 2021 would return no data or wrong data."
        ],
        ground_truth_notes=(
            "Meta Platforms announced its rebrand from Facebook on October 28, 2021, "
            "but the NASDAQ ticker change from FB to META did not occur until June 9, "
            "2022. The delay was due to regulatory and exchange requirements. Any "
            "query using META for late 2021 data is identifier time travel."
        ),
        source_fields=SourceFields(
            company="Meta Platforms / Facebook",
            event_date="2021-10-28",
            bad_ticker="META",
            historical_ticker="FB",
            extra={
                "rebrand_announcement": "2021-10-28",
                "ticker_change_date": "2022-06-09",
                "source": "NASDAQ, CRSP"
            },
        ),
    ),
    
    BenchmarkCase(
        id="hard_meta_planned_postponed",
        module=Module.TICKER_TIME_MACHINE,
        difficulty=Difficulty.HARD,
        prompt=(
            "A researcher knows that Meta originally planned to change its ticker in "
            "December 2021 but postponed it. They use ticker FB for December 2021 "
            "data, reasoning that 'the original plan doesn't matter, only the actual "
            "ticker at that time.' They correctly use FB until June 8, 2022 and META "
            "from June 9, 2022 onward. Audit this workflow."
        ),
        expected_validity=Validity.VALID,
        expected_violations=[],
        expected_repair=[],
        ground_truth_notes=(
            "This workflow correctly uses the actual ticker at each point in time. "
            "Original plans or announcements don't change the trading ticker. "
            "FB was the valid ticker through June 8, 2022, and META from June 9, 2022."
        ),
        source_fields=SourceFields(
            company="Meta Platforms",
            historical_ticker="FB",
            ticker="META",
            extra={
                "planned_change": "2021-12",
                "actual_change": "2022-06-09"
            },
        ),
    ),
    
    BenchmarkCase(
        id="hard_meta_june9_intraday",
        module=Module.TICKER_TIME_MACHINE,
        difficulty=Difficulty.HARD,
        prompt=(
            "A researcher studies Meta's price action on June 9, 2022, the day of the "
            "ticker change. They use META for all intraday data that day. The change "
            "occurred at market open. Audit this workflow."
        ),
        expected_validity=Validity.VALID,
        expected_violations=[],
        expected_repair=[],
        ground_truth_notes=(
            "The ticker change from FB to META was effective at market open on June 9, "
            "2022. Using META for all trading data that day is valid because no "
            "trading occurred under FB on June 9 - the change was pre-market."
        ),
        source_fields=SourceFields(
            company="Meta Platforms",
            ticker="META",
            event_date="2022-06-09",
            extra={"change_effective": "market open"},
        ),
    ),
]


# =============================================================================
# 4. GOOG VS GOOGL SHARE CLASS CASES
# GOOGL = Class A (voting), GOOG = Class C (non-voting)
# =============================================================================

GOOG_GOOGL_CASES = [
    BenchmarkCase(
        id="hard_goog_proxy_vote_study",
        module=Module.TICKER_TIME_MACHINE,
        difficulty=Difficulty.HARD,
        prompt=(
            "A researcher studies shareholder activism and proxy voting outcomes at "
            "Alphabet from 2015-2023. They analyze stock price reactions to proxy "
            "vote results using ticker GOOG (Class C shares). They argue that GOOG "
            "is more liquid and has more trading volume. Audit this workflow."
        ),
        expected_validity=Validity.INVALID,
        expected_violations=[ViolationType.ISSUER_SECURITY_CONFUSION],
        expected_repair=[
            "GOOG represents Class C shares which have NO voting rights.",
            "Proxy vote outcomes do not directly affect non-voting shareholders.",
            "Use GOOGL (Class A voting shares) for proxy/governance event studies.",
            "Class C holders are economically exposed but not governance-exposed.",
            "The price reaction difference between GOOG and GOOGL around votes is itself interesting."
        ],
        ground_truth_notes=(
            "GOOG is Class C non-voting stock. GOOGL is Class A with voting rights. "
            "A proxy voting study should use GOOGL because those shareholders "
            "actually vote. Using GOOG for governance studies conflates economic "
            "ownership with voting control."
        ),
        source_fields=SourceFields(
            company="Alphabet Inc",
            ticker="GOOG",
            extra={
                "goog_class": "C (non-voting)",
                "googl_class": "A (voting)",
                "split_date": "2014-04-03",
                "source": "SEC filings, CRSP"
            },
        ),
    ),
    
    BenchmarkCase(
        id="hard_googl_earnings_reaction",
        module=Module.TICKER_TIME_MACHINE,
        difficulty=Difficulty.MEDIUM,
        prompt=(
            "A researcher studies Alphabet earnings announcement reactions from "
            "2016-2023. They use GOOGL (Class A) returns around earnings dates. "
            "They note that GOOG and GOOGL have nearly identical returns around "
            "earnings. Audit this workflow."
        ),
        expected_validity=Validity.VALID,
        expected_violations=[],
        expected_repair=[],
        ground_truth_notes=(
            "For earnings reaction studies, either GOOG or GOOGL is acceptable "
            "because earnings affect the economic value of both share classes "
            "equally. Both shares have the same claim on earnings and dividends. "
            "Using GOOGL is valid."
        ),
        source_fields=SourceFields(
            company="Alphabet Inc",
            ticker="GOOGL",
            extra={"study_type": "earnings announcement"},
        ),
    ),
    
    BenchmarkCase(
        id="hard_goog_pre_2014",
        module=Module.TICKER_TIME_MACHINE,
        difficulty=Difficulty.HARD,
        prompt=(
            "A researcher studies Google from 2008-2018 using ticker GOOG throughout. "
            "They treat GOOG as a continuous series spanning the entire period. "
            "Audit this workflow."
        ),
        expected_validity=Validity.INVALID,
        expected_violations=[
            ViolationType.IDENTIFIER_TIME_TRAVEL,
            ViolationType.ISSUER_SECURITY_CONFUSION,
        ],
        expected_repair=[
            "Before April 2014, only one Google share class traded (under GOOG).",
            "In April 2014, the stock split created GOOG (Class C) and GOOGL (Class A).",
            "The pre-2014 GOOG is more comparable to current GOOGL than current GOOG.",
            "For continuity with pre-2014 Google, use GOOGL post-2014.",
            "Or treat the split as a corporate action and adjust accordingly."
        ],
        ground_truth_notes=(
            "Google's April 2014 stock split created two share classes. Pre-split "
            "GOOG became post-split GOOGL (Class A voting). The current GOOG (Class C) "
            "was newly issued. Treating GOOG as continuous misses this fundamental change."
        ),
        source_fields=SourceFields(
            company="Google / Alphabet",
            ticker="GOOG",
            backtest_start="2008-01-01",
            backtest_end="2018-12-31",
            extra={
                "split_date": "2014-04-03",
                "pre_split_comparable": "GOOGL"
            },
        ),
    ),
]


# =============================================================================
# 5. IBM/KYNDRYL SPIN-OFF CASES
# Separation: Nov 3, 2021, KD trading: Nov 4, 2021
# Ratio: 1 KD per 5 IBM shares
# =============================================================================

IBM_KYNDRYL_CASES = [
    BenchmarkCase(
        id="hard_ibm_kyndryl_price_only",
        module=Module.TICKER_TIME_MACHINE,
        difficulty=Difficulty.HARD,
        prompt=(
            "A researcher computes IBM total returns for October-November 2021. They "
            "use IBM closing prices from CRSP: $140.42 on Nov 3 and $118.99 on Nov 4. "
            "They calculate the Nov 4 return as (118.99 - 140.42) / 140.42 = -15.3%. "
            "Audit this workflow."
        ),
        expected_validity=Validity.INVALID,
        expected_violations=[
            ViolationType.WRONG_EVENT_WINDOW,
            ViolationType.ISSUER_SECURITY_CONFUSION,
        ],
        expected_repair=[
            "IBM spun off Kyndryl (KD) on November 3, 2021.",
            "IBM shareholders received 1 KD share per 5 IBM shares.",
            "The Nov 4 IBM price drop reflects the spinoff distribution, not a loss.",
            "Total return must include the value of KD shares received.",
            "Use CRSP distribution codes (facpr, facshr) to adjust properly.",
            "Or use CRSP adjusted returns which account for spinoffs."
        ],
        ground_truth_notes=(
            "IBM completed the Kyndryl spinoff on Nov 3, 2021. The ~15% price drop "
            "reflects the distribution of Kyndryl shares to IBM holders. An IBM "
            "investor on Nov 3 owned both IBM and KD on Nov 4. Ignoring the KD "
            "distribution creates a spurious -15% return."
        ),
        source_fields=SourceFields(
            company="IBM",
            ticker="IBM",
            event_date="2021-11-03",
            extra={
                "spinoff_ticker": "KD",
                "spinoff_company": "Kyndryl Holdings",
                "distribution_ratio": "1 KD per 5 IBM",
                "kd_first_trade": "2021-11-04",
                "source": "IBM 8-K, CRSP"
            },
        ),
    ),
    
    BenchmarkCase(
        id="hard_ibm_crsp_adjusted_return",
        module=Module.TICKER_TIME_MACHINE,
        difficulty=Difficulty.HARD,
        prompt=(
            "A researcher computes IBM returns for November 2021 using CRSP adjusted "
            "returns (ret field) which incorporate the Kyndryl distribution factor. "
            "They do not separately track KD shares. Audit this workflow."
        ),
        expected_validity=Validity.VALID,
        expected_violations=[],
        expected_repair=[],
        ground_truth_notes=(
            "CRSP adjusted returns (the 'ret' field) incorporate spinoff distributions "
            "via the factor to adjust shares (facshr). Using CRSP ret for IBM through "
            "the Kyndryl spinoff correctly reflects total shareholder return. This is "
            "the proper approach for total return calculations."
        ),
        source_fields=SourceFields(
            company="IBM",
            ticker="IBM",
            extra={
                "method": "CRSP adjusted returns",
                "spinoff_handled": "via facshr factor"
            },
        ),
    ),
    
    BenchmarkCase(
        id="hard_kyndryl_nov3_price",
        module=Module.TICKER_TIME_MACHINE,
        difficulty=Difficulty.HARD,
        prompt=(
            "A researcher studies the first day of Kyndryl trading. They query KD "
            "prices for November 3, 2021 (the spinoff date) and November 4, 2021. "
            "They find no price for Nov 3 and conclude this is a data error. "
            "Audit this workflow."
        ),
        expected_validity=Validity.AMBIGUOUS,
        expected_violations=[],
        expected_repair=[
            "KD did not trade until November 4, 2021 (regular-way trading).",
            "No Nov 3 price is correct - not a data error.",
            "When-issued trading may have occurred before Nov 4.",
            "The researcher should verify when-issued vs regular trading dates."
        ],
        ground_truth_notes=(
            "This is ambiguous because the researcher might be looking for when-issued "
            "prices vs regular trading. KD regular-way trading began Nov 4. The absence "
            "of Nov 3 prices is not an error but the researcher needs to clarify their "
            "intent."
        ),
        source_fields=SourceFields(
            company="Kyndryl Holdings",
            ticker="KD",
            event_date="2021-11-04",
            extra={"first_regular_trade": "2021-11-04"},
        ),
    ),
]


# =============================================================================
# 6. SEC FILING CLOCK CASES
# EDGAR: 6 AM - 10 PM ET, most after 5:30 PM get next business day
# =============================================================================

SEC_FILING_CLOCK_CASES = [
    BenchmarkCase(
        id="hard_filing_530pm_nextday",
        module=Module.FILING_CLOCK,
        difficulty=Difficulty.HARD,
        prompt=(
            "An 8-K is filed at 5:45 PM ET on Tuesday, March 14, 2023. EDGAR shows "
            "acceptance time of 5:45 PM but filing date of March 15, 2023. A trading "
            "strategy executes at 10:00 AM ET on Wednesday March 15 based on the 8-K "
            "contents. The researcher argues the filing was 'accepted' on March 14. "
            "Audit this workflow."
        ),
        expected_validity=Validity.AMBIGUOUS,
        expected_violations=[],
        expected_repair=[
            "EDGAR acceptance time and filing date can differ.",
            "Filings after 5:30 PM typically get next-day filing date.",
            "Dissemination to subscribers may occur at acceptance or at filing date.",
            "Need to verify when the document was actually publicly disseminated.",
            "Some sophisticated investors may access filings immediately after acceptance."
        ],
        ground_truth_notes=(
            "This is genuinely ambiguous. While the acceptance time was 5:45 PM on "
            "March 14, the official filing date is March 15. EDGAR dissemination "
            "timing varies. Retail investors see the filing date; some institutional "
            "systems may capture acceptance time. More information is needed."
        ),
        source_fields=SourceFields(
            filing_timestamp="2023-03-14 17:45:00 America/New_York",
            decision_timestamp="2023-03-15 10:00:00 America/New_York",
            extra={
                "edgar_filing_date": "2023-03-15",
                "edgar_acceptance": "2023-03-14 17:45:00",
                "source": "SEC EDGAR"
            },
        ),
    ),
    
    BenchmarkCase(
        id="hard_filing_517pm_sameday",
        module=Module.FILING_CLOCK,
        difficulty=Difficulty.HARD,
        prompt=(
            "An 8-K is filed at 5:17 PM ET on Monday, April 10, 2023. EDGAR shows "
            "both acceptance time and filing date as April 10, 2023. A trading "
            "strategy executes at 9:30 AM ET on Tuesday April 11 based on the 8-K. "
            "Audit this workflow."
        ),
        expected_validity=Validity.VALID,
        expected_violations=[],
        expected_repair=[],
        ground_truth_notes=(
            "Filings before 5:30 PM typically receive same-day filing date. Both "
            "acceptance and filing date are April 10. Trading on April 11 morning "
            "clearly uses information that was publicly available the previous "
            "business day. This is valid."
        ),
        source_fields=SourceFields(
            filing_timestamp="2023-04-10 17:17:00 America/New_York",
            decision_timestamp="2023-04-11 09:30:00 America/New_York",
        ),
    ),
    
    BenchmarkCase(
        id="hard_filing_before_6am",
        module=Module.FILING_CLOCK,
        difficulty=Difficulty.HARD,
        prompt=(
            "A company submits a 10-K at 5:55 AM ET on March 1, 2023. EDGAR does not "
            "open until 6:00 AM. The acceptance timestamp shows 6:00 AM. A pre-market "
            "trading strategy executes at 6:05 AM based on the 10-K. "
            "Audit this workflow."
        ),
        expected_validity=Validity.VALID,
        expected_violations=[],
        expected_repair=[],
        ground_truth_notes=(
            "EDGAR processes filings starting at 6:00 AM ET. A submission at 5:55 AM "
            "would be accepted at or shortly after 6:00 AM. Trading at 6:05 AM after "
            "a 6:00 AM acceptance gives 5 minutes for the filing to be public. This "
            "is tight but valid for sophisticated systems."
        ),
        source_fields=SourceFields(
            filing_timestamp="2023-03-01 06:00:00 America/New_York",
            decision_timestamp="2023-03-01 06:05:00 America/New_York",
            extra={"edgar_opens": "6:00 AM ET"},
        ),
    ),
    
    BenchmarkCase(
        id="hard_filing_acceptance_vs_dissemination",
        module=Module.FILING_CLOCK,
        difficulty=Difficulty.HARD,
        prompt=(
            "A researcher studies 8-K information content using EDGAR acceptance "
            "timestamps. They measure returns from acceptance time to 24 hours later. "
            "They find abnormal returns starting exactly at acceptance time and "
            "conclude this proves 'fast traders' access filings instantly. "
            "Audit this workflow."
        ),
        expected_validity=Validity.AMBIGUOUS,
        expected_violations=[],
        expected_repair=[
            "Acceptance time does not guarantee immediate public dissemination.",
            "Some filings may be disseminated instantly; others may have delays.",
            "Need to verify actual dissemination timestamps, not just acceptance.",
            "The pattern could also be explained by coincident news (press releases).",
            "Should control for concurrent information releases."
        ],
        ground_truth_notes=(
            "This is ambiguous because EDGAR acceptance ≠ public availability. "
            "The finding could reflect: (1) true fast access to EDGAR, (2) coincident "
            "press releases, or (3) other channels. The researcher needs to verify "
            "actual dissemination timing."
        ),
        source_fields=SourceFields(
            extra={
                "issue": "acceptance vs dissemination timing",
                "source": "SEC EDGAR"
            },
        ),
    ),
]


# =============================================================================
# 7. S&P INDEX ANNOUNCEMENT VS EFFECTIVE DATE
# Announcements: typically 5:15 PM ET
# Effective: after close on specified date
# =============================================================================

SP_INDEX_TIMING_CASES = [
    BenchmarkCase(
        id="hard_sp500_announcement_515pm",
        module=Module.SURVIVORSHIP_DELISTING,
        difficulty=Difficulty.HARD,
        prompt=(
            "S&P announces at 5:15 PM ET on Wednesday that XYZ Corp will be added to "
            "the S&P 500, effective after close on the following Friday. A backtest "
            "includes XYZ in the S&P 500 portfolio starting at Thursday's open. "
            "Audit this workflow."
        ),
        expected_validity=Validity.INVALID,
        expected_violations=[ViolationType.SURVIVORSHIP_BIAS],
        expected_repair=[
            "XYZ is not in the S&P 500 until after Friday's close.",
            "The announcement is at 5:15 PM Wednesday, after market close.",
            "Index membership should only reflect XYZ starting Monday.",
            "Pre-inclusion trading could be a separate 'announcement effect' study.",
            "For index replication, add XYZ after Friday close at effective date."
        ],
        ground_truth_notes=(
            "S&P 500 additions are effective after the close on a specified date. "
            "Including XYZ on Thursday or Friday, before the effective date, is "
            "forward-looking. The stock should be added at Friday's close for "
            "Monday trading."
        ),
        source_fields=SourceFields(
            extra={
                "announcement_time": "5:15 PM ET Wednesday",
                "effective_date": "after Friday close",
                "source": "S&P Dow Jones Indices"
            },
        ),
    ),
    
    BenchmarkCase(
        id="hard_sp500_announcement_day_trade",
        module=Module.SURVIVORSHIP_DELISTING,
        difficulty=Difficulty.HARD,
        prompt=(
            "An announcement-effect study measures returns for stocks added to the "
            "S&P 500. They measure from the close on announcement day to close 5 "
            "days later. S&P announces changes at 5:15 PM after market close. "
            "Audit this workflow."
        ),
        expected_validity=Validity.VALID,
        expected_violations=[],
        expected_repair=[],
        ground_truth_notes=(
            "For announcement-effect studies, using the announcement day close as "
            "the starting point is valid. The 5:15 PM announcement is after that "
            "day's close, so returns from that close forward capture the reaction. "
            "This is appropriate event study design."
        ),
        source_fields=SourceFields(
            extra={
                "study_type": "announcement effect",
                "measurement_start": "announcement day close"
            },
        ),
    ),
    
    BenchmarkCase(
        id="hard_sp500_effective_date_list",
        module=Module.SURVIVORSHIP_DELISTING,
        difficulty=Difficulty.HARD,
        prompt=(
            "A researcher backtests an index fund from 2010-2020. They download "
            "historical S&P 500 constituent lists dated as of each month-end. The "
            "lists reflect effective-date membership (who was in the index at close "
            "of that date). They form portfolios on the first trading day of each "
            "month using the prior month-end list. Audit this workflow."
        ),
        expected_validity=Validity.VALID,
        expected_violations=[],
        expected_repair=[],
        ground_truth_notes=(
            "Using month-end constituent lists for next-month portfolios is valid. "
            "The month-end list reflects who is actually in the index at that time. "
            "Forming portfolios on the subsequent trading day uses only information "
            "available at month-end."
        ),
        source_fields=SourceFields(
            backtest_start="2010-01-01",
            backtest_end="2020-12-31",
            extra={"rebalance": "monthly", "data": "effective-date constituent lists"},
        ),
    ),
]


# =============================================================================
# 8. ERRONEOUS INDEX ANNOUNCEMENTS
# e.g., March 2024 DJ US Dividend 100 error
# =============================================================================

ERRONEOUS_ANNOUNCEMENT_CASES = [
    BenchmarkCase(
        id="hard_index_erroneous_list",
        module=Module.SURVIVORSHIP_DELISTING,
        difficulty=Difficulty.HARD,
        prompt=(
            "In March 2024, S&P Dow Jones released a pro forma constituent list for "
            "the Dow Jones U.S. Dividend 100 Index that was later corrected. A "
            "researcher uses the initial (erroneous) list for a March 2024 portfolio, "
            "arguing that 'this is what was publicly available at the time.' "
            "Audit this workflow."
        ),
        expected_validity=Validity.AMBIGUOUS,
        expected_violations=[],
        expected_repair=[
            "The erroneous list was public information at the time.",
            "If measuring real-time tradeable returns, the initial list may be correct.",
            "If the goal is index replication, the corrected list should be used.",
            "Document which version was used and why.",
            "The discrepancy itself could be an interesting research subject."
        ],
        ground_truth_notes=(
            "This is genuinely ambiguous. For a study of 'what an investor could have "
            "done in real-time,' the erroneous list might be appropriate. For index "
            "replication or comparing to actual index returns, the corrected list is "
            "needed. Intent determines validity."
        ),
        source_fields=SourceFields(
            extra={
                "index": "Dow Jones U.S. Dividend 100",
                "error_date": "March 2024",
                "source": "Reuters report"
            },
        ),
    ),
]


# =============================================================================
# 9. COMPUSTAT CURRENT VS POINT-IN-TIME
# Current files: restated; Snapshot: point-in-time
# =============================================================================

COMPUSTAT_PIT_CASES = [
    BenchmarkCase(
        id="hard_compustat_2026_for_2012",
        module=Module.ACCOUNTING_AVAILABILITY,
        difficulty=Difficulty.HARD,
        prompt=(
            "A researcher downloads Compustat Fundamentals Annual in May 2026 to "
            "backtest an earnings-based strategy from 2010-2015. They align fiscal "
            "year data with trading dates using datadate + 4 months (to allow for "
            "10-K filing). They use the downloaded values directly. Audit this workflow."
        ),
        expected_validity=Validity.INVALID,
        expected_violations=[
            ViolationType.RESTATEMENT_LEAKAGE,
        ],
        expected_repair=[
            "Current Compustat files contain restated values, not as-originally-reported.",
            "Companies restate historical financials for various reasons.",
            "Use Compustat Snapshot or Point-in-Time files for backtesting.",
            "Compare against SEC filing dates to ensure data was available.",
            "The 4-month lag does not address restatement look-ahead bias."
        ],
        ground_truth_notes=(
            "Compustat's current (non-snapshot) database contains the most recent "
            "values, which may have been restated multiple times since original "
            "filing. A 2026 download for 2012 data could contain restatements from "
            "2013, 2015, or later. This is classic look-ahead bias."
        ),
        source_fields=SourceFields(
            backtest_start="2010-01-01",
            backtest_end="2015-12-31",
            extra={
                "data_download": "2026-05",
                "data_source": "Compustat Annual (current file)",
                "issue": "restatement look-ahead"
            },
        ),
    ),
    
    BenchmarkCase(
        id="hard_compustat_snapshot_correct",
        module=Module.ACCOUNTING_AVAILABILITY,
        difficulty=Difficulty.MEDIUM,
        prompt=(
            "A researcher uses Compustat Point-in-Time Snapshot files for a 2010-2015 "
            "backtest. They select snapshot dates that correspond to one month after "
            "each 10-K filing deadline. They use only data that appears in the snapshot "
            "dated before their portfolio formation date. Audit this workflow."
        ),
        expected_validity=Validity.VALID,
        expected_violations=[],
        expected_repair=[],
        ground_truth_notes=(
            "Using Compustat Snapshot files with appropriate snapshot dates is the "
            "correct approach for point-in-time backtesting. Selecting snapshots after "
            "10-K deadlines ensures data was likely available. This methodology avoids "
            "restatement look-ahead bias."
        ),
        source_fields=SourceFields(
            backtest_start="2010-01-01",
            backtest_end="2015-12-31",
            extra={"data_source": "Compustat Point-in-Time Snapshot"},
        ),
    ),
    
    BenchmarkCase(
        id="hard_compustat_restandardization",
        module=Module.ACCOUNTING_AVAILABILITY,
        difficulty=Difficulty.HARD,
        prompt=(
            "A researcher notes that Compustat changed its standardization methodology "
            "for certain items in 2018. Their 2015-2020 backtest uses data downloaded "
            "in 2022, which applies the new methodology to all years. They argue that "
            "'the numbers are still accurate, just standardized differently.' "
            "Audit this workflow."
        ),
        expected_validity=Validity.INVALID,
        expected_violations=[ViolationType.RESTATEMENT_LEAKAGE],
        expected_repair=[
            "Standardization methodology changes create look-ahead bias.",
            "Pre-2018 values under post-2018 methodology were not available in 2015-2017.",
            "This can change rankings and factor scores.",
            "Use vintage-appropriate data or snapshot files.",
            "Document standardization version and assess materiality."
        ],
        ground_truth_notes=(
            "Compustat periodically updates standardization rules. Applying 2018 "
            "methodology to 2015 data creates values that didn't exist in 2015. "
            "This is subtle but can materially affect certain accounting ratios "
            "and anomaly strategies."
        ),
        source_fields=SourceFields(
            backtest_start="2015-01-01",
            backtest_end="2020-12-31",
            extra={
                "methodology_change": "2018",
                "download_date": "2022",
                "issue": "re-standardization"
            },
        ),
    ),
]


# =============================================================================
# 10. AS-FILED VS STANDARDIZED FINANCIALS
# XBRL as-filed vs Compustat/FactSet standardized
# =============================================================================

AS_FILED_VS_STANDARDIZED_CASES = [
    BenchmarkCase(
        id="hard_xbrl_compustat_difference",
        module=Module.ACCOUNTING_AVAILABILITY,
        difficulty=Difficulty.HARD,
        prompt=(
            "A researcher finds that Compustat's 'Total Assets' for Company X in "
            "2019 differs from the XBRL-tagged 'Total Assets' in the 10-K. They "
            "assume Compustat made an extraction error and 'correct' the Compustat "
            "value to match XBRL. Audit this workflow."
        ),
        expected_validity=Validity.INVALID,
        expected_violations=[ViolationType.RESTATEMENT_LEAKAGE],
        expected_repair=[
            "Differences between Compustat and XBRL are often intentional standardization.",
            "Compustat applies consistent definitions across companies.",
            "XBRL as-filed may use company-specific custom tags or definitions.",
            "Do not 'correct' Compustat to match XBRL without understanding the difference.",
            "Document the discrepancy and use one source consistently."
        ],
        ground_truth_notes=(
            "Compustat and XBRL discrepancies are usually due to standardization "
            "differences, not extraction errors. Compustat may reclassify items for "
            "cross-company comparability. Changing values introduces researcher bias "
            "and inconsistency."
        ),
        source_fields=SourceFields(
            extra={
                "data_sources": "Compustat, SEC XBRL",
                "issue": "standardization vs as-filed"
            },
        ),
    ),
    
    BenchmarkCase(
        id="hard_factset_compustat_consistent",
        module=Module.ACCOUNTING_AVAILABILITY,
        difficulty=Difficulty.MEDIUM,
        prompt=(
            "A researcher uses Compustat for US firms and FactSet for international "
            "firms in a global asset pricing study. They acknowledge that definitions "
            "may differ between vendors but apply the same variable construction to "
            "both. Audit this workflow."
        ),
        expected_validity=Validity.AMBIGUOUS,
        expected_violations=[],
        expected_repair=[
            "Using multiple data vendors introduces definitional inconsistencies.",
            "Book equity, total assets, etc. may be calculated differently.",
            "This may be unavoidable for global studies.",
            "Should document the potential impact and test robustness.",
            "Consider harmonization procedures or vendor-specific adjustments."
        ],
        ground_truth_notes=(
            "This is ambiguous. Multi-vendor studies face real data limitations. "
            "The approach may be acceptable if properly documented and if robustness "
            "is tested. It's not clearly valid or invalid without more context about "
            "how critical the cross-vendor comparability is."
        ),
        source_fields=SourceFields(
            extra={
                "vendors": "Compustat, FactSet",
                "scope": "global"
            },
        ),
    ),
]


# =============================================================================
# 11. ADJUSTED PRICE TRAPS
# CRSP adjusted prices: for total return, not price-level rules
# =============================================================================

ADJUSTED_PRICE_CASES = [
    BenchmarkCase(
        id="hard_adjusted_price_level_rule",
        module=Module.TICKER_TIME_MACHINE,
        difficulty=Difficulty.HARD,
        prompt=(
            "A researcher backtests a strategy that buys stocks when they cross above "
            "$5 per share (to avoid penny stocks). They use CRSP adjusted prices "
            "(prc/cfacpr) for this threshold rule throughout 1995-2020. They argue "
            "adjusted prices maintain comparability over time. Audit this workflow."
        ),
        expected_validity=Validity.INVALID,
        expected_violations=[ViolationType.WRONG_EVENT_WINDOW],
        expected_repair=[
            "Adjusted prices are for return calculation, not price-level thresholds.",
            "A stock at $10 in 2000 might show $2.50 adjusted due to later splits.",
            "The historical investor saw $10, not $2.50.",
            "Use raw historical prices (prc field) for price-level trading rules.",
            "Adjusted prices can make historical prices look like penny stocks."
        ],
        ground_truth_notes=(
            "CRSP adjusted prices divide by the cumulative adjustment factor, which "
            "includes splits and dividends. A stock that was $100 in 2000 but split "
            "10:1 might show $10 adjusted. Using adjusted prices for '$5 threshold' "
            "rules makes no economic sense - the investor saw $100, not $10."
        ),
        source_fields=SourceFields(
            backtest_start="1995-01-01",
            backtest_end="2020-12-31",
            extra={
                "issue": "adjusted price for level-based rule",
                "correct_field": "prc (raw price)",
                "incorrect_field": "prc/cfacpr (adjusted)"
            },
        ),
    ),
    
    BenchmarkCase(
        id="hard_adjusted_price_return_calc",
        module=Module.TICKER_TIME_MACHINE,
        difficulty=Difficulty.EASY,
        prompt=(
            "A researcher calculates buy-and-hold returns using CRSP adjusted prices. "
            "For a stock held from 2010-2020, they compute: (adj_prc_2020 / adj_prc_2010) - 1. "
            "Audit this workflow."
        ),
        expected_validity=Validity.VALID,
        expected_violations=[],
        expected_repair=[],
        ground_truth_notes=(
            "Using adjusted prices for return calculation is correct. The adjustment "
            "factor accounts for splits and distributions, allowing direct price "
            "comparison across time. This is the intended use of adjusted prices."
        ),
        source_fields=SourceFields(
            backtest_start="2010-01-01",
            backtest_end="2020-12-31",
            extra={"calculation": "total return from adjusted prices"},
        ),
    ),
    
    BenchmarkCase(
        id="hard_adjusted_price_base_date",
        module=Module.TICKER_TIME_MACHINE,
        difficulty=Difficulty.HARD,
        prompt=(
            "A researcher downloads CRSP data on January 15, 2024. They use adjusted "
            "prices to compare stock A in 2015 vs stock B in 2015. Stock A has had "
            "three 2:1 splits since 2015; Stock B has had none. They note that stock "
            "A's 2015 adjusted price is 1/8 of its 2015 raw price while stock B's is "
            "unchanged. They compare the adjusted prices directly. Audit this workflow."
        ),
        expected_validity=Validity.INVALID,
        expected_violations=[ViolationType.WRONG_EVENT_WINDOW],
        expected_repair=[
            "CRSP adjustment factors use the most recent data as the base.",
            "Adjusted prices are comparable WITHIN a stock over time.",
            "Adjusted prices are NOT comparable ACROSS stocks at a point in time.",
            "Stock A's $10 adjusted ≠ Stock B's $10 adjusted in 2015.",
            "For cross-stock comparison at a point in time, use raw prices."
        ],
        ground_truth_notes=(
            "CRSP adjusted prices divide historical prices by future adjustment factors. "
            "This makes a single stock's prices comparable over time but makes "
            "cross-stock comparisons invalid. A stock with many subsequent splits "
            "will have artificially low adjusted historical prices."
        ),
        source_fields=SourceFields(
            extra={
                "issue": "cross-stock adjusted price comparison",
                "source": "CRSP"
            },
        ),
    ),
]


# =============================================================================
# 12. DELISTING RETURN OMISSION
# Shumway-Warther: -55% correction for missing NASDAQ performance delistings
# =============================================================================

DELISTING_RETURN_CASES = [
    BenchmarkCase(
        id="hard_delisting_missing_drop",
        module=Module.SURVIVORSHIP_DELISTING,
        difficulty=Difficulty.HARD,
        prompt=(
            "A researcher backtests a value strategy from 1995-2010 using CRSP monthly "
            "data. When a stock delists, they drop it from the portfolio on the last "
            "trading day, ignoring any delisting return (DLRET). They argue that "
            "'missing data should be excluded.' Audit this workflow."
        ),
        expected_validity=Validity.INVALID,
        expected_violations=[
            ViolationType.DELISTING_RETURN_OMISSION,
            ViolationType.SURVIVORSHIP_BIAS,
        ],
        expected_repair=[
            "Delisting returns (DLRET) must be included for accurate backtesting.",
            "Missing DLRET is often for performance-related delistings (bankruptcies).",
            "Shumway-Warther estimate -55% correction for missing NASDAQ performance delistings.",
            "Options: (1) use available DLRET, (2) impute conservative return, (3) drop delistings with bias acknowledgment.",
            "Simply dropping stocks on last trade overstates strategy returns."
        ],
        ground_truth_notes=(
            "CRSP delisting returns capture the economic outcome of delistings. "
            "Performance-related delistings (bankruptcies, exchange violations) "
            "often have large negative returns. Ignoring DLRET biases returns upward "
            "because the worst outcomes are excluded."
        ),
        source_fields=SourceFields(
            backtest_start="1995-01-01",
            backtest_end="2010-12-31",
            extra={
                "source": "Shumway & Warther (1999)",
                "nasdaq_bias": "-55% for missing performance delistings"
            },
        ),
    ),
    
    BenchmarkCase(
        id="hard_delisting_zero_fill",
        module=Module.SURVIVORSHIP_DELISTING,
        difficulty=Difficulty.HARD,
        prompt=(
            "A researcher backtests from 1995-2010. When DLRET is missing, they "
            "impute zero return rather than dropping the observation. They argue "
            "that 'zero is better than omission.' Audit this workflow."
        ),
        expected_validity=Validity.INVALID,
        expected_violations=[ViolationType.DELISTING_RETURN_OMISSION],
        expected_repair=[
            "Zero imputation is better than dropping but still biased upward.",
            "Most missing performance-related DLRETs are large negative returns.",
            "Shumway-Warther recommend -30% (NYSE) to -55% (NASDAQ) for missing DLRETs.",
            "Conservative imputation: use -100% for bankruptcies, -30% for others.",
            "Zero imputation ignores the systematic negative bias."
        ],
        ground_truth_notes=(
            "Zero imputation acknowledges the existence of the delisted stock but "
            "assigns a neutral return. Since missing DLRETs are systematically negative "
            "(performance failures), zero overstates returns. It's an improvement over "
            "dropping but still not conservative enough."
        ),
        source_fields=SourceFields(
            backtest_start="1995-01-01",
            backtest_end="2010-12-31",
            extra={"imputation": "zero for missing DLRET"},
        ),
    ),
    
    BenchmarkCase(
        id="hard_delisting_conservative_impute",
        module=Module.SURVIVORSHIP_DELISTING,
        difficulty=Difficulty.MEDIUM,
        prompt=(
            "A researcher backtests from 1995-2010. They include DLRET when available. "
            "For missing performance-related delistings (codes 400-599), they impute "
            "-30%. For missing non-performance delistings (mergers, etc.), they use the "
            "last available return. Audit this workflow."
        ),
        expected_validity=Validity.VALID,
        expected_violations=[],
        expected_repair=[],
        ground_truth_notes=(
            "This is a reasonable approach following academic best practices. "
            "Using available DLRET, conservative imputation for missing performance "
            "delistings, and treating mergers differently acknowledges the data "
            "limitations while not ignoring the issue. The -30% is conservative."
        ),
        source_fields=SourceFields(
            backtest_start="1995-01-01",
            backtest_end="2010-12-31",
            extra={
                "imputation": "-30% for missing performance delistings",
                "source": "Shumway & Warther methodology"
            },
        ),
    ),
]


# =============================================================================
# 13. EARNINGS TIMING WINDOW CASES
# After-close vs pre-open announcements need different windows
# =============================================================================

EARNINGS_TIMING_CASES = [
    BenchmarkCase(
        id="hard_earnings_uniform_window",
        module=Module.FILING_CLOCK,
        difficulty=Difficulty.HARD,
        prompt=(
            "A researcher studies earnings announcement reactions using close-to-close "
            "returns. They measure from day t-1 close to day t close for all "
            "announcements, where t is the announcement date. They do not distinguish "
            "between pre-market and after-market announcements. Audit this workflow."
        ),
        expected_validity=Validity.INVALID,
        expected_violations=[ViolationType.WRONG_EVENT_WINDOW],
        expected_repair=[
            "Pre-market and after-hours announcements have different information timing.",
            "After-close announcements: information is in day t+1 open, not day t close.",
            "Pre-market announcements: information is in day t open and day t close.",
            "Use timestamp data to classify announcement timing.",
            "For after-close: measure day t close to day t+1 close.",
            "For pre-market: measure day t-1 close to day t close."
        ],
        ground_truth_notes=(
            "Using a uniform close-to-close window ignores when the announcement "
            "actually occurred. After-close announcements are incorporated overnight; "
            "pre-market announcements are incorporated during the trading day. "
            "Mixing them dilutes the measured reaction."
        ),
        source_fields=SourceFields(
            extra={
                "issue": "uniform event window regardless of announcement timing",
                "source": "Standard event study methodology"
            },
        ),
    ),
    
    BenchmarkCase(
        id="hard_earnings_timestamp_window",
        module=Module.FILING_CLOCK,
        difficulty=Difficulty.MEDIUM,
        prompt=(
            "A researcher uses I/B/E/S announcement timestamps to classify earnings "
            "as pre-market (before 9:30 AM ET) or after-close (after 4:00 PM ET). "
            "For after-close, they measure day t close to day t+1 close. "
            "For pre-market, they measure day t-1 close to day t close. "
            "Audit this workflow."
        ),
        expected_validity=Validity.VALID,
        expected_violations=[],
        expected_repair=[],
        ground_truth_notes=(
            "This is the correct approach. Classifying announcements by timing and "
            "using appropriate event windows ensures the measured return captures "
            "the actual market reaction to the news."
        ),
        source_fields=SourceFields(
            extra={
                "timestamp_source": "I/B/E/S",
                "pre_market": "before 9:30 AM ET",
                "after_close": "after 4:00 PM ET"
            },
        ),
    ),
    
    BenchmarkCase(
        id="hard_earnings_intraday_window",
        module=Module.FILING_CLOCK,
        difficulty=Difficulty.HARD,
        prompt=(
            "A researcher studies intraday price reactions to earnings. They define "
            "the event window as -5 to +30 minutes around the announcement timestamp. "
            "For after-close announcements, they use the next morning's open as the "
            "first available price. They treat this 'delayed reaction' as equivalent "
            "to the intraday reaction. Audit this workflow."
        ),
        expected_validity=Validity.AMBIGUOUS,
        expected_violations=[],
        expected_repair=[
            "After-close and intraday windows are fundamentally different.",
            "After-close: overnight information processing, gap at open.",
            "Intraday: continuous price discovery around announcement.",
            "Mixing them may be necessary for sample size but introduces noise.",
            "Should control for announcement timing in analysis.",
            "Consider separate analysis for each timing category."
        ],
        ground_truth_notes=(
            "This is ambiguous. The researcher is trying to measure the same concept "
            "(immediate reaction) but the market microstructure differs. After-close "
            "announcements get overnight processing; intraday announcements get "
            "continuous price discovery. Whether mixing is acceptable depends on "
            "the research question."
        ),
        source_fields=SourceFields(
            extra={
                "window": "-5 to +30 minutes",
                "after_close_handling": "next open"
            },
        ),
    ),
]


# =============================================================================
# CASE TAGS MAPPING
# Maps case IDs to their appropriate tags
# =============================================================================

HARD_CASE_TAGS: dict[str, list[str]] = {
    # Ticker reassignment
    "hard_ticker_s_continuous_2004_2006": ["multi_violation", "requires_identifier_reasoning"],
    "hard_ticker_s_permno_resolved": ["trap_valid", "requires_identifier_reasoning"],
    "hard_ticker_c_citi_2009": ["trap_valid", "requires_corporate_action_reasoning"],
    
    # Security reorganization
    "hard_manville_permno_stitch": ["multi_violation", "requires_corporate_action_reasoning"],
    "hard_gm_old_new_2009": ["multi_violation", "requires_corporate_action_reasoning"],
    
    # FB-META timing
    "hard_meta_rebrand_dec2021": ["requires_identifier_reasoning", "near_miss"],
    "hard_meta_planned_postponed": ["trap_valid", "requires_identifier_reasoning"],
    "hard_meta_june9_intraday": ["trap_valid", "requires_identifier_reasoning", "requires_timestamp_reasoning"],
    
    # GOOG vs GOOGL
    "hard_goog_proxy_vote_study": ["requires_identifier_reasoning", "requires_corporate_action_reasoning"],
    "hard_googl_earnings_reaction": ["trap_valid", "requires_identifier_reasoning"],
    "hard_goog_pre_2014": ["multi_violation", "requires_identifier_reasoning", "requires_corporate_action_reasoning"],
    
    # IBM/Kyndryl
    "hard_ibm_kyndryl_price_only": ["multi_violation", "requires_corporate_action_reasoning"],
    "hard_ibm_crsp_adjusted_return": ["trap_valid", "requires_corporate_action_reasoning", "requires_dataset_semantics"],
    "hard_kyndryl_nov3_price": ["ambiguous", "requires_timestamp_reasoning"],
    
    # SEC filing clock
    "hard_filing_530pm_nextday": ["ambiguous", "requires_timestamp_reasoning"],
    "hard_filing_517pm_sameday": ["trap_valid", "requires_timestamp_reasoning"],
    "hard_filing_before_6am": ["trap_valid", "requires_timestamp_reasoning"],
    "hard_filing_acceptance_vs_dissemination": ["ambiguous", "requires_timestamp_reasoning"],
    
    # S&P index timing
    "hard_sp500_announcement_515pm": ["requires_timestamp_reasoning"],
    "hard_sp500_announcement_day_trade": ["trap_valid", "requires_timestamp_reasoning"],
    "hard_sp500_effective_date_list": ["trap_valid"],
    
    # Erroneous announcements
    "hard_index_erroneous_list": ["ambiguous", "requires_dataset_semantics"],
    
    # Compustat PIT
    "hard_compustat_2026_for_2012": ["requires_dataset_semantics"],
    "hard_compustat_snapshot_correct": ["trap_valid", "requires_dataset_semantics"],
    "hard_compustat_restandardization": ["requires_dataset_semantics"],
    
    # As-filed vs standardized
    "hard_xbrl_compustat_difference": ["requires_dataset_semantics"],
    "hard_factset_compustat_consistent": ["ambiguous", "requires_dataset_semantics"],
    
    # Adjusted price
    "hard_adjusted_price_level_rule": ["requires_dataset_semantics"],
    "hard_adjusted_price_return_calc": ["trap_valid", "requires_dataset_semantics"],
    "hard_adjusted_price_base_date": ["requires_dataset_semantics"],
    
    # Delisting return
    "hard_delisting_missing_drop": ["multi_violation"],
    "hard_delisting_zero_fill": [],
    "hard_delisting_conservative_impute": ["trap_valid"],
    
    # Earnings timing
    "hard_earnings_uniform_window": ["requires_timestamp_reasoning"],
    "hard_earnings_timestamp_window": ["trap_valid", "requires_timestamp_reasoning"],
    "hard_earnings_intraday_window": ["ambiguous", "requires_timestamp_reasoning"],
}


def apply_tags_to_hard_cases() -> list[BenchmarkCase]:
    """Apply case_tags to all hard cases based on the mapping."""
    all_cases = (
        TICKER_REASSIGNMENT_CASES +
        SECURITY_REORGANIZATION_CASES +
        FB_META_TIMING_CASES +
        GOOG_GOOGL_CASES +
        IBM_KYNDRYL_CASES +
        SEC_FILING_CLOCK_CASES +
        SP_INDEX_TIMING_CASES +
        ERRONEOUS_ANNOUNCEMENT_CASES +
        COMPUSTAT_PIT_CASES +
        AS_FILED_VS_STANDARDIZED_CASES +
        ADJUSTED_PRICE_CASES +
        DELISTING_RETURN_CASES +
        EARNINGS_TIMING_CASES
    )
    
    tagged_cases = []
    for case in all_cases:
        # Create a copy with tags
        tags = HARD_CASE_TAGS.get(case.id, [])
        case_dict = case.model_dump()
        case_dict['case_tags'] = tags
        case_dict['source_note'] = "Source-backed hard case for v3/v4 benchmark"
        tagged_cases.append(BenchmarkCase(**case_dict))
    
    return tagged_cases


# =============================================================================
# Collect all hard cases (with tags applied)
# =============================================================================

HARD_CASES: list[BenchmarkCase] = apply_tags_to_hard_cases()


def get_hard_cases() -> list[BenchmarkCase]:
    """Return all genuinely hard benchmark cases."""
    return HARD_CASES


def get_hard_cases_by_family() -> dict[str, list[BenchmarkCase]]:
    """Return hard cases organized by family."""
    return {
        "ticker_reassignment": TICKER_REASSIGNMENT_CASES,
        "security_reorganization": SECURITY_REORGANIZATION_CASES,
        "fb_meta_timing": FB_META_TIMING_CASES,
        "goog_googl": GOOG_GOOGL_CASES,
        "ibm_kyndryl": IBM_KYNDRYL_CASES,
        "sec_filing_clock": SEC_FILING_CLOCK_CASES,
        "sp_index_timing": SP_INDEX_TIMING_CASES,
        "erroneous_announcements": ERRONEOUS_ANNOUNCEMENT_CASES,
        "compustat_pit": COMPUSTAT_PIT_CASES,
        "as_filed_vs_standardized": AS_FILED_VS_STANDARDIZED_CASES,
        "adjusted_price": ADJUSTED_PRICE_CASES,
        "delisting_return": DELISTING_RETURN_CASES,
        "earnings_timing": EARNINGS_TIMING_CASES,
    }


def print_hard_cases_summary():
    """Print summary of hard cases."""
    families = get_hard_cases_by_family()
    
    print("=" * 70)
    print("HARD BENCHMARK CASES SUMMARY")
    print("=" * 70)
    
    total = 0
    valid_count = 0
    invalid_count = 0
    ambiguous_count = 0
    
    for family_name, cases in families.items():
        print(f"\n{family_name}: {len(cases)} cases")
        for case in cases:
            validity_marker = {"valid": "[V]", "invalid": "[X]", "ambiguous": "[?]"}[case.expected_validity.value]
            print(f"  {validity_marker} {case.id}")
            total += 1
            if case.expected_validity == Validity.VALID:
                valid_count += 1
            elif case.expected_validity == Validity.INVALID:
                invalid_count += 1
            else:
                ambiguous_count += 1
    
    print(f"\n{'=' * 70}")
    print(f"TOTAL: {total} cases")
    print(f"  Valid (trap cases): {valid_count}")
    print(f"  Invalid: {invalid_count}")
    print(f"  Ambiguous: {ambiguous_count}")
    print("=" * 70)


if __name__ == "__main__":
    print_hard_cases_summary()
