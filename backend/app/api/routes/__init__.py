"""API Routes Submodule."""

from app.api.routes.agent import router as agent_router
from app.api.routes.crowd import router as crowd_router
from app.api.routes.events import router as events_router
from app.api.routes.health import router as health_router
from app.api.routes.routes import router as routes_router
from app.api.routes.user import router as user_router
from app.api.routes.weather import router as weather_router

__all__ = [
    "agent_router",
    "events_router",
    "crowd_router",
    "weather_router",
    "health_router",
    "user_router",
    "routes_router",
]
