"""Integration Tests for FastAPI Endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_root_and_healthz(async_client: AsyncClient):
    """Test root and liveness health check."""
    res = await async_client.get("/")
    assert res.status_code == 200
    data = res.json()
    assert data["project"] == "SideQuest"

    res_h = await async_client.get("/healthz")
    assert res_h.status_code == 200
    assert res_h.json()["status"] == "ok"

    res_r = await async_client.get("/readiness")
    assert res_r.status_code == 200
    assert res_r.json()["database_ready"] is True


@pytest.mark.asyncio
async def test_events_endpoints(async_client: AsyncClient):
    """Test events querying, filtering, and detail endpoints."""
    # List all
    res = await async_client.get("/api/v1/events?limit=5")
    assert res.status_code == 200
    events = res.json()
    assert len(events) <= 5
    assert len(events) > 0

    # Categories
    res_cat = await async_client.get("/api/v1/events/categories")
    assert res_cat.status_code == 200
    assert "art" in res_cat.json()

    # Detail
    event_id = events[0]["id"]
    res_detail = await async_client.get(f"/api/v1/events/{event_id}")
    assert res_detail.status_code == 200
    assert res_detail.json()["id"] == event_id


@pytest.mark.asyncio
async def test_crowd_and_heatmap_endpoints(async_client: AsyncClient):
    """Test crowd heatmap and venues live status endpoints."""
    # Heatmap
    res_heat = await async_client.get("/api/v1/crowd/heatmap")
    assert res_heat.status_code == 200
    points = res_heat.json()
    assert len(points) > 0
    assert "weight" in points[0]
    assert 0.0 <= points[0]["weight"] <= 1.0

    # Venues
    res_venues = await async_client.get("/api/v1/crowd/venues")
    assert res_venues.status_code == 200
    assert len(res_venues.json()) > 0


@pytest.mark.asyncio
async def test_weather_endpoints(async_client: AsyncClient):
    """Test weather and solar endpoints."""
    res_w = await async_client.get("/api/v1/weather/current?lat=25.0330&lng=121.5654")
    assert res_w.status_code == 200
    assert "temperature_c" in res_w.json()
    assert "uv_index" in res_w.json()

    res_s = await async_client.get("/api/v1/weather/solar?lat=25.0330&lng=121.5654")
    assert res_s.status_code == 200
    assert "solar_radiation_w_m2" in res_s.json()


@pytest.mark.asyncio
async def test_agent_endpoints(async_client: AsyncClient):
    """Test agent chat and recommend API routes."""
    # POST /api/v1/agent/chat
    payload = {
        "message": "想看展覽喝咖啡，不想人擠人",
        "user_latitude": 25.0330,
        "user_longitude": 121.5654,
    }
    res_chat = await async_client.post("/api/v1/agent/chat", json=payload)
    assert res_chat.status_code == 200
    data = res_chat.json()
    assert "reply" in data
    assert len(data["recommendations"]) > 0

    # POST /api/v1/agent/recommend
    rec_payload = {
        "user_latitude": 25.0330,
        "user_longitude": 121.5654,
        "interests": ["art", "craft"],
        "avoid_crowd": True,
        "limit": 3,
    }
    res_rec = await async_client.post("/api/v1/agent/recommend", json=rec_payload)
    assert res_rec.status_code == 200
    rec_data = res_rec.json()
    assert len(rec_data["recommendations"]) == 3


@pytest.mark.asyncio
async def test_agent_chat_stream(async_client: AsyncClient):
    """Test SSE streaming endpoint."""
    payload = {
        "message": "信義區好熱，推薦室內活動",
        "user_latitude": 25.0330,
        "user_longitude": 121.5654,
    }
    res_stream = await async_client.post("/api/v1/agent/chat/stream", json=payload)
    assert res_stream.status_code == 200
    assert "text/event-stream" in res_stream.headers.get("content-type", "")
