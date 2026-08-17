"""Unit tests for Google Calendar integration, schedule conflict detection, and user preferences (Step 11 & Step 17)."""

import pytest
from app.models.user import (
    CalendarConflictCheckRequest,
    CalendarSyncRequest,
    UpdatePreferencesRequest,
)
from app.services.user_service import UserService


@pytest.fixture
def user_service():
    """Returns a fresh UserService instance."""
    return UserService()


def test_list_personas_includes_calendar_events(user_service):
    """Verify that seeded personas contain Google Calendar events."""
    personas = user_service.list_personas()
    assert len(personas) >= 4
    sunny = next((p for p in personas if p.user_id == "demo_weekend_explorer"), None)
    assert sunny is not None
    assert sunny.google_account_connected is True
    assert len(sunny.calendar_events) > 0
    assert "Sprint" in sunny.calendar_events[0].title


def test_calendar_conflict_detection(user_service):
    """Verify that an overlapping event triggers a conflict response."""
    # Sunny has a Sprint meeting on 2026-08-22 from 14:00 to 16:30
    conflict_req = CalendarConflictCheckRequest(
        event_id="evt_test_conflict",
        event_title="當代文化實驗場展覽",
        start_time="2026-08-22T14:30:00+08:00",
        end_time="2026-08-22T17:00:00+08:00",
        location="臺灣當代文化實驗場",
    )
    res = user_service.check_calendar_conflict(user_id="demo_weekend_explorer", req=conflict_req)
    assert res.has_conflict is True
    assert len(res.conflicting_events) == 1
    assert "Sprint" in res.conflicting_events[0].title

    # Non-overlapping event (e.g. morning 09:00 - 11:00)
    no_conflict_req = CalendarConflictCheckRequest(
        event_id="evt_test_no_conflict",
        event_title="晨間植物園散步",
        start_time="2026-08-22T09:00:00+08:00",
        end_time="2026-08-22T11:00:00+08:00",
        location="台北植物園",
    )
    res_no = user_service.check_calendar_conflict(user_id="demo_weekend_explorer", req=no_conflict_req)
    assert res_no.has_conflict is False
    assert len(res_no.conflicting_events) == 0


def test_calendar_sync_overwrite(user_service):
    """Verify overwriting conflicting events."""
    sync_req = CalendarSyncRequest(
        event_id="evt_popop_craft_workshop",
        event_title="瓶蓋工廠手作職人工作坊",
        start_time="2026-08-22T14:00:00+08:00",
        end_time="2026-08-22T16:30:00+08:00",
        location="南港瓶蓋工廠",
        description="手作金工體驗",
        resolution_choice="overwrite",
    )
    res = user_service.sync_calendar_event(user_id="demo_weekend_explorer", req=sync_req)
    assert res.success is True
    assert res.action_taken == "overwritten"
    events = user_service.get_calendar_events("demo_weekend_explorer")
    # Sprint meeting should be removed and replaced by the new event
    assert any("瓶蓋工廠" in e.title for e in events)
    assert not any("Sprint 檢討會議" in e.title for e in events)


def test_calendar_sync_both(user_service):
    """Verify keeping both events in calendar."""
    sync_req = CalendarSyncRequest(
        event_id="evt_clab_future_media",
        event_title="C-LAB 未來媒體藝術展",
        start_time="2026-08-22T14:30:00+08:00",
        end_time="2026-08-22T16:00:00+08:00",
        location="臺灣當代文化實驗場",
        resolution_choice="both",
    )
    res = user_service.sync_calendar_event(user_id="demo_weekend_explorer", req=sync_req)
    assert res.success is True
    assert res.action_taken == "both_kept"
    events = user_service.get_calendar_events("demo_weekend_explorer")
    assert any("C-LAB" in e.title for e in events)


def test_update_preferences_route_and_tags(user_service):
    """Verify updating user route preference, budget, and tags."""
    update_req = UpdatePreferencesRequest(
        favorite_tags=["AI", "當代藝術", "捷運直達"],
        prefer_indoor=True,
        avoid_crowd=True,
        max_budget=1200,
        route_preference="fastest",
    )
    profile = user_service.update_preferences(user_id="demo_weekend_explorer", req=update_req)
    assert profile.max_budget == 1200
    assert profile.route_preference == "fastest"
    assert "捷運直達" in profile.favorite_tags
