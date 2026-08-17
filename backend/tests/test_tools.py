"""Unit Tests for 6 Agent Tools."""

import pytest
from app.agent.tools import get_tool_registry


@pytest.mark.asyncio
async def test_tool_registry():
    """Verify tool registry contains all 6 required tools with valid Gemini declarations."""
    registry = get_tool_registry()
    tools = registry.list_tools()
    assert len(tools) == 6

    declarations = registry.get_gemini_declarations()
    assert len(declarations) == 6
    tool_names = {d["name"] for d in declarations}
    assert tool_names == {
        "search_events",
        "check_weather",
        "check_crowd_density",
        "get_place_details",
        "compute_route",
        "get_solar_exposure",
    }


@pytest.mark.asyncio
async def test_search_events_tool():
    """Test EventTool search functionality."""
    registry = get_tool_registry()
    tool = registry.get_tool("search_events")

    # Search all
    res = await tool.execute(limit=5)
    assert res["status"] == "success"
    assert res["total_found"] > 0
    assert len(res["events"]) <= 5

    # Search with keyword
    res_kw = await tool.execute(keyword="手作")
    assert res_kw["status"] == "success"
    assert any("手作" in e["title"] or "手作" in e["tags"] for e in res_kw["events"])


@pytest.mark.asyncio
async def test_check_weather_tool():
    """Test WeatherTool microclimate output."""
    registry = get_tool_registry()
    tool = registry.get_tool("check_weather")

    res = await tool.execute(latitude=25.0441, longitude=121.5294, district="中正區")
    assert res["status"] == "success"
    assert "temperature_c" in res
    assert "uv_index" in res
    assert res["uv_index"] >= 0
    assert isinstance(res["indoor_recommended"], bool)


@pytest.mark.asyncio
async def test_check_crowd_density_tool():
    """Test CrowdTool for congestion check and alternative recommendation."""
    registry = get_tool_registry()
    tool = registry.get_tool("check_crowd_density")

    # Test overloaded venue (Huashan)
    res_overload = await tool.execute(venue_id="venue_huashan")
    assert res_overload["status"] == "success"
    assert res_overload["crowd_score"] >= 80
    assert res_overload["is_overloaded"] is True
    assert res_overload["alternative_suggestion"] is not None
    assert "alternative_venue_name" in res_overload["alternative_suggestion"]

    # Test comfortable venue (Popop)
    res_popop = await tool.execute(venue_id="venue_popop")
    assert res_popop["status"] == "success"
    assert res_popop["crowd_score"] <= 35
    assert res_popop["is_overloaded"] is False

    # Test city summary
    res_summary = await tool.execute()
    assert res_summary["status"] == "success"
    assert "city_average_crowd_score" in res_summary


@pytest.mark.asyncio
async def test_get_place_details_tool():
    """Test PlacesTool details lookup."""
    registry = get_tool_registry()
    tool = registry.get_tool("get_place_details")

    res = await tool.execute(place_name="華山1914文創園區")
    assert res["status"] == "success"
    assert res["rating"] >= 4.0
    assert "address" in res


@pytest.mark.asyncio
async def test_compute_route_tool():
    """Test RoutesTool calculation and thermal comfort scoring."""
    registry = get_tool_registry()
    tool = registry.get_tool("compute_route")

    res = await tool.execute(
        origin_lat=25.0330,
        origin_lng=121.5654,
        destination_lat=25.0531,
        destination_lng=121.6062,
        destination_name="POPOP Taipei 瓶蓋工廠",
        prioritize_shade=True,
    )
    assert res["status"] == "success"
    assert res["total_duration_minutes"] > 0
    assert res["underground_or_shaded_percentage"] >= 50
    assert len(res["segments"]) > 0


@pytest.mark.asyncio
async def test_get_solar_exposure_tool():
    """Test SolarTool radiation and shade evaluation."""
    registry = get_tool_registry()
    tool = registry.get_tool("get_solar_exposure")

    res = await tool.execute(latitude=25.0441, longitude=121.5294)
    assert res["status"] == "success"
    assert res["solar_radiation_w_m2"] > 0
    assert "sunscreen_recommendation" in res
