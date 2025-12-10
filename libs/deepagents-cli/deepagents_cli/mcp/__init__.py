"""MCP (Model Context Protocol) integration for DeepAgents CLI."""

from deepagents_cli.mcp.loader import load_mcp_config
from deepagents_cli.mcp.manager import (
    MCPManager,
    MCPServerState,
    MCPServerStatus,
    clear_mcp_manager,
    get_mcp_manager,
    set_mcp_manager,
)

__all__ = [
    "load_mcp_config",
    "MCPManager",
    "MCPServerState",
    "MCPServerStatus",
    "get_mcp_manager",
    "set_mcp_manager",
    "clear_mcp_manager",
]
