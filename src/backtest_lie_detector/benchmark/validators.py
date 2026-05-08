"""
Benchmark case validators.

Provides functions to validate ground truth for benchmark cases
using external data sources where available.
"""

from datetime import datetime
from typing import Optional

from backtest_lie_detector.schemas import BenchmarkCase, Module, ViolationType
from backtest_lie_detector.data.crsp import check_ticker_valid_on_date_manual
from backtest_lie_detector.data.sec import check_filing_available_before


def check_ticker_valid_on_date(ticker: str, date: str) -> dict:
    """
    Check if a ticker was valid on a given date.
    
    Uses manual lookup of known ticker changes.
    
    Args:
        ticker: Stock ticker symbol.
        date: Date in YYYY-MM-DD format.
    
    Returns:
        Dictionary with validity check results.
    """
    return check_ticker_valid_on_date_manual(ticker, date)


def check_filing_available_before_decision(
    filing_timestamp: str,
    decision_timestamp: str,
) -> dict:
    """
    Check if filing information was available before decision time.
    
    Args:
        filing_timestamp: When filing was accepted by EDGAR.
        decision_timestamp: When trading decision was made.
    
    Returns:
        Dictionary with availability check results.
    """
    return check_filing_available_before(filing_timestamp, decision_timestamp)


def check_accounting_data_available(
    portfolio_date: str,
    fiscal_period_end: str,
    filing_date: Optional[str] = None,
    typical_lag_days: int = 60,
) -> dict:
    """
    Check if accounting data would have been available.
    
    Args:
        portfolio_date: When portfolio was formed.
        fiscal_period_end: End of fiscal period for data.
        filing_date: Actual filing date if known.
        typical_lag_days: Typical filing lag if date unknown.
    
    Returns:
        Dictionary with availability assessment.
    """
    try:
        portfolio_dt = datetime.strptime(portfolio_date, "%Y-%m-%d")
        fiscal_dt = datetime.strptime(fiscal_period_end, "%Y-%m-%d")
        
        if filing_date:
            filing_dt = datetime.strptime(filing_date, "%Y-%m-%d")
            available = portfolio_dt >= filing_dt
            days_diff = (portfolio_dt - filing_dt).days
        else:
            # Estimate using typical lag
            from datetime import timedelta
            estimated_filing = fiscal_dt + timedelta(days=typical_lag_days)
            available = portfolio_dt >= estimated_filing
            days_diff = (portfolio_dt - estimated_filing).days
            filing_dt = estimated_filing
        
        return {
            "available": available,
            "portfolio_date": portfolio_date,
            "fiscal_period_end": fiscal_period_end,
            "filing_date": filing_dt.strftime("%Y-%m-%d"),
            "days_after_filing": days_diff if available else None,
            "days_before_filing": -days_diff if not available else None,
        }
    
    except Exception as e:
        return {
            "available": None,
            "error": str(e),
        }


def check_survivorship_issue(
    backtest_start: str,
    backtest_end: str,
    universe_filter: str,
) -> dict:
    """
    Check if a universe filter introduces survivorship bias.
    
    Args:
        backtest_start: Start date of backtest.
        backtest_end: End date of backtest.
        universe_filter: Description of how universe is filtered.
    
    Returns:
        Dictionary with survivorship bias assessment.
    """
    filter_lower = universe_filter.lower()
    
    # Check for common survivorship bias patterns
    suspicious_patterns = [
        "current",
        "still listed",
        "still trading",
        "active",
        "today",
        "present",
        "2025",
        "2026",
        "exclude.*delist",
    ]
    
    import re
    has_bias_indicator = any(
        re.search(pattern, filter_lower) for pattern in suspicious_patterns
    )
    
    return {
        "has_survivorship_bias": has_bias_indicator,
        "universe_filter": universe_filter,
        "reason": (
            "Universe filter appears to use future information" 
            if has_bias_indicator 
            else "No obvious survivorship bias detected"
        ),
        "confidence": "high" if has_bias_indicator else "low",
    }


def validate_case_ground_truth(case: BenchmarkCase) -> dict:
    """
    Validate the ground truth of a benchmark case.
    
    Runs appropriate validators based on case module and violations.
    
    Args:
        case: The benchmark case to validate.
    
    Returns:
        Dictionary with validation results.
    """
    results = {
        "case_id": case.id,
        "module": case.module.value,
        "expected_validity": case.expected_validity.value,
        "validations": [],
    }
    
    source = case.source_fields
    
    # Ticker Time Machine validation
    if case.module == Module.TICKER_TIME_MACHINE:
        if source.bad_ticker and source.event_date:
            ticker_check = check_ticker_valid_on_date(
                source.bad_ticker, 
                source.event_date
            )
            results["validations"].append({
                "type": "ticker_validity",
                "ticker": source.bad_ticker,
                "date": source.event_date,
                "result": ticker_check,
            })
    
    # Filing Clock validation
    if case.module == Module.FILING_CLOCK:
        if source.filing_timestamp and source.decision_timestamp:
            filing_check = check_filing_available_before_decision(
                source.filing_timestamp,
                source.decision_timestamp
            )
            results["validations"].append({
                "type": "filing_availability",
                "result": filing_check,
            })
    
    # Accounting Availability validation
    if case.module == Module.ACCOUNTING_AVAILABILITY:
        if source.portfolio_date and source.fiscal_year_end:
            acct_check = check_accounting_data_available(
                source.portfolio_date,
                source.fiscal_year_end,
                source.filing_date,
            )
            results["validations"].append({
                "type": "accounting_availability",
                "result": acct_check,
            })
    
    # Survivorship validation
    if case.module == Module.SURVIVORSHIP_DELISTING:
        if source.universe_filter:
            surv_check = check_survivorship_issue(
                source.backtest_start or "unknown",
                source.backtest_end or "unknown",
                source.universe_filter,
            )
            results["validations"].append({
                "type": "survivorship_check",
                "result": surv_check,
            })
    
    # Overall consistency check
    if results["validations"]:
        # Check if validations are consistent with expected validity
        all_consistent = True
        for validation in results["validations"]:
            if "available" in validation.get("result", {}):
                available = validation["result"]["available"]
                if available is not None:
                    if case.expected_validity.value == "valid" and not available:
                        all_consistent = False
                    if case.expected_validity.value == "invalid" and available:
                        all_consistent = False
        
        results["consistent"] = all_consistent
    else:
        results["consistent"] = None
        results["note"] = "No automated validations available for this case"
    
    return results


def validate_all_cases(cases: list[BenchmarkCase]) -> list[dict]:
    """
    Validate all benchmark cases.
    
    Args:
        cases: List of benchmark cases.
    
    Returns:
        List of validation results.
    """
    return [validate_case_ground_truth(case) for case in cases]
