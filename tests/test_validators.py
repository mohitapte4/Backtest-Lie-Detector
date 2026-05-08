"""Tests for benchmark validators."""

import pytest

from backtest_lie_detector.benchmark.validators import (
    check_ticker_valid_on_date,
    check_filing_available_before_decision,
    check_accounting_data_available,
    check_survivorship_issue,
)


class TestTickerValidation:
    """Tests for ticker validity checking."""
    
    def test_meta_before_rebrand(self):
        """META was not valid before June 2022."""
        result = check_ticker_valid_on_date("META", "2018-03-20")
        
        assert result["valid"] is False
        assert "2022" in result.get("reason", "") or result.get("valid") is False
    
    def test_meta_after_rebrand(self):
        """META should be valid after June 2022."""
        result = check_ticker_valid_on_date("META", "2023-01-01")
        
        # Either valid or unknown (if not in database)
        assert result["valid"] in [True, None]
    
    def test_unknown_ticker(self):
        """Unknown tickers should return uncertain."""
        result = check_ticker_valid_on_date("UNKNOWNTICKER", "2020-01-01")
        
        assert result["valid"] is None


class TestFilingAvailability:
    """Tests for filing availability checking."""
    
    def test_filing_before_decision(self):
        """Filing available before decision should be valid."""
        result = check_filing_available_before_decision(
            filing_timestamp="2023-01-15 09:00:00",
            decision_timestamp="2023-01-15 14:00:00",
        )
        
        assert result["available"] is True
    
    def test_filing_after_decision(self):
        """Filing after decision should be invalid."""
        result = check_filing_available_before_decision(
            filing_timestamp="2023-01-15 16:00:00",
            decision_timestamp="2023-01-15 14:00:00",
        )
        
        assert result["available"] is False
    
    def test_same_timestamp(self):
        """Same timestamp should be invalid (not strictly before)."""
        result = check_filing_available_before_decision(
            filing_timestamp="2023-01-15 14:00:00",
            decision_timestamp="2023-01-15 14:00:00",
        )
        
        assert result["available"] is False


class TestAccountingAvailability:
    """Tests for accounting data availability."""
    
    def test_data_available_after_filing(self):
        """Data should be available after 10-K is filed."""
        result = check_accounting_data_available(
            portfolio_date="2023-04-01",
            fiscal_period_end="2022-12-31",
            filing_date="2023-02-28",
        )
        
        assert result["available"] is True
    
    def test_data_not_available_before_filing(self):
        """Data should not be available before 10-K is filed."""
        result = check_accounting_data_available(
            portfolio_date="2023-01-15",
            fiscal_period_end="2022-12-31",
            filing_date="2023-02-28",
        )
        
        assert result["available"] is False
    
    def test_estimated_lag(self):
        """Without filing date, use typical lag."""
        result = check_accounting_data_available(
            portfolio_date="2023-03-15",
            fiscal_period_end="2022-12-31",
            filing_date=None,
            typical_lag_days=60,
        )
        
        # March 15 is 74 days after Dec 31, should be available with 60-day lag
        assert result["available"] is True


class TestSurvivorshipCheck:
    """Tests for survivorship bias detection."""
    
    def test_current_universe_flagged(self):
        """Using current/still listed should be flagged."""
        result = check_survivorship_issue(
            backtest_start="2000-01-01",
            backtest_end="2020-12-31",
            universe_filter="companies still listed in 2025",
        )
        
        assert result["has_survivorship_bias"] is True
    
    def test_point_in_time_ok(self):
        """Point-in-time universe should not be flagged."""
        result = check_survivorship_issue(
            backtest_start="2000-01-01",
            backtest_end="2020-12-31",
            universe_filter="all common stocks with valid returns each month",
        )
        
        assert result["has_survivorship_bias"] is False
    
    def test_current_keyword_flagged(self):
        """The word 'current' should trigger a flag."""
        result = check_survivorship_issue(
            backtest_start="2010-01-01",
            backtest_end="2020-12-31",
            universe_filter="current S&P 500 constituents",
        )
        
        assert result["has_survivorship_bias"] is True
