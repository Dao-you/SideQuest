"""Crowd Density Sensing Tool using CrowdServiceInterface."""

from typing import Any, Dict, Optional
from app.agent.tools.base import BaseTool
from app.services.crowd_service import get_crowd_service


class CrowdTool(BaseTool):
    """Tool to check real-time crowd congestion index, wait times, and flow trends."""

    name = "check_crowd_density"
    description = (
        "查詢指定活動場館或商圈的即時人潮擁擠指數 (Crowd Score 0-100)、人流等級 (LOW/MODERATE/HIGH/OVERLOADED) 與排隊等候時間。"
        "若指數超過 80 代表極度擁擠，應主動尋找鄰近私房替代場館。"
    )
    parameters_schema = {
        "type": "object",
        "properties": {
            "venue_id": {
                "type": "string",
                "description": "場館唯一識別碼，例如 'venue_huashan', 'venue_songshan', 'venue_popop', 'venue_clab'",
            },
            "venue_name": {
                "type": "string",
                "description": "場館或地標名稱，例如 '華山1914', '松山文創', '瓶蓋工廠'",
            },
        },
    }

    async def execute(
        self,
        venue_id: Optional[str] = None,
        venue_name: Optional[str] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Execute crowd density inspection."""
        service = get_crowd_service()
        venues = await service.get_all_venues()

        matched_venue = None
        if venue_id:
            matched_venue = next((v for v in venues if v.venue_id == venue_id), None)
        elif venue_name:
            matched_venue = next(
                (v for v in venues if venue_name.lower() in v.venue_name.lower() or v.venue_name.lower() in venue_name.lower()),
                None,
            )

        if matched_venue:
            is_overloaded = matched_venue.crowd_score >= 80
            # Identify low-crowd alternative if overloaded
            alternative_suggestion = None
            if is_overloaded:
                low_crowd_venues = [v for v in venues if v.crowd_score <= 35 and v.venue_id != matched_venue.venue_id]
                if low_crowd_venues:
                    alt = low_crowd_venues[0]
                    alternative_suggestion = {
                        "alternative_venue_id": alt.venue_id,
                        "alternative_venue_name": alt.venue_name,
                        "alternative_crowd_score": alt.crowd_score,
                        "alternative_mrt": alt.location.mrt_station,
                        "reason": f"相較於 {matched_venue.venue_name} (人潮指數 {matched_venue.crowd_score})，{alt.venue_name} 目前人潮僅 {alt.crowd_score}，看展與休閒品質極佳！",
                    }

            return {
                "status": "success",
                "venue_id": matched_venue.venue_id,
                "venue_name": matched_venue.venue_name,
                "crowd_score": matched_venue.crowd_score,
                "crowd_level": matched_venue.crowd_level.value,
                "wait_time_minutes": matched_venue.wait_time_minutes,
                "trend": matched_venue.trend.value,
                "is_overloaded": is_overloaded,
                "alternative_suggestion": alternative_suggestion,
            }

        # If no specific venue provided, return general city congestion overview
        avg_score = sum(v.crowd_score for v in venues) / max(1, len(venues))
        return {
            "status": "success",
            "city_average_crowd_score": round(avg_score, 1),
            "top_congested_venues": [
                {"venue_name": v.venue_name, "crowd_score": v.crowd_score, "level": v.crowd_level.value}
                for v in sorted(venues, key=lambda x: x.crowd_score, reverse=True)[:3]
            ],
            "top_comfortable_hidden_gems": [
                {"venue_name": v.venue_name, "crowd_score": v.crowd_score, "level": v.crowd_level.value}
                for v in sorted(venues, key=lambda x: x.crowd_score)[:3]
            ],
        }
