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
