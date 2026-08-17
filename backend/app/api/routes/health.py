"""Health Check and Cloud Run Probe Routes."""

from typing import Any, Dict
from fastapi import APIRouter, Depends, Response, status

from app.api.deps import get_firestore_dep
from app.config import settings
from app.services.firestore_service import FirestoreService

router = APIRouter(tags=["Health & Monitoring"])


@router.get(
    "/healthz",
    summary="Cloud Run Liveness Probe (存活探針)",
    description="檢查後端伺服器程序是否存活。",
)
async def healthz() -> Dict[str, Any]:
    """Liveness probe."""
    return {
        "status": "ok",
        "service": settings.APP_NAME,
        "environment": settings.ENVIRONMENT,
    }


@router.get(
    "/readiness",
    summary="Cloud Run Readiness Probe (就緒探針)",
    description="確認後端資料庫與相依服務是否正常就緒可接收流量。",
)
async def readiness(
    response: Response,
    db: FirestoreService = Depends(get_firestore_dep),
) -> Dict[str, Any]:
    """Readiness probe."""
    is_ready = await db.is_healthy()
    if not is_ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {
            "status": "unhealthy",
            "database_ready": False,
        }

    return {
        "status": "ready",
        "database_ready": True,
        "gcp_firestore_connected": db.is_connected_to_gcp,
        "environment": settings.ENVIRONMENT,
    }
