"""Unit and integration tests for Google Routes endpoint and visualizer."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_compute_routes_endpoint():
    """Test POST /api/v1/routes/compute."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "origin_lat": 25.0441,
            "origin_lng": 121.5294,
            "destination_lat": 25.0528,
            "destination_lng": 121.6067,
            "destination_name": "POPOP Taipei 瓶蓋工廠",
            "travel_mode": "TRANSIT",
            "prioritize_shade": True,
        }
        res = await client.post("/api/v1/routes/compute", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert "total_duration_minutes" in data
        assert "comfort_score" in data
        assert "transit_summary" in data
        assert "underground_or_shaded_percentage" in data
        assert data["total_duration_minutes"] > 0
        assert data["comfort_score"] >= 0


@pytest.mark.asyncio
async def test_routes_visualizer_html_endpoint():
    """Test GET /api/v1/routes/visualize returns HTML."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/v1/routes/visualize")
        assert res.status_code == 200
        assert "SideQuest" in res.text
        assert "Google Routes" in res.text
        assert "leaflet" in res.text


@pytest.mark.asyncio
@pytest.mark.parametrize("preference", [
    "fastest",
    "wheelchair",
    "more_bus",
    "more_subway",
    "less_walking",
    "more_shading",
    "less_crowded",
    "mixed",
])
async def test_compute_routes_with_preferences(preference: str):
    """Test POST /api/v1/routes/compute across all route preferences."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "origin_lat": 25.0441,
            "origin_lng": 121.5294,
            "destination_lat": 25.0528,
            "destination_lng": 121.6067,
            "destination_name": "POPOP Taipei 瓶蓋工廠",
            "travel_mode": "TRANSIT",
            "preference": preference,
            "wheelchair_accessible": (preference == "wheelchair"),
            "departure_time": "now",
        }
        res = await client.post("/api/v1/routes/compute", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data["preference"] == preference
        assert "multimodal" in data and data["multimodal"] is not None
        assert data["multimodal"]["walk_calories"] > 0
        assert data["multimodal"]["bike_calories"] > 0
        assert data["multimodal"]["taxi_cost_twd"] > 0
        assert len(data["segments"]) > 0
        if preference == "wheelchair":
            assert "無障礙" in data["transit_summary"] or "無障礙" in (data.get("accessibility_note") or "")

