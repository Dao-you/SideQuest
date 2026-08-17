"""Crowd Sensing, Heatmap, and Venue Congestion Service with Interface."""

from typing import List, Optional
from app.logging_config import logger
from app.models.crowd import HeatmapPoint, VenueLiveStatus
from app.services.firestore_service import FirestoreService, get_firestore_service
from app.services.interfaces import CrowdServiceInterface
from app.services.mock_data_seeder import MockDataSeeder


class CrowdService(CrowdServiceInterface):
    """Crowd service implementing CrowdServiceInterface with live Firestore queries and mock fallback."""

    def __init__(self, db: Optional[FirestoreService] = None) -> None:
        self.db = db or get_firestore_service()

    async def get_heatmap_points(self) -> List[HeatmapPoint]:
        """Fetch heatmap points from database or compute from mock venues."""
        try:
            points = await self.db.get_heatmap_points()
            if points:
                return points
        except Exception as e:
            logger.warning(f"Error fetching heatmap points from database: {e}. Falling back to mock dataset.")

        # Fallback to mock venues
        venues = MockDataSeeder.get_seed_venues()
        return [
            HeatmapPoint(
                latitude=v.location.latitude,
                longitude=v.location.longitude,
                weight=round(v.crowd_score / 100.0, 2),
                venue_name=v.venue_name,
            )
            for v in venues
        ]

    async def get_all_venues(self) -> List[VenueLiveStatus]:
        """Fetch all venues live status with fallback."""
        try:
            venues = await self.db.get_all_venues()
            if venues:
                return venues
        except Exception as e:
            logger.warning(f"Error fetching venues from database: {e}. Falling back to mock dataset.")

        return MockDataSeeder.get_seed_venues()

    async def get_venue_by_id(self, venue_id: str) -> Optional[VenueLiveStatus]:
        """Fetch single venue status with fallback."""
        try:
            venue = await self.db.get_venue_by_id(venue_id)
            if venue:
                return venue
        except Exception as e:
            logger.warning(f"Error fetching venue {venue_id} from database: {e}. Falling back to mock.")

        venues = MockDataSeeder.get_seed_venues()
        for v in venues:
            if v.venue_id == venue_id:
                return v
        return None


_crowd_service_instance: Optional[CrowdService] = None


def get_crowd_service() -> CrowdService:
    """Singleton getter for CrowdService."""
    global _crowd_service_instance
    if _crowd_service_instance is None:
        _crowd_service_instance = CrowdService()
    return _crowd_service_instance
