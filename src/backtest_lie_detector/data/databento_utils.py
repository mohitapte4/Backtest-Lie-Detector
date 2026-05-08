"""
Databento data utilities.

Placeholder for Databento market data access.
Used for intraday event timing validation.
"""

from typing import Optional
from datetime import datetime


class DatabentoClient:
    """
    Placeholder interface for Databento market data.
    
    Full implementation would require Databento API key.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Databento client.
        
        Args:
            api_key: Databento API key.
        """
        self.api_key = api_key
        self._connected = False
    
    def get_market_hours(self, date_str: str, exchange: str = "XNYS") -> dict:
        """
        Get market hours for a given date.
        
        Args:
            date_str: Date in YYYY-MM-DD format.
            exchange: Exchange code (XNYS for NYSE).
        
        Returns:
            Dictionary with market hours info.
        """
        # Standard NYSE hours (placeholder)
        return {
            "date": date_str,
            "exchange": exchange,
            "pre_market_start": "04:00:00",
            "market_open": "09:30:00",
            "market_close": "16:00:00",
            "after_hours_end": "20:00:00",
            "timezone": "America/New_York",
        }
    
    def is_market_open(self, timestamp: datetime) -> bool:
        """
        Check if market was open at a given timestamp.
        
        Args:
            timestamp: Timestamp to check.
        
        Returns:
            True if market was open.
        """
        # Simple check: 9:30 AM - 4:00 PM ET, weekdays
        if timestamp.weekday() >= 5:  # Saturday, Sunday
            return False
        
        hour = timestamp.hour
        minute = timestamp.minute
        
        # After 9:30 AM and before 4:00 PM
        if hour < 9 or (hour == 9 and minute < 30):
            return False
        if hour >= 16:
            return False
        
        return True


# US Market Holidays (partial list for validation)
US_MARKET_HOLIDAYS_2023 = [
    "2023-01-02",  # New Year's Day (observed)
    "2023-01-16",  # MLK Day
    "2023-02-20",  # Presidents Day
    "2023-04-07",  # Good Friday
    "2023-05-29",  # Memorial Day
    "2023-06-19",  # Juneteenth
    "2023-07-04",  # Independence Day
    "2023-09-04",  # Labor Day
    "2023-11-23",  # Thanksgiving
    "2023-12-25",  # Christmas
]


def is_trading_day(date_str: str) -> bool:
    """
    Check if a date is a trading day.
    
    Args:
        date_str: Date in YYYY-MM-DD format.
    
    Returns:
        True if the date is a trading day.
    """
    from datetime import datetime
    
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    
    # Check if weekend
    if dt.weekday() >= 5:
        return False
    
    # Check if holiday (only 2023 holidays implemented)
    if date_str in US_MARKET_HOLIDAYS_2023:
        return False
    
    return True
