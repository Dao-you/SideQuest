"""Tests for Interface-based Architecture, Service Abstractions, and Resilient Mock Fallback."""

import pytest
from app.models.event import EventFilter
from app.services import (
    CrowdService,
    CrowdServiceInterface,
    EventService,
    EventServiceInterface,
    FeedbackService,
    FeedbackServiceInterface,
    PlacesService,
    PlacesServiceInterface,
    PromptMetadataService,
    PromptMetadataServiceInterface,
    UserService,
    UserServiceInterface,
    WeatherService,
    WeatherServiceInterface,
    get_crowd_service,
    get_event_service,
    get_feedback_service,
    get_places_service,
    get_prompt_metadata_service,
    get_user_service,
    get_weather_service,
)
from app.models.agent import FeedbackRequest


def test_service_interface_inheritance():
    """Verify that all concrete services properly implement their abstract interfaces."""
    assert issubclass(EventService, EventServiceInterface)
    assert issubclass(CrowdService, CrowdServiceInterface)
    assert issubclass(WeatherService, WeatherServiceInterface)
    assert issubclass(PlacesService, PlacesServiceInterface)
    assert issubclass(UserService, UserServiceInterface)
    assert issubclass(PromptMetadataService, PromptMetadataServiceInterface)
    assert issubclass(FeedbackService, FeedbackServiceInterface)


@pytest.mark.asyncio
async def test_event_service_fallback():
    """Verify EventService falls back to MockDataSeeder when real database is empty or unavailable."""
    event_service = get_event_service()
    events = await event_service.get_events(EventFilter(limit=10))
    assert len(events) > 0

    # Test single event retrieval
    first_id = events[0].id
    event = await event_service.get_event_by_id(first_id)
    assert event is not None
    assert event.id == first_id

    # Test categories
    categories = await event_service.get_categories()
    assert len(categories) > 0
    assert "art" in categories


@pytest.mark.asyncio
async def test_crowd_service_fallback():
    """Verify CrowdService returns real or mock fallback heatmap points and venues."""
    crowd_service = get_crowd_service()
    heatmap = await crowd_service.get_heatmap_points()
    assert len(heatmap) > 0
    assert heatmap[0].weight >= 0.0

    venues = await crowd_service.get_all_venues()
    assert len(venues) > 0
    venue_id = venues[0].venue_id
    single_venue = await crowd_service.get_venue_by_id(venue_id)
    assert single_venue is not None
    assert single_venue.venue_id == venue_id


@pytest.mark.asyncio
async def test_weather_and_places_service_fallback():
    """Verify WeatherService and PlacesService return reliable responses even without external API credentials."""
    weather_service = get_weather_service()
    weather = await weather_service.get_microclimate(25.0330, 121.5654)
    assert weather.temperature_c > 0
    assert weather.apparent_temperature_c > 0

    solar = await weather_service.get_solar_exposure(25.0330, 121.5654)
    assert solar.shade_coverage_percentage >= 0

    places_service = get_places_service()
    place = await places_service.get_place_details("華山1914文創園區")
    assert place.name is not None
    assert place.rating >= 4.0

    route = await places_service.compute_route(
        origin_lat=25.0330,
        origin_lng=121.5654,
        dest_lat=25.0441,
        dest_lng=121.5294,
        dest_name="華山1914",
    )
    assert route.total_duration_minutes > 0
    assert route.comfort_score > 0


@pytest.mark.asyncio
async def test_prompt_and_feedback_services():
    """Verify PromptMetadataService and FeedbackService dynamically provide data without hardcoding in routes."""
    prompt_service = get_prompt_metadata_service()
    quick_data = prompt_service.get_quick_prompts()
    assert len(quick_data.example_prompts) >= 4
    assert len(quick_data.quick_tags) >= 5

    feedback_service = get_feedback_service()
    fb_res = await feedback_service.submit_feedback(
        FeedbackRequest(
            session_id="test_sess_001",
            event_id="evt_popop_craft_workshop",
            is_helpful=True,
            feedback_tag="accurate",
            comment="介面非常直覺！",
        )
    )
    assert fb_res.status == "success"
