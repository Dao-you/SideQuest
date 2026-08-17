"""Services module containing Abstract Interfaces and resilient implementations."""

from app.services.interfaces import (
    CrowdServiceInterface,
    EventServiceInterface,
    FeedbackServiceInterface,
    PlacesServiceInterface,
    PromptMetadataServiceInterface,
    UserServiceInterface,
    WeatherServiceInterface,
)
from app.services.firestore_service import FirestoreService, get_firestore_service
from app.services.maps_service import MapsService, get_maps_service
from app.services.event_service import EventService, get_event_service
from app.services.crowd_service import CrowdService, get_crowd_service
from app.services.weather_service import WeatherService, get_weather_service
from app.services.places_service import PlacesService, get_places_service
from app.services.user_service import UserService, get_user_service
from app.services.prompt_service import PromptMetadataService, get_prompt_metadata_service
from app.services.feedback_service import FeedbackService, get_feedback_service
from app.services.mock_data_seeder import MockDataSeeder

__all__ = [
    # Interfaces
    "EventServiceInterface",
    "CrowdServiceInterface",
    "WeatherServiceInterface",
    "PlacesServiceInterface",
    "UserServiceInterface",
    "PromptMetadataServiceInterface",
    "FeedbackServiceInterface",
    # Service Implementations & Providers
    "FirestoreService",
    "get_firestore_service",
    "MapsService",
    "get_maps_service",
    "EventService",
    "get_event_service",
    "CrowdService",
    "get_crowd_service",
    "WeatherService",
    "get_weather_service",
    "PlacesService",
    "get_places_service",
    "UserService",
    "get_user_service",
    "PromptMetadataService",
    "get_prompt_metadata_service",
    "FeedbackService",
    "get_feedback_service",
    "MockDataSeeder",
]
