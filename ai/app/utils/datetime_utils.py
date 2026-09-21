from datetime import datetime, timezone
from typing import Any, Union
import logging

logger = logging.getLogger(__name__)

def ensure_utc_datetime(dt: Any) -> Union[datetime, None]:
    """
    Ensure datetime is timezone-aware and in UTC.
    Returns None if input is None, otherwise returns UTC timezone-aware datetime.
    """
    if dt is None:
        return None
    
    if not isinstance(dt, datetime):
        logger.warning(f"Expected datetime, got {type(dt)}: {dt}")
        return None
    
    # If no timezone info, assume UTC
    if dt.tzinfo is None:
        utc_dt = dt.replace(tzinfo=timezone.utc)
        logger.debug(f"Added UTC timezone to naive datetime: {dt} -> {utc_dt}")
        return utc_dt
    
    # If already UTC, return as is
    if dt.tzinfo == timezone.utc:
        return dt
    
    # Convert to UTC if different timezone
    utc_dt = dt.astimezone(timezone.utc)
    logger.debug(f"Converted to UTC: {dt} -> {utc_dt}")
    return utc_dt

def format_utc_datetime(dt: Any) -> Union[str, None]:
    """
    Format datetime to ISO format with 'Z' suffix to indicate UTC timezone.
    Returns None if input is None, otherwise returns ISO string with 'Z' suffix.
    """
    if dt is None:
        return None
    
    utc_dt = ensure_utc_datetime(dt)
    if utc_dt is None:
        return None
    
    # Format as ISO string and replace +00:00 with Z
    iso_str = utc_dt.isoformat()
    if iso_str.endswith('+00:00'):
        iso_str = iso_str.replace('+00:00', 'Z')
    
    return iso_str

def parse_and_normalize_datetime(date_str: str, source: str = "unknown") -> Union[datetime, None]:
    """
    Parse date string and normalize to UTC timezone-aware datetime.
    Handles various date formats including those with and without timezone indicators.
    """
    if not date_str:
        logger.warning(f"No date string provided from {source}")
        return None
    
    try:
        logger.debug(f"Parsing date string from {source}: {date_str}")
        
        # Handle different date formats and timezone indicators
        if date_str.endswith('Z'):
            # UTC time - convert to timezone-aware datetime
            dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            logger.debug(f"Parsed UTC date: {dt} (timezone: {dt.tzinfo})")
        elif '+' in date_str:
            # Already timezone-aware
            dt = datetime.fromisoformat(date_str)
            logger.debug(f"Parsed timezone-aware date: {dt} (timezone: {dt.tzinfo})")
        else:
            # No timezone info - assume UTC and make it timezone-aware
            dt = datetime.fromisoformat(date_str)
            dt = dt.replace(tzinfo=timezone.utc)
            logger.debug(f"Parsed date without timezone, assumed UTC: {dt} (timezone: {dt.tzinfo})")
        
        # Ensure the datetime is timezone-aware
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
            logger.debug(f"Made timezone-aware (UTC): {dt}")
        
        # Normalize to UTC
        utc_dt = ensure_utc_datetime(dt)
        logger.debug(f"Final normalized datetime: {utc_dt} (timezone: {utc_dt.tzinfo})")
        return utc_dt
        
    except ValueError as e:
        logger.error(f"Error parsing date string '{date_str}' from {source}: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error parsing date string '{date_str}' from {source}: {str(e)}")
        return None
