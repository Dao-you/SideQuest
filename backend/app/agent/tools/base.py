"""Base Tool Specification and Registration."""

from abc import ABC, abstractmethod
from typing import Any, Dict


class BaseTool(ABC):
    """Abstract Base Class for all SideQuest Agent Tools."""

    name: str
    description: str
    parameters_schema: Dict[str, Any]

    @abstractmethod
    async def execute(self, **kwargs: Any) -> Dict[str, Any]:
        """Execute tool action asynchronously and return structured output."""
        pass

    def to_gemini_tool_declaration(self) -> Dict[str, Any]:
        """Format tool definition for Gemini 2.0 Function Calling."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters_schema,
        }

    def to_mcp_tool_declaration(self) -> Dict[str, Any]:
        """Format tool definition for Model Context Protocol (MCP) servers."""
        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": self.parameters_schema,
        }
