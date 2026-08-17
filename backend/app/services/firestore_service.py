"""Firestore Service with Graceful Degradation and In-Memory Fallback."""

import os
from typing import Dict, List, Optional
from app.config import settings
from app.logging_config import logger
from app.models.crowd import HeatmapPoint, VenueLiveStatus
from app.models.event import Event, EventFilter
from app.services.mock_data_seeder import MockDataSeeder


class FirestoreService:
    """Manages Firestore connections and provides in-memory fallback for offline/demo reliability."""

    def __init__(self) -> None:
        self._firestore_client = None
        self._is_firestore_connected = False
        
        # In-memory storage caches
        self._events_cache: Dict[str, Event] = {}
        self._venues_cache: Dict[str, VenueLiveStatus] = {}

    async def initialize(self) -> None:
        """Initialize connection to Firestore or load in-memory datasets."""
        # Always preload seed data into memory cache
        for venue in MockDataSeeder.get_seed_venues():
            self._venues_cache[venue.venue_id] = venue
        for event in MockDataSeeder.get_seed_events():
            self._events_cache[event.id] = event

        logger.info(f"Loaded {len(self._events_cache)} events and {len(self._venues_cache)} venues into memory cache.")

        # Try connecting to real GCP Firestore if configured
        if settings.GCP_PROJECT_ID or os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
            try:
                from google.cloud import firestore
                self._firestore_client = firestore.AsyncClient(
                    project=settings.GCP_PROJECT_ID or None,
                    database=settings.FIRESTORE_DATABASE,
                )
                self._is_firestore_connected = True
                logger.info("Successfully connected to Google Cloud Firestore.")
            except Exception as e:
                self._is_firestore_connected = False
                logger.warning(f"Firestore connection failed, using high-fidelity in-memory storage. Error: {e}")
        else:
            logger.info("No GCP_PROJECT_ID configured. Running in High-Fidelity Standalone In-Memory Mode.")

    async def is_healthy(self) -> bool:
        """Check if storage service is operational."""
        return len(self._events_cache) > 0

    @property
    def is_connected_to_gcp(self) -> bool:
        """Returns True if live Firestore is connected."""
        return self._is_firestore_connected

    async def get_events(self, filter_params: Optional[EventFilter] = None) -> List[Event]:
        """Query and filter events."""
        events = list(self._events_cache.values())

        if not filter_params:
            return events

        filtered = []
        for evt in events:
            # Filter category
            if filter_params.category and filter_params.category.lower() not in evt.category.value.lower():
                continue
            
            # Filter indoor
            if filter_params.is_indoor is not None and evt.is_indoor != filter_params.is_indoor:
                continue

            # Filter AC
            if filter_params.ac_available is not None and evt.ac_available != filter_params.ac_available:
                continue

            # Filter district
            if filter_params.district and filter_params.district not in evt.location.district and filter_params.district not in evt.location.address:
                continue

            # Filter keyword search (title, tags, description, venue_name)
            if filter_params.keyword:
                kw = filter_params.keyword.lower()
                matches_kw = (
                    kw in evt.title.lower()
                    or kw in evt.description.lower()
                    or kw in evt.venue_name.lower()
                    or any(kw in tag.lower() for tag in evt.tags)
                )
                if not matches_kw:
                    continue

            # Filter rating
            if filter_params.min_rating is not None and evt.rating < filter_params.min_rating:
                continue

            # Filter max crowd (check venue crowd score)
            if filter_params.max_crowd is not None:
                venue = self._venues_cache.get(evt.venue_id)
                if venue and venue.crowd_score > filter_params.max_crowd:
                    continue

            filtered.append(evt)

        # Pagination
        start = filter_params.offset
        end = start + filter_params.limit
        return filtered[start:end]

    async def get_event_by_id(self, event_id: str) -> Optional[Event]:
        """Fetch single event by ID."""
        return self._events_cache.get(event_id)

    async def get_all_venues(self) -> List[VenueLiveStatus]:
        """Fetch all venue real-time statuses."""
        return list(self._venues_cache.values())

    async def get_venue_by_id(self, venue_id: str) -> Optional[VenueLiveStatus]:
        """Fetch venue real-time status by ID."""
        return self._venues_cache.get(venue_id)

    async def get_heatmap_points(self) -> List[HeatmapPoint]:
        """Generate normalized heatmap points for Google Maps JavaScript API."""
        points = []
        for venue in self._venues_cache.values():
            # Normalize weight between 0.1 and 1.0
            weight = max(0.1, round(venue.crowd_score / 100.0, 2))
            points.append(
                HeatmapPoint(
                    latitude=venue.location.latitude,
                    longitude=venue.location.longitude,
                    weight=weight,
                    venue_name=venue.venue_name,
                    crowd_score=venue.crowd_score,
                    crowd_level=venue.crowd_level,
                )
            )
        return points


_firestore_service_instance: Optional[FirestoreService] = None


def get_firestore_service() -> FirestoreService:
    """Singleton getter for FirestoreService."""
    global _firestore_service_instance
    if _firestore_service_instance is None:
        _firestore_service_instance = FirestoreService()
    return _firestore_service_instance
