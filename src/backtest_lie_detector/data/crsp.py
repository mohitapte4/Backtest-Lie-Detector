"""
CRSP data access utilities.

Provides WRDS CRSP data queries for ticker history, delistings,
and benchmark case validation/generation.
"""

import os
from typing import Optional
from datetime import date
from dotenv import load_dotenv

load_dotenv()


class CRSPData:
    """
    Interface for CRSP data queries via WRDS.
    
    Requires WRDS credentials set via environment variables or .env file.
    """
    
    def __init__(self, wrds_username: Optional[str] = None):
        """
        Initialize CRSP data connection.
        
        Args:
            wrds_username: WRDS username. If None, reads from WRDS_USERNAME env var.
        """
        self.wrds_username = wrds_username or os.getenv("WRDS_USERNAME")
        self._connected = False
        self._conn = None
    
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
            print(f"Connected to WRDS as {self.wrds_username}")
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
    
    def get_ticker_changes(self, min_year: int = 2000) -> list[dict]:
        """
        Find stocks that had ticker changes.
        
        Args:
            min_year: Minimum year to search from.
        
        Returns:
            List of ticker change records.
        """
        if not self._connected:
            raise RuntimeError("Not connected to WRDS")
        
        query = f"""
        WITH ticker_counts AS (
            SELECT permno, COUNT(DISTINCT ticker) as num_tickers
            FROM crsp.stocknames
            WHERE namedt >= '{min_year}-01-01'
            GROUP BY permno
            HAVING COUNT(DISTINCT ticker) > 1
        )
        SELECT s.permno, s.ticker, s.namedt, s.nameendt, s.comnam
        FROM crsp.stocknames s
        INNER JOIN ticker_counts tc ON s.permno = tc.permno
        WHERE s.namedt >= '{min_year}-01-01'
        ORDER BY s.permno, s.namedt
        """
        
        df = self._conn.raw_sql(query)
        return df.to_dict('records')
    
    def get_notable_delistings(
        self,
        min_year: int = 2000,
        dlstcd_min: int = 400,
        dlstcd_max: int = 599
    ) -> list[dict]:
        """
        Get notable delistings (bankruptcies, liquidations).
        
        Args:
            min_year: Minimum year.
            dlstcd_min: Minimum delisting code (400 = liquidation).
            dlstcd_max: Maximum delisting code (599 = dropped).
        
        Returns:
            List of delisting records with company names.
        """
        if not self._connected:
            raise RuntimeError("Not connected to WRDS")
        
        query = f"""
        SELECT d.permno, d.dlstdt, d.dlret, d.dlstcd, s.ticker, s.comnam
        FROM crsp.dsedelist d
        LEFT JOIN (
            SELECT permno, ticker, comnam
            FROM crsp.stocknames
            WHERE nameendt = (
                SELECT MAX(nameendt) FROM crsp.stocknames s2 
                WHERE s2.permno = crsp.stocknames.permno
            )
        ) s ON d.permno = s.permno
        WHERE d.dlstdt >= '{min_year}-01-01'
          AND d.dlstcd BETWEEN {dlstcd_min} AND {dlstcd_max}
        ORDER BY d.dlstdt DESC
        LIMIT 50
        """
        
        df = self._conn.raw_sql(query)
        return df.to_dict('records')
    
    def get_company_by_name(self, name_pattern: str) -> list[dict]:
        """
        Search for companies by name pattern.
        
        Args:
            name_pattern: SQL LIKE pattern for company name.
        
        Returns:
            List of matching company records.
        """
        if not self._connected:
            raise RuntimeError("Not connected to WRDS")
        
        query = f"""
        SELECT DISTINCT permno, ticker, comnam, namedt, nameendt
        FROM crsp.stocknames
        WHERE UPPER(comnam) LIKE UPPER('%{name_pattern}%')
        ORDER BY namedt DESC
        LIMIT 20
        """
        
        df = self._conn.raw_sql(query)
        return df.to_dict('records')
    
    def get_famous_ticker_histories(self) -> dict:
        """
        Get ticker histories for famous companies with known changes.
        
        Returns:
            Dictionary of company name to ticker history.
        """
        if not self._connected:
            raise RuntimeError("Not connected to WRDS")
        
        # Famous companies with known ticker changes
        famous = {
            "Meta/Facebook": "SELECT * FROM crsp.stocknames WHERE permno = 13407 ORDER BY namedt",
            "Alphabet/Google": "SELECT * FROM crsp.stocknames WHERE permno IN (90319, 93436) ORDER BY namedt",
            "AT&T": "SELECT * FROM crsp.stocknames WHERE ticker = 'T' ORDER BY namedt",
        }
        
        results = {}
        for name, query in famous.items():
            try:
                df = self._conn.raw_sql(query)
                results[name] = df.to_dict('records')
            except Exception as e:
                results[name] = {"error": str(e)}
        
        return results


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
