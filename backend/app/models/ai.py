"""Models for the lightweight Vertex AI recommendation endpoint."""

from typing import Any, Dict, List

from pydantic import BaseModel, Field


class AiRecommendRequest(BaseModel):
    """Natural-language request plus the event catalog visible to the client."""

    message: str = Field(..., min_length=1, max_length=1200)
    events: List[Dict[str, Any]] = Field(default_factory=list, max_length=100)


class AiRecommendResponse(BaseModel):
    """Small response contract used by the Vue prototype."""

    reply: str
    provider: str
    model: str
    used_event_count: int
