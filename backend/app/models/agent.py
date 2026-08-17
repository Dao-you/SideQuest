"""Agent Interaction, SSE Streaming, Structured Criteria, and Recommendation Models."""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from app.models.event import RecommendationCard


class SSEEventType(str, Enum):
    """Server-Sent Event Types for Agent Reasoning Stream."""
    THOUGHT = "thought"
    UNDERSTANDING = "understanding"          # PRD 7.3: Structured criteria confirmation
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    MARKDOWN_CHUNK = "markdown_chunk"
    RECOMMENDATION_CARDS = "recommendation_cards"
    DONE = "done"
    ERROR = "error"


class ParsedCriteria(BaseModel):
    """PRD Section 7.3: Agent's structured understanding of user query."""
    date_time_range: str = Field(default="本週末下午", description="Understood date & time range")
    target_district: str = Field(default="台北市全區", description="Understood target area or district")
    interests: List[str] = Field(default_factory=list, description="Extracted interest topics / categories")
    max_budget_twd: Optional[int] = Field(default=None, description="Budget cap in TWD (None if not specified)")
    is_free_only: bool = Field(default=False, description="Strictly free events only")
    max_travel_minutes: Optional[int] = Field(default=45, description="Maximum acceptable transit time")
    avoid_crowd: bool = Field(default=True, description="Enforce crowd dispersal penalty")
    prefer_indoor: Optional[bool] = Field(default=None, description="Indoor / AC preference")
    assumptions: List[str] = Field(default_factory=list, description="Reasonable default assumptions made by Agent")
    clarification_question: Optional[str] = Field(default=None, description="Max 1 clarification question if ambiguous")


class AgentThoughtStep(BaseModel):
    """A single step in the Agent's reasoning trace."""
    step: int
    title: str
    tool_name: Optional[str] = None
    tool_args: Optional[Dict[str, Any]] = None
    tool_output_summary: Optional[str] = None
    thought: str
    timestamp: str


class ChatRequest(BaseModel):
    """User message and context for Agent chat."""
    message: str = Field(..., description="User query in natural language")
    user_latitude: Optional[float] = Field(default=25.0330, description="User current latitude (default: Taipei)")
    user_longitude: Optional[float] = Field(default=121.5654, description="User current longitude")
    session_id: Optional[str] = Field(default=None, description="Optional session ID for multi-turn conversations")
    user_id: Optional[str] = Field(default="demo_weekend_explorer", description="User ID for loading preferences/favorites")
    avoid_crowd_strict: bool = Field(default=True, description="Enforce crowd dispersal penalty")
    prefer_indoor: Optional[bool] = Field(default=None, description="Explicit indoor AC preference")
    max_budget_twd: Optional[int] = Field(default=None, description="Explicit budget limit")
    max_travel_minutes: Optional[int] = Field(default=45, description="Max acceptable transit time")


class ChatResponse(BaseModel):
    """Non-streaming response from Agent."""
    session_id: str
    reply: str
    parsed_criteria: Optional[ParsedCriteria] = None
    one_sentence_summary: str = Field(default="", description="PRD 7.6: One-sentence explanation of how results were derived/changed")
    thought_steps: List[AgentThoughtStep] = Field(default_factory=list)
    recommendations: List[RecommendationCard] = Field(default_factory=list)
    dispersal_summary: str = Field(default="")
    execution_time_ms: float = 0.0


class SSEEvent(BaseModel):
    """Structured SSE event payload."""
    event: SSEEventType
    data: Any


class AgentRecommendationRequest(BaseModel):
    """Quick structured recommendation request."""
    user_latitude: float = 25.0330
    user_longitude: float = 121.5654
    interests: List[str] = Field(default_factory=list, description="Keywords / categories, e.g. ['art', 'cafe', 'tech']")
    avoid_crowd: bool = True
    prefer_indoor: bool = True
    max_budget: Optional[int] = None
    limit: int = Field(default=3, ge=1, le=10)


class AgentRecommendation(BaseModel):
    """Container for recommendation query results."""
    recommendations: List[RecommendationCard]
    dispersal_insights: str
    total_evaluated: int
    city_crowd_status: str


class QuickPromptItem(BaseModel):
    """Example prompt for home page (PRD 7.2)."""
    title: str
    prompt: str
    category: str
    icon: str


class QuickTagItem(BaseModel):
    """Quick filter chip for home page (PRD 7.2)."""
    id: str
    label: str
    icon: str
    filter_key: str
    filter_value: Any


class QuickPromptsResponse(BaseModel):
    """PRD Section 7.2: Example prompts and quick chips."""
    example_prompts: List[QuickPromptItem]
    quick_tags: List[QuickTagItem]


class FeedbackRequest(BaseModel):
    """PRD Section 6 (Stage 10): User feedback on recommendation accuracy."""
    session_id: str
    event_id: str
    is_helpful: bool
    feedback_tag: Optional[str] = Field(default=None, description="'accurate', 'too_far', 'too_crowded', 'expensive', 'not_interested'")
    comment: Optional[str] = None


class FeedbackResponse(BaseModel):
    """Feedback acknowledgment response."""
    status: str = "success"
    message: str = "感謝您的回饋！SideQuest 將持續優化推薦演算法。"
