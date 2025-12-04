"""MCP (Model Context Protocol) integration for DeepAgents."""

from deepagents.mcp.client import MCPClient
from deepagents.mcp.protocol import (
    MCPResource,
    MCPServerCapabilities,
    MCPServerConfig,
    MCPTool,
    MCPToolInput,
)
from deepagents.mcp.tool_adapter import mcp_tool_to_langchain

__all__ = [
    "MCPClient",
    "MCPResource",
    "MCPServerCapabilities",
    "MCPServerConfig",
    "MCPTool",
    "MCPToolInput",
    "mcp_tool_to_langchain",
]
