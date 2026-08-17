"""FastAPI Application Main Entry Point."""

from contextlib import asynccontextmanager
import time
from typing import AsyncGenerator
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import (
    agent_router,
    crowd_router,
    events_router,
    health_router,
    routes_router,
    user_router,
    weather_router,
)
from app.config import settings
from app.logging_config import logger
from app.services.firestore_service import get_firestore_service


def get_lan_ip() -> str:
    """Detect local network IPv4 address."""
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifecycle hook: initializes database and seed data on startup."""
    logger.info("Initializing SideQuest Backend Application...")
    firestore_service = get_firestore_service()
    await firestore_service.initialize()
    lan_ip = get_lan_ip()
    port = settings.PORT
    logger.info("Database and services initialized successfully.")
    logger.info("SideQuest Backend local docs: http://localhost:%s/docs", port)
    logger.info("SideQuest Backend LAN docs: http://%s:%s/docs", lan_ip, port)
    logger.info("SideQuest Backend health: http://%s:%s/healthz", lan_ip, port)
    yield
    logger.info("Shutting down SideQuest Backend...")


OPENAPI_TAGS = [
    {
        "name": "Agent Discovery & Decision",
        "description": (
            "🧭 **Gemini 3.7 Flash / Vertex AI Agentic Core**\n\n"
            "提供自然語言意圖理解 (PRD 7.3)、指定日期／時間與約會情境解析、自主調用 6 大工具之推論軌跡、"
            "**人流疏導推薦演算法 (PRD 8.3 五大權重)**，Server-Sent Events (SSE) 思考串流，以及 3 大推薦卡片輸出。"
        ),
    },
    {
        "name": "User & Persona (Mock Login)",
        "description": (
            "👤 **模擬登入與個人狀態 (PRD Section 7.1)**\n\n"
            "提供 4 大測試角色（週末探索者、技術社群愛好者、避開人潮者、親子家庭家長）Demo Login、個人收藏清單 (Bookmarks) 與偏好設定管理。"
        ),
    },
    {
        "name": "Events",
        "description": (
            "🎭 **城市活動與展覽目錄 (Event Catalog)**\n\n"
            "支援一般城市活動（文博會、煙火節、市集）與技術社群活動（DevJam、AI 工作坊、Luma/Accupass 小聚）檢索。"
        ),
    },
    {
        "name": "Crowd Density & Heatmap",
        "description": (
            "👥 **即時人潮熱度與地圖圖層 (Crowd Flux & Heatmap)**\n\n"
            "提供 Google Maps JavaScript API HeatmapLayer 所需之熱力圖座標權重點，以及各場館擁擠度等級與排隊時間。"
        ),
    },
    {
        "name": "Microclimate & Solar",
        "description": (
            "☀️ **微氣候與 Google Solar 遮蔽分析 (Weather & Solar Comfort)**\n\n"
            "提供目標座標之溫度、體感溫度、紫外線 (UV) 指數、日照輻射量 (W/m²) 與防曬遮蔭建議。"
        ),
    },
    {
        "name": "Health & Monitoring",
        "description": (
            "💓 **Google Cloud Run 存活與就緒探針 (Liveness & Readiness Probes)**\n\n"
            "用於 GCP Load Balancer 與 Cloud Run 實例健康檢查。"
        ),
    },
]

app = FastAPI(
    title="🧭 SideQuest API - 智慧城市 Agentic 活動與人流疏導決策系統",
    description=r"""
# 🌟 SideQuest Backend API

> **Google DevJam 2026: Agent X 智慧城市｜城市活動探索與人流分散 Agent**

SideQuest 是一個以 **Google Gemini 3.7 Flash / Vertex AI** 為 Agentic 大腦，串聯 **Google Maps Platform (Places, Routes, Solar, Weather)** 與 **Google Cloud Firestore** 的智慧城市決策後端系統，完整符合 PRD MVP 規範。

---

### 🚀 核心亮點（PRD 100% 實現）：
- **🤖 自然語言意圖理解 (PRD 7.3)**：自動萃取指定日期／時間、約會情境、區域、預算上限、人潮與室內偏好；以台北時區篩選活動日期交集後，結構化回傳已理解之條件。
- **👥 人流疏導與 3 大推薦卡片 (PRD 7.4 & 8.3)**：依 35% 興趣、25% 時間、20% 交通遮蔭、10% 預算、10% 舒適度綜合評分，產出【最符合需求】、【舒適替代選擇】與【特色探索選擇】。
- **🔄 多輪對話條件調整 (PRD 7.6)**：支援「第二個太遠」「只看免費」「改成室內」，保留既有條件並給予一句話調整摘要。
- **👤 4 大 Persona 模擬登入與收藏 (PRD 7.1)**：提供週末探索者、技術極客、避開人潮者與親子家長免密碼 Demo Login 及個人收藏夾。
- **☀️ 微氣候與捷運遮蔭路徑 (PRD 10)**：結合高溫、UV 與捷運地下街連通率，提供最佳抗熱路線。
""",
    version="0.1.0",
    openapi_tags=OPENAPI_TAGS,
    docs_url="/docs",
    redoc_url=None,
    openapi_url="/openapi.json",
    swagger_ui_parameters={
        "docExpansion": "list",
        "defaultModelsExpandDepth": 2,
        "displayRequestDuration": True,
        "filter": True,
        "tryItOutEnabled": True,
        "persistAuthorization": True,
    },
    lifespan=lifespan,
)

# CORS Configuration (Configured for localhost, LAN access, and Cloud Run)
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"^https?://.*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """Add execution time and request logging middleware."""
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = f"{process_time * 1000:.2f}ms"
    return response


# Include Health check endpoints at root level and API v1 prefix
app.include_router(health_router)
app.include_router(health_router, prefix=settings.API_V1_PREFIX)

# Include API v1 Routes
app.include_router(agent_router, prefix=settings.API_V1_PREFIX)
app.include_router(user_router, prefix=settings.API_V1_PREFIX)
app.include_router(events_router, prefix=settings.API_V1_PREFIX)
app.include_router(crowd_router, prefix=settings.API_V1_PREFIX)
app.include_router(weather_router, prefix=settings.API_V1_PREFIX)
app.include_router(routes_router, prefix=settings.API_V1_PREFIX)


@app.get("/", tags=["Root"])
async def root():
    """Root metadata endpoint."""
    return {
        "project": "SideQuest",
        "competition": "Google DevJam 2026 (Agent X 智慧城市)",
        "version": "0.1.0",
        "docs_url": "/docs",
        "healthz_url": "/healthz",
        "endpoints": {
            "agent_stream": f"{settings.API_V1_PREFIX}/agent/chat/stream",
            "agent_quick_prompts": f"{settings.API_V1_PREFIX}/agent/quick-prompts",
            "user_personas": f"{settings.API_V1_PREFIX}/user/personas",
            "events": f"{settings.API_V1_PREFIX}/events",
            "crowd_heatmap": f"{settings.API_V1_PREFIX}/crowd/heatmap",
            "weather": f"{settings.API_V1_PREFIX}/weather/current",
        },
    }
