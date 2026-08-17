"""Places Details and Route Comfort Service with Interface."""

from typing import Optional
from app.models.places import PlaceDetails, RouteComfort
from app.services.interfaces import PlacesServiceInterface
from app.services.maps_service import MapsService, get_maps_service


class PlacesService(PlacesServiceInterface):
    """Places and Routing service implementing PlacesServiceInterface."""

    def __init__(self, maps: Optional[MapsService] = None) -> None:
        self.maps = maps or get_maps_service()

    async def get_place_details(
        self,
        place_name: str,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
    ) -> PlaceDetails:
        """Fetch place details from Google Places (New) API or fallback."""
        return await self.maps.get_place_details(place_name, latitude, longitude)

    async def compute_route(
        self,
        origin_lat: float,
        origin_lng: float,
        dest_lat: float,
        dest_lng: float,
        dest_name: str = "目的地",
        prioritize_shade: bool = True,
    ) -> RouteComfort:
        """Compute transit and shaded pedestrian route with comfort rating."""
        return await self.maps.compute_route(
            origin_lat=origin_lat,
            origin_lng=origin_lng,
            dest_lat=dest_lat,
            dest_lng=dest_lng,
            dest_name=dest_name,
            prioritize_shade=prioritize_shade,
        )


_places_service_instance: Optional[PlacesService] = None


def get_places_service() -> PlacesService:
    """Singleton getter for PlacesService."""
    global _places_service_instance
    if _places_service_instance is None:
        _places_service_instance = PlacesService()
    return _places_service_instance
