"""SideQuest Autonomous Agent Orchestrator with Gemini 3.7 & PRD Multi-turn Reasoning."""

import asyncio
from datetime import datetime, timezone
import json
import re
import time
from typing import Any, AsyncGenerator, Dict, List, Optional, Tuple
import uuid

from app.agent.date_parser import parse_natural_date_time
from app.agent.prompt_templates import SYSTEM_PROMPT
from app.agent.ranking_engine import ranking_engine
from app.agent.tools import get_tool_registry
from app.config import settings
from app.logging_config import logger
from app.models.agent import (
    AgentRecommendation,
    AgentRecommendationRequest,
    AgentThoughtStep,
    ChatRequest,
    ChatResponse,
    ParsedCriteria,
    SSEEvent,
    SSEEventType,
)
from app.models.event import EventFilter, RecommendationCard
from app.services.crowd_service import get_crowd_service
from app.services.event_service import get_event_service
from app.services.interfaces import (
    CrowdServiceInterface,
    EventServiceInterface,
    PlacesServiceInterface,
    UserServiceInterface,
    WeatherServiceInterface,
)
from app.services.places_service import get_places_service
from app.services.user_service import get_user_service
from app.services.weather_service import get_weather_service


class GeminiAgent:
    """Agent orchestrator managing multi-step reasoning, tool invocations, and SSE streams using Service Interfaces."""

    def __init__(
        self,
        event_service: Optional[EventServiceInterface] = None,
        crowd_service: Optional[CrowdServiceInterface] = None,
        weather_service: Optional[WeatherServiceInterface] = None,
        places_service: Optional[PlacesServiceInterface] = None,
        user_service: Optional[UserServiceInterface] = None,
    ) -> None:
        self.api_key = settings.GEMINI_API_KEY
        self.model_name = settings.GEMINI_MODEL
        self.tool_registry = get_tool_registry()
        self.event_service = event_service or get_event_service()
        self.crowd_service = crowd_service or get_crowd_service()
        self.weather_service = weather_service or get_weather_service()
        self.places_service = places_service or get_places_service()
        self.user_service = user_service or get_user_service()
        # In-memory session store for multi-turn contextual refinement (PRD 7.6)
        self._session_cache: Dict[str, Dict[str, Any]] = {}

    def _parse_user_criteria(self, query: str, prev_criteria: Optional[ParsedCriteria] = None) -> Tuple[ParsedCriteria, str]:
        """Extract structured criteria from natural language and detect modification delta (PRD 7.3 & 7.6)."""
        q = query.lower()
        delta_summary = ""

        # Inherit previous criteria if available
        if prev_criteria:
            date_time = prev_criteria.date_time_range
            district = prev_criteria.target_district
            interests = list(prev_criteria.interests)
            max_budget = prev_criteria.max_budget_twd
            is_free = prev_criteria.is_free_only
            max_travel = prev_criteria.max_travel_minutes
            avoid_crowd = prev_criteria.avoid_crowd
            prefer_indoor = prev_criteria.prefer_indoor
            assumptions = list(prev_criteria.assumptions)
            requested_date = prev_criteria.requested_date
            requested_date_end = prev_criteria.requested_date_end
            requested_start_time = prev_criteria.requested_start_time
            requested_end_time = prev_criteria.requested_end_time
            date_resolution = prev_criteria.date_resolution
            occasion = prev_criteria.occasion
            is_refinement = True
        else:
            date_time = "本週末下午"
            district = "台北市全區"
            interests = []
            max_budget = None
            is_free = False
            max_travel = 45
            avoid_crowd = True
            prefer_indoor = True
            assumptions = ["預設以台北市捷運沿線為範圍", "優先推薦具備空調避暑之場館"]
            requested_date = None
            requested_date_end = None
            requested_start_time = None
            requested_end_time = None
            date_resolution = "unspecified"
            occasion = None
            is_refinement = False

        # 1. District extraction
        districts = ["中正區", "信義區", "大安區", "大同區", "中山區", "南港區", "士林區", "萬華區"]
        for d in districts:
            if d in query or d.replace("區", "") in query:
                district = d
                if is_refinement:
                    delta_summary += f"已將搜尋區域限制為【{district}】；"
                break

        # 2. Date/Time extraction. Keep the human-readable label and normalized
        # values together so the same window can be used by the catalog filter.
        parsed_window = parse_natural_date_time(query)
        if parsed_window:
            date_time = parsed_window.label
            requested_date = parsed_window.start_date.isoformat()
            requested_date_end = parsed_window.end_date.isoformat()
            requested_start_time = parsed_window.start_time.strftime("%H:%M") if parsed_window.start_time else None
            requested_end_time = parsed_window.end_time.strftime("%H:%M") if parsed_window.end_time else None
            date_resolution = parsed_window.resolution
            if is_refinement:
                delta_summary += f"已將活動日期調整為【{date_time}】；"

        # 3. Occasion extraction for date planning (especially date/partner queries).
        if any(token in q for token in ("約會", "另一半", "男朋友", "女朋友", "情侶", "浪漫")):
            occasion = "約會"
            if "浪漫約會" not in interests:
                interests.append("浪漫約會")
        elif any(token in q for token in ("親子", "小孩", "孩子")):
            occasion = "親子"

        # 4. Budget extraction (PRD 7.6: "只看免費的", "500元內")
        if "免費" in query:
            is_free = True
            max_budget = 0
            if is_refinement:
                delta_summary += "已篩選為【純免費活動】；"
        else:
            budget_match = re.search(r"(\d+)\s*(?:元|塊|twd|nt)", query, re.IGNORECASE)
            if budget_match:
                max_budget = int(budget_match.group(1))
                if is_refinement:
                    delta_summary += f"已限制預算上限為【{max_budget} 元以內】；"

        # 5. Crowd preference (PRD 7.6: "不想去太多人", "避開人潮")
        if any(w in query for w in ["不要太擠", "不想人擠人", "太多人", "避開人潮", "少人"]):
            avoid_crowd = True
            if is_refinement:
                delta_summary += "已嚴格啟用【避開人潮優先機制】；"

        # 6. Indoor / Outdoor preference
        if "室內" in query or "吹冷氣" in query:
            prefer_indoor = True
            if is_refinement:
                delta_summary += "已切換為【全室內空調活動】；"
        elif "戶外" in query or "公園" in query:
            prefer_indoor = False
            if is_refinement:
                delta_summary += "已切換為【戶外體驗活動】；"

        # 7. Distance / Transit preference (PRD 7.6: "第二個太遠了", "太遠", "近一點")
        if any(w in query for w in ["太遠", "近一點", "走不到", "捷運直達"]):
            max_travel = 25
            if is_refinement:
                delta_summary += "已縮減可接受交通距離至【25分鐘以內/捷運直達】；"

        # 8. Interests / Topics extraction
        topic_map = {
            "ai": "AI 人工智慧",
            "agent": "AI Agent",
            "技術": "技術講座",
            "產品": "產品設計",
            "ux": "UX 設計",
            "黑客松": "黑客松",
            "devjam": "DevJam",
            "展覽": "文藝特展",
            "市集": "風格市集",
            "咖啡": "獨立咖啡",
            "手作": "創客手作",
            "文博會": "臺灣文博會",
            "煙火": "夏日煙火節",
            "音樂": "音樂展演",
            "親子": "親子互動",
            "動漫": "動漫特展",
        }
        for k, label in topic_map.items():
            if k in q and label not in interests:
                interests.append(label)

        if not interests and not is_refinement:
            interests = ["城市探索", "週末休閒"]

        parsed = ParsedCriteria(
            date_time_range=date_time,
            target_district=district,
            interests=interests,
            max_budget_twd=max_budget,
            is_free_only=is_free,
            max_travel_minutes=max_travel,
            avoid_crowd=avoid_crowd,
            prefer_indoor=prefer_indoor,
            requested_date=requested_date,
            requested_date_end=requested_date_end,
            requested_start_time=requested_start_time,
            requested_end_time=requested_end_time,
            date_resolution=date_resolution,
            occasion=occasion,
            assumptions=assumptions,
            clarification_question=None,
        )

        if not delta_summary:
            delta_summary = f"已根據您的需求「{query[:20]}」為您即時重排並提供 3 個最佳活動建議。"

        return parsed, delta_summary

    async def _execute_tool(self, name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """Execute registered tool by name with exception handling."""
        try:
            tool = self.tool_registry.get_tool(name)
            return await tool.execute(**args)
        except Exception as e:
            logger.error(f"Error executing tool {name} with args {args}: {e}")
            return {"status": "error", "message": str(e)}

    async def stream_chat(self, request: ChatRequest) -> AsyncGenerator[SSEEvent, None]:
        """Stream thoughts, tool traces, response text, and recommendation cards via SSE (PRD Section 6 & 7)."""
        session_id = request.session_id or f"sess_{uuid.uuid4().hex[:10]}"
        start_time = time.time()
        user_msg = request.message
        user_lat = request.user_latitude or 25.0330
        user_lng = request.user_longitude or 121.5654
        user_id = request.user_id or "demo_weekend_explorer"

        # Load user profile & previous session criteria (PRD 7.1 & 7.6)
        user_profile = self.user_service.get_user_profile(user_id)
        prev_session = self._session_cache.get(session_id, {})
        prev_criteria: Optional[ParsedCriteria] = prev_session.get("criteria")

        thought_steps: List[AgentThoughtStep] = []

        # =========================================================================
        # Stage 1: Natural Language Intent Parsing & Criteria Confirmation (PRD 7.3)
        # =========================================================================
        parsed_criteria, delta_summary = self._parse_user_criteria(user_msg, prev_criteria)
        self._session_cache[session_id] = {"criteria": parsed_criteria, "user_id": user_id}

        step1_title = "解析自然語言意圖與結構化條件確認"
        step1_thought = f"已解析使用者需求：時段【{parsed_criteria.date_time_range}】、區域【{parsed_criteria.target_district}】、興趣【{', '.join(parsed_criteria.interests)}】、預算【{'免費' if parsed_criteria.is_free_only else (f'{parsed_criteria.max_budget_twd}元內' if parsed_criteria.max_budget_twd else '不限')}】。"
        thought_steps.append(
            AgentThoughtStep(
                step=1,
                title=step1_title,
                tool_name="intent_parser",
                thought=step1_thought,
                timestamp=datetime.now(timezone.utc).isoformat(),
            )
        )
        yield SSEEvent(
            event=SSEEventType.THOUGHT,
            data={"step": 1, "title": step1_title, "thought": step1_thought},
        )
        await asyncio.sleep(0.1)

        # Emit PRD 7.3 Structured Criteria
        yield SSEEvent(
            event=SSEEventType.UNDERSTANDING,
            data=parsed_criteria.model_dump(),
        )
        await asyncio.sleep(0.1)

        # =========================================================================
        # Stage 2: Event Discovery across Catalogs (PRD 6 Stage 4)
        # =========================================================================
        event_search_args = {
            "keyword": user_msg,
            "limit": 10,
            "start_date": parsed_criteria.requested_date,
            "end_date": parsed_criteria.requested_date_end,
            "start_time": parsed_criteria.requested_start_time,
            "end_time": parsed_criteria.requested_end_time,
        }
        yield SSEEvent(
            event=SSEEventType.TOOL_CALL,
            data={"tool": "search_events", "args": {k: v for k, v in event_search_args.items() if v is not None}},
        )
        event_tool_res = await self._execute_tool("search_events", event_search_args)
        if event_tool_res.get("total_found", 0) == 0:
            event_tool_res = await self._execute_tool(
                "search_events",
                {k: v for k, v in event_search_args.items() if k != "keyword" and v is not None} | {"limit": 10},
            )

        yield SSEEvent(
            event=SSEEventType.TOOL_RESULT,
            data={"tool": "search_events", "result": f"自 Accupass、Luma、文化部與台北旅遊網檢索到 {event_tool_res.get('total_found', 0)} 個候選活動"},
        )
        await asyncio.sleep(0.1)

        # =========================================================================
        # Stage 3: Microclimate, Solar Exposure & Crowd Sensing
        # =========================================================================
        step2_title = "即時微氣候與熱點人潮多維度感知"
        step2_thought = "調用 check_weather, get_solar_exposure 與 check_crowd_density 評估熱舒適度與人潮擁擠指數..."
        thought_steps.append(
            AgentThoughtStep(
                step=2,
                title=step2_title,
                tool_name="check_crowd_density,check_weather",
                thought=step2_thought,
                timestamp=datetime.now(timezone.utc).isoformat(),
            )
        )
        yield SSEEvent(
            event=SSEEventType.THOUGHT,
            data={"step": 2, "title": step2_title, "thought": step2_thought},
        )
        await asyncio.sleep(0.1)

        weather_res = await self._execute_tool("check_weather", {"latitude": user_lat, "longitude": user_lng})
        solar_res = await self._execute_tool("get_solar_exposure", {"latitude": user_lat, "longitude": user_lng})
        crowd_res = await self._execute_tool("check_crowd_density", {})

        yield SSEEvent(
            event=SSEEventType.TOOL_RESULT,
            data={
                "tool": "check_weather_and_crowd",
                "result": {
                    "temperature": f"{weather_res.get('temperature_c')}°C",
                    "uv_index": weather_res.get("uv_index"),
                    "city_avg_crowd": crowd_res.get("city_average_crowd_score"),
                },
            },
        )
        await asyncio.sleep(0.1)

        # =========================================================================
        # Stage 4: Multi-Criteria Weighted Decision & Dispersal (PRD 8.3)
        # =========================================================================
        step3_title = "人流疏導推薦運算與捷運遮蔭路徑評估"
        step3_thought = "依 PRD 權重（興趣 35%、時間 25%、交通 20%、預算 10%、舒適 10%）進行綜合決策並生成 3 大卡片..."
        thought_steps.append(
            AgentThoughtStep(
                step=3,
                title=step3_title,
                tool_name="compute_route,ranking_engine",
                thought=step3_thought,
                timestamp=datetime.now(timezone.utc).isoformat(),
            )
        )
        yield SSEEvent(
            event=SSEEventType.THOUGHT,
            data={"step": 3, "title": step3_title, "thought": step3_thought},
        )
        await asyncio.sleep(0.1)

        event_filter = EventFilter(
            district=None if parsed_criteria.target_district == "台北市全區" else parsed_criteria.target_district,
            start_date=parsed_criteria.requested_date,
            end_date=parsed_criteria.requested_date_end,
            start_time=parsed_criteria.requested_start_time,
            end_time=parsed_criteria.requested_end_time,
            limit=100,
        )
        all_events = await self.event_service.get_events(event_filter)
        all_venues = await self.crowd_service.get_all_venues()
        venues_map = {v.venue_id: v for v in all_venues}
        microclimate = await self.weather_service.get_microclimate(user_lat, user_lng)

        # Compute routes
        routes_map = {}
        for ev in all_events:
            route = await self.places_service.compute_route(
                origin_lat=user_lat,
                origin_lng=user_lng,
                dest_lat=ev.location.latitude,
                dest_lng=ev.location.longitude,
                dest_name=ev.venue_name,
                prioritize_shade=True,
            )
            routes_map[ev.id] = route

        # Run PRD Ranking Engine
        top_3_cards = ranking_engine.rank_and_build_cards(
            events=all_events,
            venues_map=venues_map,
            weather=microclimate,
            routes_map=routes_map,
            query_text=user_msg,
            avoid_crowd_strict=parsed_criteria.avoid_crowd,
            prefer_indoor=parsed_criteria.prefer_indoor,
            max_budget=parsed_criteria.max_budget_twd,
            is_free_only=parsed_criteria.is_free_only,
        )

        # Detect overloaded venue and dispersal alternative
        overcrowded_card = next((c for c in top_3_cards if c.crowd_score >= 80), None)
        hidden_gem_card = next((c for c in top_3_cards if c.is_dispersal_alternative or c.crowd_score <= 35), None)

        # =========================================================================
        # Stage 5: Markdown Stream Generation
        # =========================================================================
        markdown_sections = []

        date_summary = (
            f"📅 **指定行程日期**：**{parsed_criteria.date_time_range}**，已只評估當天可參加且時段有交集的活動。\n\n"
            if parsed_criteria.requested_date
            else ""
        )
        markdown_sections.append(
            f"### 🧭 SideQuest 智慧活動與人流決策報告\n\n"
            f"> 💬 **決策摘要**：{delta_summary}\n\n"
            f"{date_summary}"
            f"☀️ **微氣候與環境感知**：台北當前氣溫 **{microclimate.temperature_c}°C**（體感 {microclimate.apparent_temperature_c}°C），"
            f"紫外線指數 **{microclimate.uv_index} ({microclimate.uv_risk_level.value})**。已為您優先規劃具備**全室內空調**與**捷運地下街直通**的活動動線！\n\n"
        )

        if overcrowded_card and hidden_gem_card:
            markdown_sections.append(
                f"### ⚠️ 即時人潮警示與智慧疏導建議\n"
                f"> **熱點人流過載**：`{overcrowded_card.event.venue_name}` 目前人潮指數高達 **{overcrowded_card.crowd_score}/100**（排隊約 25-35 分鐘），容易造成擁擠與悶熱感。\n"
                f">\n"
                f"> **✨ 專屬私房替代推薦**：建議您前往 **[{hidden_gem_card.event.venue_name}]**！\n"
                f"> 目前人潮指數僅 **{hidden_gem_card.crowd_score}/100**（舒適免排隊），同樣具備優質活動內容與冷氣環境，並可透過 **{hidden_gem_card.event.location.mrt_station}** 直通，避開烈日曝曬。\n\n"
            )

        if not top_3_cards:
            markdown_sections.append(
                "### 🔎 目前沒有符合指定日期與時段的活動\n\n"
                "可以試著放寬時間、改成整天，或告訴我另一個日期，我會保留約會／活動偏好重新搜尋。\n\n"
            )
        else:
            markdown_sections.append(f"### 🎯 為您精選 3 個最佳活動建議：\n\n")

        for card in top_3_cards:
            badge_texts = " ".join([f"`{b.label}`" for b in card.badges])
            markdown_sections.append(
                f"**【{card.card_role_label}】{card.event.title}**\n"
                f"- 📍 **場館與地點**：{card.event.venue_name} ({card.event.location.district})\n"
                f"- 🏷️ **來源與平台**：`{card.event.source_platform}` ｜ 💰 **票價**：{card.event.price_type == 'free' and '免費' or f'{card.event.price_amount} 元'}\n"
                f"- 👥 **即時人潮**：**{card.crowd_score}/100** ({card.crowd_level}) ｜ 🌟 **綜合決策分**：**{card.total_score} 分**\n"
                f"- 🚇 **交通與遮蔭**：{card.transit_summary}\n"
                f"- 💡 **推薦理由**：{card.recommendation_reason}\n\n"
            )

        markdown_sections.append(
            f"您可以點擊活動卡片直接前往原始平台（如 Accupass、Luma 或官方網站）查看報名。若需要調整距離或預算，隨時跟我說！"
        )

        full_markdown = "".join(markdown_sections)

        # Stream markdown chunks
        chunk_size = 60
        for i in range(0, len(full_markdown), chunk_size):
            yield SSEEvent(
                event=SSEEventType.MARKDOWN_CHUNK,
                data={"chunk": full_markdown[i : i + chunk_size]},
            )
            await asyncio.sleep(0.03)

        # Yield structured recommendation cards (PRD 7.4)
        yield SSEEvent(
            event=SSEEventType.RECOMMENDATION_CARDS,
            data={
                "cards": [c.model_dump() for c in top_3_cards],
                "dispersal_summary": "已依即時天氣與目前可用的人流資料完成分流排序。",
                "evaluated_count": len(all_events),
            },
        )
        await asyncio.sleep(0.05)

        # Yield Done
        elapsed_ms = round((time.time() - start_time) * 1000, 2)
        yield SSEEvent(
            event=SSEEventType.DONE,
            data={
                "status": "completed",
                "session_id": session_id,
                "total_steps": len(thought_steps),
                "execution_time_ms": elapsed_ms,
                "one_sentence_summary": delta_summary,
            },
        )

    async def chat(self, request: ChatRequest) -> ChatResponse:
        """Non-streaming chat execution returning complete ChatResponse."""
        session_id = request.session_id or f"sess_{uuid.uuid4().hex[:10]}"
        start_time = time.time()
        
        all_chunks: List[str] = []
        thought_steps: List[AgentThoughtStep] = []
        cards: List[RecommendationCard] = []
        parsed_criteria: Optional[ParsedCriteria] = None

        async for event in self.stream_chat(request):
            if event.event == SSEEventType.THOUGHT:
                thought_steps.append(AgentThoughtStep(**event.data, timestamp=datetime.now(timezone.utc).isoformat()))
            elif event.event == SSEEventType.UNDERSTANDING:
                parsed_criteria = ParsedCriteria(**event.data)
            elif event.event == SSEEventType.MARKDOWN_CHUNK:
                all_chunks.append(event.data.get("chunk", ""))
            elif event.event == SSEEventType.RECOMMENDATION_CARDS:
                cards = [RecommendationCard(**c) for c in event.data.get("cards", [])]

        elapsed_ms = round((time.time() - start_time) * 1000, 2)
        return ChatResponse(
            session_id=session_id,
            reply="".join(all_chunks),
            parsed_criteria=parsed_criteria,
            one_sentence_summary=f"已成功為您整合跨平台活動並產出 3 大精準建議。",
            thought_steps=thought_steps,
            recommendations=cards,
            dispersal_summary="已成功運用人流疏導懲罰演算法與微氣候遮蔭評估完成活動排序。",
            execution_time_ms=elapsed_ms,
        )

    async def recommend(self, request: AgentRecommendationRequest) -> AgentRecommendation:
        """Quick structured recommendation method."""
        all_events = await self.event_service.get_events()
        all_venues = await self.crowd_service.get_all_venues()
        venues_map = {v.venue_id: v for v in all_venues}
        microclimate = await self.weather_service.get_microclimate(request.user_latitude, request.user_longitude)

        routes_map = {}
        for ev in all_events:
            route = await self.places_service.compute_route(
                origin_lat=request.user_latitude,
                origin_lng=request.user_longitude,
                dest_lat=ev.location.latitude,
                dest_lng=ev.location.longitude,
                dest_name=ev.venue_name,
                prioritize_shade=True,
            )
            routes_map[ev.id] = route

        query_text = " ".join(request.interests) if request.interests else "週末放鬆看展"
        cards = ranking_engine.rank_and_build_cards(
            events=all_events,
            venues_map=venues_map,
            weather=microclimate,
            routes_map=routes_map,
            query_text=query_text,
            avoid_crowd_strict=request.avoid_crowd,
            prefer_indoor=request.prefer_indoor,
            max_budget=request.max_budget,
        )

        return AgentRecommendation(
            recommendations=cards[: request.limit],
            dispersal_insights="已自動避開人潮擁擠熱點並獎勵低人潮、冷氣舒適之私房活動。",
            total_evaluated=len(all_events),
            city_crowd_status="市區整體人潮中等偏高，華山與松菸人流接近飽和，推薦往南港瓶蓋工廠或大安C-LAB分散。",
        )


_gemini_agent_instance: Optional[GeminiAgent] = None


def get_gemini_agent() -> GeminiAgent:
    """Singleton getter for GeminiAgent."""
    global _gemini_agent_instance
    if _gemini_agent_instance is None:
        _gemini_agent_instance = GeminiAgent()
    return _gemini_agent_instance
