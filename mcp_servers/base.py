"""
MCP Server Base — Model Context Protocol server implementation.

Implements the MCP pattern: each server exposes a set of tools via a
standardized interface. Agents discover tools via list_tools(), then
call them via call_tool(). This replaces bespoke REST wrappers (the NxM problem).

Transport: in-process function calls (stdio equivalent for local dev).
For production, these servers can be exposed as SSE/HTTP endpoints.
"""

from __future__ import annotations

import inspect
import json
from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class MCPToolSchema:
    """JSON Schema for a single MCP tool input — used for the handshake/list_tools."""

    name: str
    description: str
    input_schema: dict[str, Any]
    output_description: str = ""


@dataclass
class MCPToolResult:
    """Structured result from an MCP tool call."""

    tool_name: str
    content: Any
    is_error: bool = False
    error_message: str = ""

    def to_dict(self) -> dict:
        return {
            "tool": self.tool_name,
            "content": self.content,
            "is_error": self.is_error,
            "error": self.error_message if self.is_error else None,
        }


class MCPServer:
    """
    Base MCP Server.

    Subclasses register tools with the @tool() decorator.
    Agents discover tools via list_tools() and invoke them via call_tool().

    This models the MCP handshake:
      1. Client calls list_tools()  → discovers available tool schemas
      2. Client calls call_tool()   → executes a tool and gets structured result
    """

    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        self._tools: dict[str, Callable] = {}
        self._schemas: dict[str, MCPToolSchema] = {}

        # Auto-register any methods decorated with @tool
        for attr_name in dir(self):
            method = getattr(self, attr_name, None)
            if callable(method) and hasattr(method, "_mcp_tool_schema"):
                schema: MCPToolSchema = method._mcp_tool_schema
                self._tools[schema.name] = method
                self._schemas[schema.name] = schema

    def list_tools(self) -> list[MCPToolSchema]:
        """MCP handshake: return all available tool schemas."""
        return list(self._schemas.values())

    async def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> MCPToolResult:
        """MCP tool invocation — routes to the registered handler."""
        if tool_name not in self._tools:
            return MCPToolResult(
                tool_name=tool_name,
                content=None,
                is_error=True,
                error_message=f"Tool '{tool_name}' not found. Available: {list(self._tools.keys())}",
            )
        try:
            fn = self._tools[tool_name]
            if inspect.iscoroutinefunction(fn):
                result = await fn(**arguments)
            else:
                result = fn(**arguments)
            return MCPToolResult(tool_name=tool_name, content=result)
        except Exception as e:
            return MCPToolResult(
                tool_name=tool_name,
                content=None,
                is_error=True,
                error_message=str(e),
            )


def tool(
    name: str,
    description: str,
    input_schema: dict[str, Any],
    output_description: str = "",
):
    """
    Decorator to register a method as an MCP tool.

    Usage:
        @tool(
            name="search_wikipedia",
            description="Search Wikipedia for a topic",
            input_schema={"query": {"type": "string", "description": "Search query"}}
        )
        async def search_wikipedia(self, query: str) -> str:
            ...
    """

    def decorator(fn: Callable) -> Callable:
        schema = MCPToolSchema(
            name=name,
            description=description,
            input_schema=input_schema,
            output_description=output_description,
        )
        fn._mcp_tool_schema = schema
        return fn

    return decorator


class MCPClient:
    """
    Lightweight MCP client used by agents to call MCP server tools.

    In production this would connect over HTTP/SSE. In our architecture,
    it holds a direct reference to the server instance (stdio-equivalent).
    """

    def __init__(self, server: MCPServer):
        self._server = server

    def list_tools(self) -> list[MCPToolSchema]:
        return self._server.list_tools()

    async def call(self, tool_name: str, **kwargs) -> Any:
        """Call a tool and return its content, or raise on error."""
        result = await self._server.call_tool(tool_name, kwargs)
        if result.is_error:
            raise RuntimeError(f"MCP tool error [{tool_name}]: {result.error_message}")
        return result.content
