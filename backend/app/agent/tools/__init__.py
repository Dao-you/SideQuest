"""Agent Tools Suite for SideQuest."""

from typing import Dict, List
from app.agent.tools.base import BaseTool
from app.agent.tools.event_tool import EventTool
from app.agent.tools.weather_tool import WeatherTool
from app.agent.tools.crowd_tool import CrowdTool
from app.agent.tools.places_tool import PlacesTool
from app.agent.tools.routes_tool import RoutesTool
from app.agent.tools.solar_tool import SolarTool


class ToolRegistry:
    """Manages and registers all available Agent tools."""

    def __init__(self) -> None:
        self._tools: Dict[str, BaseTool] = {}
        self.register(EventTool())
        self.register(WeatherTool())
        self.register(CrowdTool())
        self.register(PlacesTool())
        self.register(RoutesTool())
        self.register(SolarTool())

    def register(self, tool: BaseTool) -> None:
        """Register a tool instance."""
        self._tools[tool.name] = tool

    def get_tool(self, name: str) -> BaseTool:
        """Retrieve tool by name."""
        if name not in self._tools:
            raise KeyError(f"Tool '{name}' is not registered.")
        return self._tools[name]

    def list_tools(self) -> List[BaseTool]:
        """List all registered tools."""
        return list(self._tools.values())

    def get_gemini_declarations(self) -> List[dict]:
        """Get Gemini 2.0 Function Calling declarations."""
        return [tool.to_gemini_tool_declaration() for tool in self._tools.values()]


_tool_registry_instance = None


def get_tool_registry() -> ToolRegistry:
    """Singleton getter for ToolRegistry."""
    global _tool_registry_instance
    if _tool_registry_instance is None:
        _tool_registry_instance = ToolRegistry()
    return _tool_registry_instance


__all__ = [
    "BaseTool",
    "EventTool",
    "WeatherTool",
    "CrowdTool",
    "PlacesTool",
    "RoutesTool",
    "SolarTool",
    "ToolRegistry",
    "get_tool_registry",
]
