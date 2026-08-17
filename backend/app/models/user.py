"""User and Mock Authentication Models for PRD MVP."""

from typing import List, Optional
from pydantic import BaseModel, Field


class GoogleCalendarEvent(BaseModel):
    """Google Calendar Event representation for schedule conflict detection."""
    event_id: str = Field(..., description="Unique Google Calendar event ID")
    title: str = Field(..., description="Event title / subject")
    start_time: str = Field(..., description="ISO start time string, e.g. 2026-08-22T14:00:00+08:00")
    end_time: str = Field(..., description="ISO end time string, e.g. 2026-08-22T16:30:00+08:00")
    location: Optional[str] = Field(default="", description="Event location")
    description: Optional[str] = Field(default="", description="Event notes or description")
    category: str = Field(default="personal", description="Event category: work, meeting, social, personal, sidequest")
    is_sidequest_event: bool = Field(default=False, description="Whether this event was synced from SideQuest")


class UserProfile(BaseModel):
    """User Profile for Mock Persona and Login."""
    user_id: str = Field(..., description="Unique user ID or session user ID")
    name: str = Field(..., description="User display name")
    email: str = Field(..., description="User email (simulated)")
    avatar_url: str = Field(default="", description="User avatar image URL")
    persona_title: str = Field(default="週末探索者", description="User persona description")
    favorite_categories: List[str] = Field(default_factory=list, description="Default interest categories")
    favorite_tags: List[str] = Field(default_factory=list, description="Preferred keyword tags")
    favorite_event_ids: List[str] = Field(default_factory=list, description="Bookmarked event IDs")
    prefer_indoor: bool = Field(default=True, description="Default indoor AC preference")
    avoid_crowd: bool = Field(default=True, description="Default crowd avoidance preference")
    max_budget: Optional[int] = Field(default=500, description="Default budget ceiling in TWD")
    route_preference: str = Field(default="shade_first", description="Preferred routing strategy: shade_first, fastest, accessible")
    google_account_connected: bool = Field(default=True, description="Whether Google Account and Calendar are linked")
    google_email: str = Field(default="kevin.sidequest@gmail.com", description="Linked Google account email")
    calendar_events: List[GoogleCalendarEvent] = Field(default_factory=list, description="Synced Google Calendar events")
    is_mock_account: bool = Field(default=True, description="Identifies mock MVP account")
    auth_provider: str = Field(default="mock", description="Authentication provider: 'google', 'mock', or 'guest'")
    google_sub: Optional[str] = Field(default=None, description="Google unique user subject identifier")


class GoogleAuthRequest(BaseModel):
    """Credential returned by the official Google Identity Services button."""
    credential: str = Field(..., min_length=1, description="Google Identity Services signed JWT ID token")


class GoogleAuthResponse(BaseModel):
    """Response after authenticating with Google."""
    success: bool = Field(..., description="Authentication status")
    user: UserProfile = Field(..., description="Authenticated user profile")
    message: str = Field(..., description="Status message")
    auth_method: str = Field(default="google_oauth2", description="Authentication method used")


class GoogleAuthConfigResponse(BaseModel):
    """Response containing Google OAuth Web Client configuration."""
    client_id: str = Field(..., description="Google OAuth 2.0 Web Client ID")
    enabled: bool = Field(..., description="Whether Google OAuth is enabled")


class MockLoginRequest(BaseModel):
    """Request to log in with a test account or guest mode."""
    account_id: Optional[str] = Field(
        default="demo_weekend_explorer",
        description="Preset account ID: 'demo_weekend_explorer', 'demo_tech_geek', 'demo_crowd_avoider', 'demo_family_parent' or custom ID",
    )
    custom_name: Optional[str] = Field(default=None, description="Custom display name for guest login")


class FavoriteToggleRequest(BaseModel):
    """Request to add or remove an event from favorites."""
    event_id: str = Field(..., description="Target event ID")


class FavoriteToggleResponse(BaseModel):
    """Response after toggling favorite status."""
    event_id: str
    is_favorited: bool
    total_favorites: int
    message: str


class UpdatePreferencesRequest(BaseModel):
    """Request to update user preferences."""
    favorite_categories: Optional[List[str]] = None
    favorite_tags: Optional[List[str]] = None
    prefer_indoor: Optional[bool] = None
    avoid_crowd: Optional[bool] = None
    max_budget: Optional[int] = None
    route_preference: Optional[str] = None
    google_account_connected: Optional[bool] = None
    google_email: Optional[str] = None


class CalendarConflictCheckRequest(BaseModel):
    """Request to verify schedule conflict against user's Google Calendar."""
    event_id: str = Field(..., description="Target SideQuest event or place ID")
    event_title: str = Field(..., description="Target event or place name")
    start_time: str = Field(..., description="ISO start time string (e.g. 2026-08-22T14:30:00+08:00)")
    end_time: str = Field(..., description="ISO end time string (e.g. 2026-08-22T17:00:00+08:00)")
    location: Optional[str] = Field(default="", description="Target location")


class CalendarConflictCheckResponse(BaseModel):
    """Response containing any detected Google Calendar schedule conflicts."""
    has_conflict: bool = Field(..., description="True if an existing event overlaps with target time")
    conflicting_events: List[GoogleCalendarEvent] = Field(default_factory=list, description="Overlapping events in Google Calendar")
    message: str = Field(..., description="User-facing summary message")
    suggested_action: str = Field(default="choose_resolution", description="Recommendation: none, choose_resolution, proceed")


class CalendarSyncRequest(BaseModel):
    """Request to add or overwrite an event in Google Calendar."""
    event_id: str = Field(..., description="Target SideQuest event or place ID")
    event_title: str = Field(..., description="Target event or place title")
    start_time: str = Field(..., description="ISO start time string")
    end_time: str = Field(..., description="ISO end time string")
    location: Optional[str] = Field(default="", description="Place address or venue name")
    description: Optional[str] = Field(default="", description="Event details, crowd level, tickets")
    resolution_choice: str = Field(
        default="overwrite",
        description="Resolution for conflicts: 'overwrite' (replaces conflicting event), 'both' (keeps both), 'cancel' (keeps original)"
    )


class CalendarSyncResponse(BaseModel):
    """Response after executing Google Calendar synchronization."""
    success: bool
    synced_event: Optional[GoogleCalendarEvent] = None
    action_taken: str
    message: str
    all_calendar_events: List[GoogleCalendarEvent] = Field(default_factory=list)

