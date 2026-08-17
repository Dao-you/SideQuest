"""Event Discovery and Catalog Service with Interface and Mock Fallback."""

from typing import List, Optional
from app.logging_config import logger
from app.models.event import Event, EventCategory, EventFilter
from app.services.firestore_service import FirestoreService, get_firestore_service
from app.services.interfaces import EventServiceInterface
from app.services.mock_data_seeder import MockDataSeeder


class EventService(EventServiceInterface):
    """Event catalog service that tries GCP Firestore / Real API first, with graceful mock fallback."""

    def __init__(self, db: Optional[FirestoreService] = None) -> None:
        self.db = db or get_firestore_service()

    async def get_events(self, filter_params: Optional[EventFilter] = None) -> List[Event]:
        """Fetch events with filtering and graceful fallback."""
        try:
            # Attempt to fetch from real Firestore database
            events = await self.db.get_events(filter_params)
            if events:
                return events
        except Exception as e:
            logger.warning(f"Error querying events from database: {e}. Falling back to mock dataset.")

        # Fallback to Mock Data Seeder
        all_seed = MockDataSeeder.get_seed_events()
        if not filter_params:
            return all_seed

        # Apply in-memory filtering on mock data
        filtered = all_seed
        if filter_params.category:
            filtered = [e for e in filtered if e.category.value.lower() == filter_params.category.lower()]
        if filter_params.district:
            filtered = [e for e in filtered if e.location.district == filter_params.district]
        if filter_params.is_indoor is not None:
            filtered = [e for e in filtered if e.is_indoor == filter_params.is_indoor]
        if filter_params.ac_available is not None:
            filtered = [e for e in filtered if e.ac_available == filter_params.ac_available]
        if filter_params.price_type:
            filtered = [e for e in filtered if e.price_type == filter_params.price_type]
        if filter_params.keyword:
            kw = filter_params.keyword.lower()
            filtered = [
                e for e in filtered
                if kw in e.title.lower() or kw in e.description.lower() or any(kw in t.lower() for t in e.tags)
            ]

        offset = filter_params.offset
        limit = filter_params.limit
        return filtered[offset : offset + limit]

    async def get_event_by_id(self, event_id: str) -> Optional[Event]:
        """Fetch single event by ID with fallback."""
        try:
            event = await self.db.get_event_by_id(event_id)
            if event:
                return event
        except Exception as e:
            logger.warning(f"Error querying event {event_id} from database: {e}. Falling back to mock.")

        # Fallback to Mock Data
        seed_events = MockDataSeeder.get_seed_events()
        for e in seed_events:
            if e.id == event_id:
                return e
        return None

    async def get_categories(self) -> List[str]:
        """Return list of supported event categories."""
        return [c.value for c in EventCategory]


_event_service_instance: Optional[EventService] = None


def get_event_service() -> EventService:
    """Singleton getter for EventService."""
    global _event_service_instance
    if _event_service_instance is None:
        _event_service_instance = EventService()
    return _event_service_instance
