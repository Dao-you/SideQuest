"""Tests for natural-language date planning and availability filtering."""

from datetime import datetime

import pytest

from app.agent.date_parser import TAIPEI_TZ, parse_natural_date_time
from app.models.event import EventFilter
from app.services.event_matching import event_overlaps_window
from app.services.event_service import get_event_service


def test_parse_explicit_date_and_time_window():
    parsed = parse_natural_date_time(
        "2026年8月22日下午2點到5點想和另一半約會",
        datetime(2026, 8, 17, 9, 0, tzinfo=TAIPEI_TZ),
    )

    assert parsed is not None
    assert parsed.start_date.isoformat() == "2026-08-22"
    assert parsed.start_time.strftime("%H:%M") == "14:00"
    assert parsed.end_time.strftime("%H:%M") == "17:00"


def test_parse_relative_weekday_in_taipei_time():
    parsed = parse_natural_date_time(
        "下週六晚上約會",
        datetime(2026, 8, 17, 9, 0, tzinfo=TAIPEI_TZ),
    )

    assert parsed is not None
    assert parsed.start_date.isoformat() == "2026-08-22"
    assert parsed.start_time.strftime("%H:%M") == "18:00"


@pytest.mark.asyncio
async def test_event_service_filters_events_by_requested_date():
    events = await get_event_service().get_events(
        EventFilter(start_date="2026-08-22", end_date="2026-08-22", limit=100)
    )

    assert events
    requested_date = datetime(2026, 8, 22, tzinfo=TAIPEI_TZ).date()
    assert all(
        event_overlaps_window(
            event.start_time,
            event.end_time,
            requested_date,
            requested_date,
        )
        for event in events
    )
