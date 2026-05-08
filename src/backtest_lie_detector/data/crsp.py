"""
CRSP data access utilities.

Placeholder for WRDS CRSP data validation functions.
These are optional and used only for validating benchmark ground truth.
"""

from typing import Optional
from datetime import date


class CRSPData:
    """
    Interface for CRSP data queries.
    
    This is a placeholder class. Full implementation would require
    WRDS credentials and the wrds package.
    """
    
    def __init__(self, wrds_username: Optional[str] = None):
        """
        Initialize CRSP data connection.
        
        Args:
            wrds_username: WRDS username for database connection.
        """
        self.wrds_username = wrds_username
        self._connected = False
    
    def connect(self) -> bool:
        """
        Establish connection to WRDS.
        
        Returns:
            True if connection successful.
        """
        try:
            import wrds
            self._conn = wrds.Connection(wrds_username=self.wrds_username)
            self._connected = True
            return True
        except ImportError:
            print("wrds package not installed. Install with: pip install wrds")
            return False
        except Exception as e:
            print(f"Failed to connect to WRDS: {e}")
            return False
    
    def get_ticker_history(
        self,
        permno: int,
        start_date: date,
        end_date: date
    ) -> list[dict]:
        """
        Get ticker history for a PERMNO.
        
        Args:
            permno: CRSP permanent number.
            start_date: Start of date range.
            end_date: End of date range.
        
        Returns:
            List of ticker records with date ranges.
        """
        if not self._connected:
            raise RuntimeError("Not connected to WRDS")
        
        query = f"""
        SELECT permno, ticker, namedt, nameendt, comnam
        FROM crsp.stocknames
        WHERE permno = {permno}
          AND namedt <= '{end_date}'
          AND nameendt >= '{start_date}'
        ORDER BY namedt
        """
        
        df = self._conn.raw_sql(query)
        return df.to_dict('records')
    
    def check_ticker_valid_on_date(
        self,
        ticker: str,
        check_date: date
    ) -> dict:
        """
        Check if a ticker was valid on a specific date.
        
        Args:
            ticker: Stock ticker to check.
            check_date: Date to check validity.
        
        Returns:
            Dictionary with validity info.
        """
        if not self._connected:
            return {
                "valid": None,
                "error": "Not connected to WRDS",
                "permno": None,
            }
        
        query = f"""
        SELECT permno, ticker, namedt, nameendt, comnam
        FROM crsp.stocknames
        WHERE ticker = '{ticker}'
          AND namedt <= '{check_date}'
          AND nameendt >= '{check_date}'
        """
        
        df = self._conn.raw_sql(query)
        
        if len(df) == 0:
            return {
                "valid": False,
                "error": f"Ticker {ticker} not found for {check_date}",
                "permno": None,
            }
        
        return {
            "valid": True,
            "permno": int(df.iloc[0]['permno']),
            "company": df.iloc[0]['comnam'],
            "start_date": df.iloc[0]['namedt'],
            "end_date": df.iloc[0]['nameendt'],
        }
    
    def get_delisting_info(self, permno: int) -> Optional[dict]:
        """
        Get delisting information for a security.
        
        Args:
            permno: CRSP permanent number.
        
        Returns:
            Delisting info or None if still active.
        """
        if not self._connected:
            return None
        
        query = f"""
        SELECT permno, dlstdt, dlret, dlstcd
        FROM crsp.dsedelist
        WHERE permno = {permno}
        """
        
        df = self._conn.raw_sql(query)
        
        if len(df) == 0:
            return None
        
        return df.iloc[0].to_dict()


# Known ticker changes for validation without WRDS
KNOWN_TICKER_CHANGES = {
    "META": {
        "start_date": "2022-06-09",
        "previous_ticker": "FB",
        "company": "Meta Platforms Inc."
    },
    "GOOGL": {
        "start_date": "2014-04-03",
        "previous_ticker": "GOOG",
        "notes": "Class A shares created in stock split"
    },
    "TWTR": {
        "end_date": "2022-10-27",
        "notes": "Acquired by Elon Musk, went private"
    },
}


def check_ticker_valid_on_date_manual(ticker: str, check_date: str) -> dict:
    """
    Check ticker validity using hardcoded known changes.
    
    This is a fallback for when WRDS is not available.
    
    Args:
        ticker: Stock ticker to check.
        check_date: Date string (YYYY-MM-DD) to check.
    
    Returns:
        Dictionary with validity assessment.
    """
    from datetime import datetime
    check_dt = datetime.strptime(check_date, "%Y-%m-%d").date()
    
    if ticker.upper() in KNOWN_TICKER_CHANGES:
        info = KNOWN_TICKER_CHANGES[ticker.upper()]
        
        if "start_date" in info:
            start = datetime.strptime(info["start_date"], "%Y-%m-%d").date()
            if check_dt < start:
                return {
                    "valid": False,
                    "reason": f"Ticker {ticker} did not exist until {info['start_date']}",
                    "previous_ticker": info.get("previous_ticker"),
                }
        
        if "end_date" in info:
            end = datetime.strptime(info["end_date"], "%Y-%m-%d").date()
            if check_dt > end:
                return {
                    "valid": False,
                    "reason": f"Ticker {ticker} stopped trading after {info['end_date']}",
                    "notes": info.get("notes"),
                }
    
    return {
        "valid": None,
        "reason": "Ticker not in known changes database, validity uncertain"
    }
