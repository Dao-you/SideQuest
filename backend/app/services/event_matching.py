"""Shared event availability matching helpers."""

from datetime import date, datetime, time
from typing import Optional
from zoneinfo import ZoneInfo


TAIPEI_TZ = ZoneInfo("Asia/Taipei")


def parse_event_datetime(value: str, *, end_of_day: bool = False) -> datetime:
    """Parse an event ISO timestamp and normalize it to Taipei time."""
    normalized = value.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        fallback = time.max if end_of_day else time.min
        return datetime.combine(date.today(), fallback, tzinfo=TAIPEI_TZ)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=TAIPEI_TZ)
    return parsed.astimezone(TAIPEI_TZ)


def event_overlaps_window(
    event_start: str,
    event_end: str,
    start_date: Optional[date],
    end_date: Optional[date],
    start_time: Optional[time] = None,
    end_time: Optional[time] = None,
) -> bool:
    """Return whether an event overlaps a requested local Taipei date/time window."""
    if start_date is None and end_date is None:
        return True
    window_start_date = start_date or end_date
    window_end_date = end_date or start_date
    assert window_start_date is not None and window_end_date is not None
    window_start = datetime.combine(window_start_date, start_time or time.min, tzinfo=TAIPEI_TZ)
    window_end = datetime.combine(window_end_date, end_time or time.max, tzinfo=TAIPEI_TZ)
    return parse_event_datetime(event_end, end_of_day=True) >= window_start and parse_event_datetime(event_start) <= window_end
