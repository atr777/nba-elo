"""
Date and time utilities for the NBA ELO Intelligence Engine.
Handles date parsing, formatting, and range generation.
"""

from datetime import datetime, timedelta
from typing import List
import pytz


def parse_date(date_string: str, format: str = "%Y%m%d") -> datetime:
    """Parse date string into datetime object."""
    return datetime.strptime(date_string, format)


def format_date(date: datetime, format: str = "%Y%m%d") -> str:
    """Format datetime object to string."""
    return date.strftime(format)


def generate_date_range(start_date: str, end_date: str, format: str = "%Y%m%d") -> List[str]:
    """
    Generate list of date strings between start and end dates (inclusive).
    
    Args:
        start_date: Start date string (e.g., "20231001")
        end_date: End date string (e.g., "20240430")
        format: Date format string
        
    Returns:
        List of date strings in specified format
    """
    start = parse_date(start_date, format)
    end = parse_date(end_date, format)
    
    dates = []
    current = start
    while current <= end:
        dates.append(format_date(current, format))
        current += timedelta(days=1)
    
    return dates


def get_days_between(date1: str, date2: str, format: str = "%Y%m%d") -> int:
    """Calculate number of days between two dates."""
    d1 = parse_date(date1, format)
    d2 = parse_date(date2, format)
    return abs((d2 - d1).days)


def is_valid_date(date_string: str, format: str = "%Y%m%d") -> bool:
    """Check if date string is valid."""
    try:
        parse_date(date_string, format)
        return True
    except ValueError:
        return False


def get_current_nba_season() -> tuple:
    """
    Determine current NBA season start and end dates.
    NBA season typically runs October - April.
    
    Returns:
        Tuple of (season_start, season_end) as strings
    """
    now = datetime.now()
    year = now.year
    
    # If we're before October, use previous year's season
    if now.month < 10:
        season_start = f"{year-1}1001"
        season_end = f"{year}0430"
    else:
        season_start = f"{year}1001"
        season_end = f"{year+1}0430"
    
    return season_start, season_end


def convert_date_format(date_string: str, from_format: str, to_format: str) -> str:
    """Convert date string from one format to another."""
    date = parse_date(date_string, from_format)
    return format_date(date, to_format)
