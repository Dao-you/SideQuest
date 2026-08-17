"""User Recommendation Feedback Service with Interface."""

from typing import List, Optional
from app.logging_config import logger
from app.models.agent import FeedbackRequest, FeedbackResponse
from app.services.firestore_service import FirestoreService, get_firestore_service
from app.services.interfaces import FeedbackServiceInterface


class FeedbackService(FeedbackServiceInterface):
    """Feedback service implementing FeedbackServiceInterface with Firestore logging and mock fallback."""

    def __init__(self, db: Optional[FirestoreService] = None) -> None:
        self.db = db or get_firestore_service()
        self._local_feedbacks: List[dict] = []

    async def submit_feedback(self, req: FeedbackRequest) -> FeedbackResponse:
        """Record user feedback rating and comments."""
        feedback_data = req.model_dump()
        self._local_feedbacks.append(feedback_data)
        logger.info(f"Feedback received: session={req.session_id}, event={req.event_id}, helpful={req.is_helpful}, tag={req.feedback_tag}")

        # If connected to Firestore, persist into collection 'feedbacks'
        if self.db.is_connected_to_gcp and self.db.db is not None:
            try:
                self.db.db.collection("feedbacks").add(feedback_data)
            except Exception as e:
                logger.warning(f"Could not persist feedback to Firestore: {e}. Saved in memory.")

        return FeedbackResponse(
            status="success",
            message=f"已成功記錄對活動 '{req.event_id}' 的回饋（{'符合需求' if req.is_helpful else '不符合需求'}）。SideQuest 感謝您的寶貴建議！",
        )


_feedback_service_instance: Optional[FeedbackService] = None


def get_feedback_service() -> FeedbackService:
    """Singleton getter for FeedbackService."""
    global _feedback_service_instance
    if _feedback_service_instance is None:
        _feedback_service_instance = FeedbackService()
    return _feedback_service_instance
