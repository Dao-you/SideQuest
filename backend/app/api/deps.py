"""FastAPI Dependencies for Dependency Injection."""

from app.agent.gemini_agent import GeminiAgent, get_gemini_agent
from app.services.firestore_service import FirestoreService, get_firestore_service
from app.services.maps_service import MapsService, get_maps_service


def get_agent_dep() -> GeminiAgent:
    """Dependency provider for GeminiAgent."""
    return get_gemini_agent()


def get_firestore_dep() -> FirestoreService:
    """Dependency provider for FirestoreService."""
    return get_firestore_service()


def get_maps_dep() -> MapsService:
    """Dependency provider for MapsService."""
    return get_maps_service()
