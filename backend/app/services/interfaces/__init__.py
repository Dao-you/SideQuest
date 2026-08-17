"""Abstract Interfaces for all SideQuest Data and Agent Services."""

from abc import ABC, abstractmethod
from typing import Any, List, Optional
from app.models.agent import FeedbackRequest, FeedbackResponse, QuickPromptsResponse
from app.models.crowd import HeatmapPoint, VenueLiveStatus
from app.models.event import Event, EventFilter
from app.models.places import PlaceDetails, RouteComfort
from app.models.user import FavoriteToggleResponse, UpdatePreferencesRequest, UserProfile
from app.models.weather import MicroclimateResponse, SolarExposureResponse


class EventServiceInterface(ABC):
    """Interface for Event Catalog and Discovery operations."""

    @abstractmethod
    async def get_events(self, filter_params: Optional[EventFilter] = None) -> List[Event]:
        """Fetch filtered list of city and community events."""
        pass

    @abstractmethod
    async def get_event_by_id(self, event_id: str) -> Optional[Event]:
        """Fetch single event by ID."""
        pass

    @abstractmethod
    async def get_categories(self) -> List[str]:
        """Fetch list of supported event categories."""
        pass


class CrowdServiceInterface(ABC):
    """Interface for Crowd Sensing, Live Congestion, and Heatmaps."""

    @abstractmethod
    async def get_heatmap_points(self) -> List[HeatmapPoint]:
        """Fetch normalized heatmap coordinates for map rendering."""
        pass

    @abstractmethod
    async def get_all_venues(self) -> List[VenueLiveStatus]:
        """Fetch live status of all monitored city venues."""
        pass

    @abstractmethod
    async def get_venue_by_id(self, venue_id: str) -> Optional[VenueLiveStatus]:
        """Fetch live status of a single venue."""
        pass


class WeatherServiceInterface(ABC):
    """Interface for Microclimate, Temperature, UV, and Solar Exposure."""

    @abstractmethod
    async def get_microclimate(self, latitude: float, longitude: float) -> MicroclimateResponse:
        """Fetch temperature, apparent temp, humidity, UV index, and rain forecast."""
        pass

    @abstractmethod
    async def get_solar_exposure(self, latitude: float, longitude: float) -> SolarExposureResponse:
        """Fetch solar irradiance and shaded comfort assessment."""
        pass


class PlacesServiceInterface(ABC):
    """Interface for Google Places details, accessibility, and Shaded Routing."""

    @abstractmethod
    async def get_place_details(
        self,
        place_name: str,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
    ) -> PlaceDetails:
        """Fetch place rating, opening hours, address, and accessibility."""
        pass

    @abstractmethod
    async def compute_route(
        self,
        origin_lat: float,
        origin_lng: float,
        dest_lat: float,
        dest_lng: float,
        dest_name: str = "目的地",
        prioritize_shade: bool = True,
        preference: str = "fastest",
        wheelchair_accessible: bool = False,
        departure_time: Optional[str] = None,
    ) -> RouteComfort:
        """Compute transit and shaded pedestrian route with comfort rating and routing preferences."""
        pass


class UserServiceInterface(ABC):
    """Interface for User Profile, Persona Demo Login, and Bookmarks."""

    @abstractmethod
    def list_personas(self) -> List[UserProfile]:
        """List preset test accounts for Demo Login."""
        pass

    @abstractmethod
    def mock_login(self, account_id: Optional[str] = None, custom_name: Optional[str] = None) -> UserProfile:
        """Authenticate as preset persona or guest."""
        pass

    @abstractmethod
    def get_profile(self, user_id: str) -> UserProfile:
        """Retrieve user profile, preferences, and favorited event IDs."""
        pass

    @abstractmethod
    def get_user_profile(self, user_id: str) -> UserProfile:
        """Alias for get_profile."""
        pass

    @abstractmethod
    async def toggle_favorite(self, user_id: str, event_id: str) -> FavoriteToggleResponse:
        """Bookmark or unbookmark an event."""
        pass

    @abstractmethod
    async def get_favorites(self, user_id: str) -> List[Event]:
        """Retrieve full event objects favorited by user."""
        pass

    @abstractmethod
    def update_preferences(self, user_id: str, req: UpdatePreferencesRequest) -> UserProfile:
        """Update user categories, tags, budget, and indoor/crowd preferences."""
        pass


class PromptMetadataServiceInterface(ABC):
    """Interface for Homepage Example Prompts and Quick Filter Chips."""

    @abstractmethod
    def get_quick_prompts(self) -> QuickPromptsResponse:
        """Retrieve curated prompt examples and quick filter tags."""
        pass


class FeedbackServiceInterface(ABC):
    """Interface for User Recommendation Quality Feedback."""

    @abstractmethod
    async def submit_feedback(self, req: FeedbackRequest) -> FeedbackResponse:
        """Record user feedback rating and comments."""
        pass
