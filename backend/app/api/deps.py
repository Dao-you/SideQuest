"""FastAPI Dependencies for Interface-Based Dependency Injection."""

from app.agent.gemini_agent import GeminiAgent, get_gemini_agent
from app.services import (
    CrowdServiceInterface,
    EventServiceInterface,
    FeedbackServiceInterface,
    FirestoreService,
    MapsService,
    PlacesServiceInterface,
    PromptMetadataServiceInterface,
    UserServiceInterface,
    WeatherServiceInterface,
    get_crowd_service,
    get_event_service,
    get_feedback_service,
    get_firestore_service,
    get_maps_service,
    get_places_service,
    get_prompt_metadata_service,
    get_user_service,
    get_weather_service,
)


def get_agent_dep() -> GeminiAgent:
    """Dependency provider for GeminiAgent."""
    return get_gemini_agent()


def get_event_service_dep() -> EventServiceInterface:
    """Dependency provider for EventServiceInterface."""
    return get_event_service()


def get_crowd_service_dep() -> CrowdServiceInterface:
    """Dependency provider for CrowdServiceInterface."""
    return get_crowd_service()


def get_weather_service_dep() -> WeatherServiceInterface:
    """Dependency provider for WeatherServiceInterface."""
    return get_weather_service()


def get_places_service_dep() -> PlacesServiceInterface:
    """Dependency provider for PlacesServiceInterface."""
    return get_places_service()


def get_user_service_dep() -> UserServiceInterface:
    """Dependency provider for UserServiceInterface."""
    return get_user_service()


def get_prompt_metadata_dep() -> PromptMetadataServiceInterface:
    """Dependency provider for PromptMetadataServiceInterface."""
    return get_prompt_metadata_service()


def get_feedback_service_dep() -> FeedbackServiceInterface:
    """Dependency provider for FeedbackServiceInterface."""
    return get_feedback_service()


def get_firestore_dep() -> FirestoreService:
    """Dependency provider for raw FirestoreService."""
    return get_firestore_service()


def get_maps_dep() -> MapsService:
    """Dependency provider for raw MapsService."""
    return get_maps_service()
