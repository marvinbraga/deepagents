"""MCP (Model Context Protocol) integration for DeepAgents CLI."""

from typing import TYPE_CHECKING, Any

from deepagents_cli.mcp.loader import load_mcp_config
from deepagents_cli.mcp.manager import (
    MCPManager,
    MCPServerState,
    MCPServerStatus,
    clear_mcp_manager,
    get_mcp_manager,
    set_mcp_manager,
)

if TYPE_CHECKING:
    from deepagents.middleware.mcp import MCPMiddleware

# Global reference to the active MCPMiddleware instance
_mcp_middleware: Any = None


def get_mcp_middleware() -> "MCPMiddleware | None":
    """Get the global MCPMiddleware instance."""
    return _mcp_middleware


def set_mcp_middleware(middleware: "MCPMiddleware | None") -> None:
    """Set the global MCPMiddleware instance."""
    global _mcp_middleware  # noqa: PLW0603
    _mcp_middleware = middleware


__all__ = [
    "MCPManager",
    "MCPServerState",
    "MCPServerStatus",
    "clear_mcp_manager",
    "get_mcp_manager",
    "get_mcp_middleware",
    "load_mcp_config",
    "set_mcp_manager",
    "set_mcp_middleware",
]
