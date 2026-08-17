"""Application runtime configuration routes."""

from fastapi import APIRouter
from app.config import settings

router = APIRouter(prefix="/config", tags=["Configuration"])


@router.get("/maps-key", summary="取得 Google Maps 前端載入密鑰")
async def get_maps_browser_key() -> dict:
    """Dynamically provide the GCP project's browser-restricted Maps API key."""
    return {
        "maps_api_key": settings.GOOGLE_MAPS_API_KEY,
        "gcp_project_id": settings.GCP_PROJECT_ID,
        "environment": settings.ENVIRONMENT,
    }
