"""
Pure Temporal Ordering Cases for V6 Benchmark.

These cases isolate temporal reasoning from domain complexity. They test
whether LLMs can detect anachronisms - events that are out of chronological order.

This addresses Jeremy's insight: "Does the LLM have a good sense of time and
ordering, enough to detect when things appear slightly out of order?"

Unlike other cases that require CRSP/Compustat semantics or corporate action
knowledge, these cases are pure chronology puzzles.
"""

from backtest_lie_detector.schemas import (
    BenchmarkCase,
    Difficulty,
    Module,
    SourceFields,
    Validity,
    ViolationType,
)


CHRONOLOGY_CASES = [
    # =========================================================================
    # Case 1: Simple Date Ordering - Valid
    # =========================================================================
    BenchmarkCase(
        id="chrono_filing_before_trade_valid",
        module=Module.FILING_CLOCK,
        difficulty=Difficulty.EASY,
        prompt=(
            "A researcher uses Q4 2019 earnings data to form a portfolio on March 1, 2020. "
            "The company's 10-K containing this data was filed on February 15, 2020. "
            "Audit this workflow."
        ),
        expected_validity=Validity.VALID,
        expected_violations=[],
        expected_repair=[],
        ground_truth_notes=(
            "The 10-K was filed February 15, 2020. The portfolio is formed March 1, 2020. "
            "February 15 comes before March 1. The data was available. Valid."
        ),
        source_fields=SourceFields(
            filing_timestamp="2020-02-15",
            decision_timestamp="2020-03-01",
        ),
        data_source="manual",
        case_tags=["chronology_trap", "pure_temporal"],
        source_note="Pure temporal ordering test",
    ),

    # =========================================================================
    # Case 2: Simple Date Ordering - Invalid
    # =========================================================================
    BenchmarkCase(
        id="chrono_trade_before_filing_invalid",
        module=Module.FILING_CLOCK,
        difficulty=Difficulty.EASY,
        prompt=(
            "A researcher uses Q4 2019 earnings data to form a portfolio on January 15, 2020. "
            "The company's 10-K containing this data was filed on February 15, 2020. "
            "Audit this workflow."
        ),
        expected_validity=Validity.INVALID,
        expected_violations=[ViolationType.FILING_CLOCK_LEAKAGE],
        expected_repair=[
            "The 10-K was not filed until February 15, 2020.",
            "Cannot use this data for a January 15, 2020 portfolio.",
            "Wait until after the filing date to use this information."
        ],
        ground_truth_notes=(
            "The portfolio is formed January 15, 2020. The 10-K was filed February 15, 2020. "
            "January 15 comes before February 15. The data was not yet available. Invalid."
        ),
        source_fields=SourceFields(
            filing_timestamp="2020-02-15",
            decision_timestamp="2020-01-15",
        ),
        data_source="manual",
        case_tags=["chronology_trap", "pure_temporal"],
        source_note="Pure temporal ordering test",
    ),

    # =========================================================================
    # Case 3: Intraday Ordering - Invalid (15 minutes before)
    # =========================================================================
    BenchmarkCase(
        id="chrono_intraday_15min_before",
        module=Module.FILING_CLOCK,
        difficulty=Difficulty.EASY,
        prompt=(
            "An 8-K filing was accepted by EDGAR at 10:30 AM ET on April 5, 2023. "
            "A trading algorithm executes a trade at 10:15 AM ET on the same day "
            "using information from that 8-K. Audit this workflow."
        ),
        expected_validity=Validity.INVALID,
        expected_violations=[ViolationType.FILING_CLOCK_LEAKAGE],
        expected_repair=[
            "The 8-K was accepted at 10:30 AM.",
            "The trade was at 10:15 AM, which is 15 minutes before the filing.",
            "Trade must occur after the filing acceptance time."
        ],
        ground_truth_notes=(
            "10:15 AM is before 10:30 AM. The filing did not exist yet when the trade "
            "was placed. This is a clear chronological violation."
        ),
        source_fields=SourceFields(
            filing_timestamp="2023-04-05 10:30:00 America/New_York",
            decision_timestamp="2023-04-05 10:15:00 America/New_York",
        ),
        data_source="manual",
        case_tags=["chronology_trap", "pure_temporal", "requires_timestamp_reasoning"],
        source_note="Pure temporal ordering test - intraday",
    ),

    # =========================================================================
    # Case 4: Intraday Ordering - Valid (5 minutes after)
    # =========================================================================
    BenchmarkCase(
        id="chrono_intraday_5min_after_valid",
        module=Module.FILING_CLOCK,
        difficulty=Difficulty.EASY,
        prompt=(
            "An 8-K filing was accepted by EDGAR at 9:30 AM ET on June 12, 2023. "
            "A trading algorithm executes a trade at 9:35 AM ET on the same day "
            "using information from that 8-K. Audit this workflow."
        ),
        expected_validity=Validity.VALID,
        expected_violations=[],
        expected_repair=[],
        ground_truth_notes=(
            "9:35 AM is after 9:30 AM. The filing was accepted 5 minutes before the trade. "
            "The information was publicly available. Valid."
        ),
        source_fields=SourceFields(
            filing_timestamp="2023-06-12 09:30:00 America/New_York",
            decision_timestamp="2023-06-12 09:35:00 America/New_York",
        ),
        data_source="manual",
        case_tags=["chronology_trap", "pure_temporal", "requires_timestamp_reasoning"],
        source_note="Pure temporal ordering test - intraday close call",
    ),

    # =========================================================================
    # Case 5: Ticker Existence - Invalid (8 days before)
    # =========================================================================
    BenchmarkCase(
        id="chrono_ticker_before_existence",
        module=Module.TICKER_TIME_MACHINE,
        difficulty=Difficulty.EASY,
        prompt=(
            "A researcher queries stock data for ticker META on June 1, 2022. "
            "The META ticker began trading on June 9, 2022 when Facebook changed its name. "
            "Audit this workflow."
        ),
        expected_validity=Validity.INVALID,
        expected_violations=[ViolationType.IDENTIFIER_TIME_TRAVEL],
        expected_repair=[
            "META did not exist as a ticker until June 9, 2022.",
            "On June 1, 2022, the company traded under ticker FB.",
            "Use FB for any date before June 9, 2022."
        ],
        ground_truth_notes=(
            "June 1 is before June 9. The ticker META did not exist on June 1, 2022. "
            "This is a chronological impossibility."
        ),
        source_fields=SourceFields(
            ticker="META",
            event_date="2022-06-01",
            extra={"ticker_start_date": "2022-06-09"},
        ),
        data_source="manual",
        case_tags=["chronology_trap", "pure_temporal", "requires_identifier_reasoning"],
        source_note="Pure temporal ordering test - ticker existence",
    ),

    # =========================================================================
    # Case 6: Cross-Midnight Edge Case - Invalid
    # =========================================================================
    BenchmarkCase(
        id="chrono_cross_midnight_invalid",
        module=Module.FILING_CLOCK,
        difficulty=Difficulty.MEDIUM,
        prompt=(
            "A filing was accepted at 11:59 PM ET on March 1, 2023. "
            "A trade was executed at 12:01 AM ET on March 1, 2023 using that filing. "
            "Audit this workflow."
        ),
        expected_validity=Validity.INVALID,
        expected_violations=[ViolationType.FILING_CLOCK_LEAKAGE],
        expected_repair=[
            "12:01 AM on March 1 is the very beginning of March 1.",
            "11:59 PM on March 1 is the very end of March 1.",
            "The trade at 12:01 AM occurs almost 24 hours before the 11:59 PM filing."
        ],
        ground_truth_notes=(
            "12:01 AM on March 1 is at the start of the day. 11:59 PM on March 1 is at "
            "the end of the day. The trade precedes the filing by nearly 24 hours. "
            "This tests understanding of clock time within a day."
        ),
        source_fields=SourceFields(
            filing_timestamp="2023-03-01 23:59:00 America/New_York",
            decision_timestamp="2023-03-01 00:01:00 America/New_York",
        ),
        data_source="manual",
        case_tags=["chronology_trap", "pure_temporal", "requires_timestamp_reasoning"],
        source_note="Pure temporal ordering test - same day AM/PM confusion",
    ),

    # =========================================================================
    # Case 7: Year Boundary - Invalid
    # =========================================================================
    BenchmarkCase(
        id="chrono_year_boundary_invalid",
        module=Module.ACCOUNTING_AVAILABILITY,
        difficulty=Difficulty.EASY,
        prompt=(
            "A researcher uses fiscal year 2022 annual data for a portfolio formed on "
            "December 15, 2022. The 10-K for fiscal year 2022 was filed on March 1, 2023. "
            "Audit this workflow."
        ),
        expected_validity=Validity.INVALID,
        expected_violations=[ViolationType.ACCOUNTING_AVAILABILITY_LEAKAGE],
        expected_repair=[
            "The FY2022 10-K was not filed until March 2023.",
            "On December 15, 2022, FY2022 was not even complete.",
            "Use FY2021 data, which would have been available."
        ],
        ground_truth_notes=(
            "December 2022 comes before March 2023. The FY2022 data was not available "
            "in December 2022. This is a simple year-boundary chronology error."
        ),
        source_fields=SourceFields(
            portfolio_date="2022-12-15",
            filing_date="2023-03-01",
            fiscal_year_end="2022-12-31",
        ),
        data_source="manual",
        case_tags=["chronology_trap", "pure_temporal"],
        source_note="Pure temporal ordering test - year boundary",
    ),

    # =========================================================================
    # Case 8: Same Minute - Valid (just barely)
    # =========================================================================
    BenchmarkCase(
        id="chrono_same_minute_valid",
        module=Module.FILING_CLOCK,
        difficulty=Difficulty.MEDIUM,
        prompt=(
            "An 8-K was accepted at 2:30:00 PM ET. A trade executes at 2:30:45 PM ET "
            "the same day using that filing. Audit this workflow."
        ),
        expected_validity=Validity.VALID,
        expected_violations=[],
        expected_repair=[],
        ground_truth_notes=(
            "2:30:45 PM is 45 seconds after 2:30:00 PM. The filing was accepted first. "
            "While very close, this is chronologically valid."
        ),
        source_fields=SourceFields(
            filing_timestamp="2023-07-20 14:30:00 America/New_York",
            decision_timestamp="2023-07-20 14:30:45 America/New_York",
        ),
        data_source="manual",
        case_tags=["chronology_trap", "pure_temporal", "requires_timestamp_reasoning"],
        source_note="Pure temporal ordering test - seconds matter",
    ),

    # =========================================================================
    # Case 9: Misleading "after" language - Actually INVALID
    # The phrase "after the announcement" sounds valid but dates reveal it's not
    # =========================================================================
    BenchmarkCase(
        id="chrono_misleading_after_invalid",
        module=Module.FILING_CLOCK,
        difficulty=Difficulty.HARD,
        prompt=(
            "A researcher studies market reactions after Apple's earnings announcement. "
            "They form a portfolio on January 25, 2024 to capture the post-announcement drift. "
            "Apple announced Q1 FY2024 earnings on February 1, 2024. "
            "Audit this workflow."
        ),
        expected_validity=Validity.INVALID,
        expected_violations=[ViolationType.FILING_CLOCK_LEAKAGE],
        expected_repair=[
            "The portfolio was formed January 25, but the announcement was February 1.",
            "Cannot study 'post-announcement' effects before the announcement happens.",
            "Form the portfolio after February 1, 2024."
        ],
        ground_truth_notes=(
            "The language says 'after the announcement' but the dates show January 25 < February 1. "
            "This tests whether the model is fooled by narrative framing vs actual dates."
        ),
        source_fields=SourceFields(
            decision_timestamp="2024-01-25",
            extra={"announcement_date": "2024-02-01"},
        ),
        data_source="manual",
        case_tags=["chronology_trap", "pure_temporal", "misleading_language"],
        source_note="Tests if model is fooled by 'after' language when dates contradict",
    ),

    # =========================================================================
    # Case 10: Misleading "before" language - Actually VALID
    # The phrase "before the crash" sounds suspicious but it's actually fine
    # =========================================================================
    BenchmarkCase(
        id="chrono_misleading_before_valid",
        module=Module.SURVIVORSHIP_DELISTING,
        difficulty=Difficulty.HARD,
        prompt=(
            "A researcher builds a portfolio on February 1, 2020 using data available at that time. "
            "They note this was 'constructed before the COVID crash' for context. "
            "The COVID market crash began around March 9, 2020. "
            "Audit this workflow."
        ),
        expected_validity=Validity.VALID,
        expected_violations=[],
        expected_repair=[],
        ground_truth_notes=(
            "February 1 is before March 9. The portfolio was formed before the crash, using "
            "data available at that time. The 'before the crash' language is just context, "
            "not an indication of look-ahead bias. This is valid."
        ),
        source_fields=SourceFields(
            decision_timestamp="2020-02-01",
            extra={"crash_date": "2020-03-09"},
        ),
        data_source="manual",
        case_tags=["chronology_trap", "pure_temporal", "trap_valid", "misleading_language"],
        source_note="Tests if model flags valid workflow due to suspicious language",
    ),

    # =========================================================================
    # Case 11: Next day but wrong year - INVALID
    # "March 2" looks like it comes after "March 1" but years matter
    # =========================================================================
    BenchmarkCase(
        id="chrono_wrong_year_invalid",
        module=Module.FILING_CLOCK,
        difficulty=Difficulty.MEDIUM,
        prompt=(
            "A 10-K was filed on March 1, 2024. A researcher uses this data for a "
            "portfolio formed on March 2, 2023. Audit this workflow."
        ),
        expected_validity=Validity.INVALID,
        expected_violations=[ViolationType.FILING_CLOCK_LEAKAGE],
        expected_repair=[
            "The portfolio was formed March 2, 2023.",
            "The 10-K was filed March 1, 2024 - almost a year LATER.",
            "Cannot use 2024 filing for a 2023 portfolio."
        ],
        ground_truth_notes=(
            "March 2, 2023 comes BEFORE March 1, 2024. The day-of-month (2 > 1) might "
            "mislead, but the year difference makes this clearly invalid."
        ),
        source_fields=SourceFields(
            filing_timestamp="2024-03-01",
            decision_timestamp="2023-03-02",
        ),
        data_source="manual",
        case_tags=["chronology_trap", "pure_temporal"],
        source_note="Tests if model catches year mismatch despite day suggesting order",
    ),

    # =========================================================================
    # Case 12: Large gap sounds suspicious but is VALID
    # =========================================================================
    BenchmarkCase(
        id="chrono_large_gap_valid",
        module=Module.ACCOUNTING_AVAILABILITY,
        difficulty=Difficulty.MEDIUM,
        prompt=(
            "A researcher uses Q4 2019 earnings data for a portfolio formed on "
            "December 15, 2020. The 10-K was filed on February 28, 2020. "
            "Audit this workflow."
        ),
        expected_validity=Validity.VALID,
        expected_violations=[],
        expected_repair=[],
        ground_truth_notes=(
            "The 10-K was filed February 2020. The portfolio is formed December 2020. "
            "That's a 10-month gap, which is unusually long but not invalid. "
            "The data was available. Using stale data is a methodology choice, not a violation."
        ),
        source_fields=SourceFields(
            filing_timestamp="2020-02-28",
            decision_timestamp="2020-12-15",
        ),
        data_source="manual",
        case_tags=["chronology_trap", "pure_temporal", "trap_valid"],
        source_note="Tests if model incorrectly flags valid workflow with large time gap",
    ),

    # =========================================================================
    # Case 13: "Latest" data language but actually old - VALID
    # =========================================================================
    BenchmarkCase(
        id="chrono_latest_is_old_valid",
        module=Module.ACCOUNTING_AVAILABILITY,
        difficulty=Difficulty.HARD,
        prompt=(
            "On June 1, 2024, a researcher forms a portfolio using 'the latest available' "
            "annual earnings data. For most firms, this is FY2023 data from 10-Ks filed "
            "in February-March 2024. Audit this workflow."
        ),
        expected_validity=Validity.VALID,
        expected_violations=[],
        expected_repair=[],
        ground_truth_notes=(
            "On June 1, 2024, the latest available annual data is indeed FY2023. "
            "FY2024 data won't be filed until early 2025. Using 3-4 month old filings "
            "for 'latest' data is correct methodology."
        ),
        source_fields=SourceFields(
            decision_timestamp="2024-06-01",
            extra={"data_period": "FY2023", "typical_filing": "Feb-Mar 2024"},
        ),
        data_source="manual",
        case_tags=["chronology_trap", "pure_temporal", "trap_valid"],
        source_note="Tests if model understands 'latest available' vs 'most recent period'",
    ),

    # =========================================================================
    # Case 14: Timezone trick - looks same day but different - INVALID
    # =========================================================================
    BenchmarkCase(
        id="chrono_timezone_trick_invalid",
        module=Module.FILING_CLOCK,
        difficulty=Difficulty.HARD,
        prompt=(
            "A filing was accepted at 11:00 PM ET on Monday, January 15. "
            "A researcher in Tokyo executes a trade at 9:00 AM Tokyo time on Tuesday, January 16, "
            "claiming the filing was 'already public' since it's the next calendar day. "
            "Audit this workflow."
        ),
        expected_validity=Validity.INVALID,
        expected_violations=[ViolationType.FILING_CLOCK_LEAKAGE, ViolationType.TIMEZONE_ERROR],
        expected_repair=[
            "11:00 PM ET Monday = 1:00 PM Tuesday Tokyo time (14 hours ahead).",
            "9:00 AM Tuesday Tokyo = 7:00 PM Monday ET.",
            "The trade at 7:00 PM ET Monday is BEFORE the 11:00 PM ET Monday filing."
        ],
        ground_truth_notes=(
            "Tokyo is 14 hours ahead of ET. 9 AM Tuesday Tokyo = 7 PM Monday ET. "
            "The filing at 11 PM ET Monday hadn't happened yet when the trade was placed. "
            "The 'next calendar day' reasoning is wrong due to timezone conversion."
        ),
        source_fields=SourceFields(
            filing_timestamp="Monday 23:00 ET",
            decision_timestamp="Tuesday 09:00 Tokyo",
        ),
        data_source="manual",
        case_tags=["chronology_trap", "pure_temporal", "requires_timestamp_reasoning"],
        source_note="Tests timezone reasoning - calendar day doesn't guarantee order",
    ),

    # =========================================================================
    # Case 15: Confident but wrong framing - INVALID
    # Professional language + specific times, but still wrong
    # =========================================================================
    BenchmarkCase(
        id="chrono_confident_wrong_invalid",
        module=Module.FILING_CLOCK,
        difficulty=Difficulty.HARD,
        prompt=(
            "Our systematic trading strategy has strict compliance controls. We only trade "
            "on SEC filings after EDGAR acceptance. On March 15, 2024, we executed trades "
            "at 2:45 PM ET based on an 8-K that was accepted at 3:15 PM ET the same day. "
            "Our compliance team verified all timestamps. Audit this workflow."
        ),
        expected_validity=Validity.INVALID,
        expected_violations=[ViolationType.FILING_CLOCK_LEAKAGE],
        expected_repair=[
            "Despite the compliance language, 2:45 PM is before 3:15 PM.",
            "The trade preceded the filing by 30 minutes.",
            "Compliance verification appears to have failed."
        ],
        ground_truth_notes=(
            "The professional framing ('strict compliance', 'verified timestamps') might "
            "make the model trust the workflow, but 2:45 PM < 3:15 PM. The chronology "
            "is simply wrong regardless of how confident the description sounds."
        ),
        source_fields=SourceFields(
            filing_timestamp="2024-03-15 15:15:00 America/New_York",
            decision_timestamp="2024-03-15 14:45:00 America/New_York",
        ),
        data_source="manual",
        case_tags=["chronology_trap", "pure_temporal", "misleading_language", "false_valid_trap"],
        source_note="Tests if confident professional language fools the model",
    ),
]


def get_chronology_cases() -> list[BenchmarkCase]:
    """Return all pure chronology test cases."""
    return CHRONOLOGY_CASES


def get_case_ids() -> list[str]:
    """Return all chronology case IDs."""
    return [case.id for case in CHRONOLOGY_CASES]


def print_chronology_summary():
    """Print summary of chronology cases."""
    print("=" * 70)
    print("CHRONOLOGY CASES SUMMARY (V6)")
    print("=" * 70)
    
    valid_count = len([c for c in CHRONOLOGY_CASES if c.expected_validity == Validity.VALID])
    invalid_count = len([c for c in CHRONOLOGY_CASES if c.expected_validity == Validity.INVALID])
    
    print(f"\nTotal cases: {len(CHRONOLOGY_CASES)}")
    print(f"  Valid: {valid_count}")
    print(f"  Invalid: {invalid_count}")
    
    print(f"\nCases:")
    for case in CHRONOLOGY_CASES:
        status = "[V]" if case.expected_validity == Validity.VALID else "[X]"
        print(f"  {status} {case.id}: {case.difficulty.value}")
    
    print("=" * 70)


if __name__ == "__main__":
    print_chronology_summary()
