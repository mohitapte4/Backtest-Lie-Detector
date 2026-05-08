"""Benchmark construction and validation utilities."""

from backtest_lie_detector.benchmark.build_cases import (
    create_ticker_time_machine_case,
    create_filing_clock_case,
    create_accounting_availability_case,
    create_survivorship_case,
    generate_all_cases,
    save_benchmark,
    load_benchmark,
)
from backtest_lie_detector.benchmark.examples import SEED_CASES
from backtest_lie_detector.benchmark.validators import (
    check_ticker_valid_on_date,
    check_filing_available_before,
    validate_case_ground_truth,
)

__all__ = [
    "create_ticker_time_machine_case",
    "create_filing_clock_case", 
    "create_accounting_availability_case",
    "create_survivorship_case",
    "generate_all_cases",
    "save_benchmark",
    "load_benchmark",
    "SEED_CASES",
    "check_ticker_valid_on_date",
    "check_filing_available_before",
    "validate_case_ground_truth",
]
