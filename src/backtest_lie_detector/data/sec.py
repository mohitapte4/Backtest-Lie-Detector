"""
SEC EDGAR data access utilities.

Provides functions for checking SEC filing timestamps and availability.
"""

import os
from datetime import datetime, timezone
from typing import Optional

import httpx


class SECEdgarData:
    """
    Interface for SEC EDGAR data queries.
    
    Uses the SEC EDGAR API for filing information.
    """
    
    BASE_URL = "https://data.sec.gov"
    
    def __init__(self, user_agent: Optional[str] = None):
        """
        Initialize SEC EDGAR client.
        
        Args:
            user_agent: Required user agent for SEC API.
                       Format: "Company Name admin@example.com"
        """
        self.user_agent = user_agent or os.getenv(
            "SEC_USER_AGENT",
            "BacktestLieDetector research@example.com"
        )
        self.headers = {
            "User-Agent": self.user_agent,
            "Accept": "application/json",
        }
    
    def get_company_filings(
        self,
        cik: str,
        form_type: Optional[str] = None,
        limit: int = 100,
    ) -> list[dict]:
        """
        Get recent filings for a company.
        
        Args:
            cik: SEC Central Index Key (10 digits, zero-padded).
            form_type: Filter by form type (e.g., "10-K", "8-K").
            limit: Maximum filings to return.
        
        Returns:
            List of filing records.
        """
        cik_padded = cik.zfill(10)
        url = f"{self.BASE_URL}/submissions/CIK{cik_padded}.json"
        
        try:
            response = httpx.get(url, headers=self.headers, timeout=30.0)
            response.raise_for_status()
            data = response.json()
        except Exception as e:
            return []
        
        filings = []
        recent = data.get("filings", {}).get("recent", {})
        
        forms = recent.get("form", [])
        dates = recent.get("filingDate", [])
        accessions = recent.get("accessionNumber", [])
        
        for i in range(min(len(forms), limit)):
            if form_type and forms[i] != form_type:
                continue
            
            filings.append({
                "form": forms[i],
                "filing_date": dates[i],
                "accession_number": accessions[i],
            })
        
        return filings
    
    def get_filing_details(
        self,
        cik: str,
        accession_number: str,
    ) -> Optional[dict]:
        """
        Get detailed information about a specific filing.
        
        Args:
            cik: SEC Central Index Key.
            accession_number: Filing accession number.
        
        Returns:
            Filing details including acceptance timestamp.
        """
        cik_padded = cik.zfill(10)
        acc_clean = accession_number.replace("-", "")
        
        url = f"{self.BASE_URL}/Archives/edgar/data/{cik_padded}/{acc_clean}/index.json"
        
        try:
            response = httpx.get(url, headers=self.headers, timeout=30.0)
            response.raise_for_status()
            return response.json()
        except Exception:
            return None


def parse_edgar_timestamp(timestamp_str: str) -> datetime:
    """
    Parse EDGAR acceptance timestamp.
    
    EDGAR timestamps are in Eastern Time.
    
    Args:
        timestamp_str: Timestamp string from EDGAR.
    
    Returns:
        Datetime object (timezone-aware, Eastern Time).
    """
    from zoneinfo import ZoneInfo
    
    # Common EDGAR timestamp formats
    formats = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d",
    ]
    
    for fmt in formats:
        try:
            dt = datetime.strptime(timestamp_str, fmt)
            return dt.replace(tzinfo=ZoneInfo("America/New_York"))
        except ValueError:
            continue
    
    raise ValueError(f"Could not parse timestamp: {timestamp_str}")


def check_filing_available_before(
    filing_timestamp: str,
    decision_timestamp: str,
) -> dict:
    """
    Check if a filing was available before a decision timestamp.
    
    Args:
        filing_timestamp: When the filing was accepted (EDGAR timestamp).
        decision_timestamp: When the trading decision was made.
    
    Returns:
        Dictionary with availability check results.
    """
    try:
        filing_dt = parse_edgar_timestamp(filing_timestamp)
        decision_dt = parse_edgar_timestamp(decision_timestamp)
    except Exception as e:
        return {
            "available": None,
            "error": f"Failed to parse timestamps: {e}",
        }
    
    available = filing_dt < decision_dt
    delta = decision_dt - filing_dt
    
    return {
        "available": available,
        "filing_time": filing_dt.isoformat(),
        "decision_time": decision_dt.isoformat(),
        "time_delta_seconds": delta.total_seconds(),
        "time_delta_hours": delta.total_seconds() / 3600,
    }


# Common filing timing patterns for validation
FILING_TIMING_PATTERNS = {
    "10-K": {
        "deadline_days_after_fy_end": {
            "large_accelerated": 60,
            "accelerated": 75,
            "non_accelerated": 90,
        },
        "typical_filing_window": "4-8 weeks after fiscal year end",
    },
    "10-Q": {
        "deadline_days_after_quarter_end": {
            "large_accelerated": 40,
            "accelerated": 40,
            "non_accelerated": 45,
        },
        "typical_filing_window": "3-6 weeks after quarter end",
    },
    "8-K": {
        "deadline_days_after_event": 4,
        "notes": "Must be filed within 4 business days of material event",
    },
}
