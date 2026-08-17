"""Small Vertex AI Gemini adapter used by the demo UI."""

import asyncio
import json
from typing import Any, Dict, List, Optional

from google import genai
from google.genai import types

from app.config import settings


SYSTEM_INSTRUCTION = """
你是 SideQuest 的台北城市活動 Agent，請用繁體中文回答。
使用者會描述他現在想怎麼感受城市，後面會附上目前活動資料。
只能根據提供的活動資料回答，不要捏造不存在的活動、時間、費用、地址或人流數據。
請先給一句 1-2 句的決策摘要，再列出最多 3 個最符合需求的活動名稱與理由。
如果資料不足以判斷，明確說明不足之處；不要輸出模型的隱藏思考過程。
語氣要像懂台北、重視舒適與人流分散的在地朋友。
""".strip()


class VertexAiService:
    """Provides a stable app-facing contract over Vertex AI or Gemini API key auth."""

    provider = "vertex-ai"

    def __init__(self) -> None:
        self.model = settings.GEMINI_MODEL
        self._client: Optional[genai.Client] = None

    def _get_client(self) -> genai.Client:
        if self._client is not None:
            return self._client
        if settings.GEMINI_API_KEY:
            self._client = genai.Client(api_key=settings.GEMINI_API_KEY)
        elif settings.GCP_PROJECT_ID:
            self._client = genai.Client(
                vertexai=True,
                project=settings.GCP_PROJECT_ID,
                location=settings.GOOGLE_CLOUD_LOCATION,
            )
        else:
            raise RuntimeError("Vertex AI is not configured: set GCP_PROJECT_ID or GEMINI_API_KEY")
        return self._client

    @staticmethod
    def _compact_events(events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Send only fields useful to the model and keep prompt size bounded."""
        allowed_fields = (
            "id", "name", "title", "category", "dateRange", "startDate", "endDate",
            "time", "highlight", "address", "venue", "fee", "admission", "description",
            "organizer", "source", "sourceUrl", "crowd", "sun", "distance",
        )
        compacted: List[Dict[str, Any]] = []
        for event in events[:100]:
            compacted.append({key: event[key] for key in allowed_fields if key in event and event[key] not in (None, "")})
        return compacted

    def _generate(self, message: str, events: List[Dict[str, Any]]) -> str:
        client = self._get_client()
        prompt = (
            f"使用者需求：\n{message}\n\n"
            f"活動資料（JSON）：\n{json.dumps(self._compact_events(events), ensure_ascii=False)}"
        )
        response = client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_INSTRUCTION,
                temperature=0.35,
                max_output_tokens=900,
            ),
        )
        text = (response.text or "").strip()
        if not text:
            raise RuntimeError("Vertex AI returned an empty response")
        return text

    async def recommend(self, message: str, events: List[Dict[str, Any]]) -> str:
        """Run the blocking SDK call off the FastAPI event loop."""
        return await asyncio.to_thread(self._generate, message, events)


_service: Optional[VertexAiService] = None


def get_vertex_ai_service() -> VertexAiService:
    global _service
    if _service is None:
        _service = VertexAiService()
    return _service
