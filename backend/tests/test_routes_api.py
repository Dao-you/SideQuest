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
        assert data["shade_time_period"] == "morning"


@pytest.mark.asyncio
async def test_compute_routes_supports_three_deterministic_shade_scenarios():
    """Acceptance-demo periods must visibly change shade and exposure metrics."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        base_payload = {
            "origin_lat": 25.0441,
            "origin_lng": 121.5294,
            "destination_lat": 25.0528,
            "destination_lng": 121.6067,
            "destination_name": "POPOP Taipei 瓶蓋工廠",
            "travel_mode": "TRANSIT",
            "prioritize_shade": True,
        }

        results = {}
        for period in ("morning", "noon", "evening"):
            response = await client.post(
                "/api/v1/routes/compute",
                json={**base_payload, "shade_time_period": period},
            )
            assert response.status_code == 200
            results[period] = response.json()

        assert results["noon"]["underground_or_shaded_percentage"] < results["morning"]["underground_or_shaded_percentage"]
        assert results["morning"]["underground_or_shaded_percentage"] < results["evening"]["underground_or_shaded_percentage"]
        assert results["noon"]["sun_exposure_minutes"] > results["morning"]["sun_exposure_minutes"]
        assert [results[period]["underground_or_shaded_percentage"] for period in ("morning", "noon", "evening")] == [55, 38, 65]
        assert results["noon"]["segments"][0]["is_shaded_or_underground"] is False
        assert "地下" not in results["noon"]["segments"][0]["instruction"]
        assert "驗收情境" in results["evening"]["route_advice"]


@pytest.mark.asyncio
async def test_openapi_documents_shade_time_period():
    """Swagger schema should expose the three accepted demo period values."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/openapi.json")
        assert response.status_code == 200
        schema = response.json()["components"]["schemas"]
        assert schema["ShadeTimePeriod"]["enum"] == ["morning", "noon", "evening"]
        assert "shade_time_period" in schema["RouteComputeRequest"]["properties"]


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
