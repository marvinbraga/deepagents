"""MCP Manager for async initialization and status tracking."""

import asyncio
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from deepagents.mcp.protocol import MCPServerConfig

logger = logging.getLogger(__name__)


class MCPServerStatus(Enum):
    """Status of an MCP server connection."""

    PENDING = "pending"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"
    DISABLED = "disabled"


@dataclass
class MCPServerState:
    """State of an individual MCP server."""

    config: MCPServerConfig
    status: MCPServerStatus = MCPServerStatus.PENDING
    error_message: str | None = None
    tool_count: int = 0
    connect_time: float | None = None


@dataclass
class MCPManager:
    """Manages MCP server connections with async initialization.

    This class handles:
    - Async background initialization of MCP servers
    - Status tracking for each server (pending/connecting/connected/error)
    - Error persistence for display in /mcp command
    - Graceful handling of connection failures
    """

    servers: dict[str, MCPServerState] = field(default_factory=dict)
    middleware: Any = None  # MCPMiddleware instance
    _init_task: asyncio.Task | None = None
    _initialized: bool = False

    @classmethod
    def from_configs(cls, configs: list[MCPServerConfig]) -> "MCPManager":
        """Create manager from list of server configs.

        Args:
            configs: List of MCP server configurations

        Returns:
            MCPManager instance with servers initialized to pending state
        """
        manager = cls()
        for config in configs:
            status = MCPServerStatus.PENDING if config.enabled else MCPServerStatus.DISABLED
            manager.servers[config.name] = MCPServerState(config=config, status=status)
        return manager

    @property
    def enabled_servers(self) -> list[MCPServerState]:
        """Get list of enabled servers."""
        return [s for s in self.servers.values() if s.config.enabled]

    @property
    def connected_servers(self) -> list[MCPServerState]:
        """Get list of connected servers."""
        return [s for s in self.servers.values() if s.status == MCPServerStatus.CONNECTED]

    @property
    def failed_servers(self) -> list[MCPServerState]:
        """Get list of servers that failed to connect."""
        return [s for s in self.servers.values() if s.status == MCPServerStatus.ERROR]

    @property
    def pending_servers(self) -> list[MCPServerState]:
        """Get list of servers still connecting."""
        return [
            s
            for s in self.servers.values()
            if s.status in (MCPServerStatus.PENDING, MCPServerStatus.CONNECTING)
        ]

    @property
    def total_tools(self) -> int:
        """Get total number of tools from connected servers."""
        return sum(s.tool_count for s in self.connected_servers)

    @property
    def is_initializing(self) -> bool:
        """Check if initialization is still in progress."""
        return self._init_task is not None and not self._init_task.done()

    def start_async_init(self, on_complete: asyncio.Future | None = None) -> asyncio.Task:
        """Start async initialization of all enabled servers.

        This method starts the initialization in the background and returns
        immediately. Use `is_initializing` to check status or await the
        returned task.

        Args:
            on_complete: Optional future to set when initialization completes

        Returns:
            The initialization task
        """
        if self._init_task is not None:
            return self._init_task

        self._init_task = asyncio.create_task(self._initialize_all(on_complete))
        return self._init_task

    async def _initialize_all(self, on_complete: asyncio.Future | None = None) -> None:
        """Initialize all enabled servers concurrently.

        Args:
            on_complete: Optional future to set when done
        """
        enabled = self.enabled_servers
        if not enabled:
            self._initialized = True
            if on_complete:
                on_complete.set_result(None)
            return

        # Mark all as connecting
        for server in enabled:
            server.status = MCPServerStatus.CONNECTING

        # Initialize each server concurrently with individual error handling
        tasks = [self._initialize_server(server) for server in enabled]
        await asyncio.gather(*tasks, return_exceptions=True)

        # Create middleware with connected servers only
        connected_configs = [s.config for s in self.connected_servers]
        if connected_configs:
            try:
                from deepagents.middleware.mcp import MCPMiddleware

                # Create middleware but don't auto-connect (we already connected)
                self.middleware = MCPMiddleware(servers=connected_configs, auto_connect=False)
                # Manually set connected clients
                # Note: This requires the middleware to expose connected clients
            except Exception:
                logger.exception("Failed to create MCP middleware")

        self._initialized = True
        logger.info(
            "MCP initialization complete: %d connected, %d failed",
            len(self.connected_servers),
            len(self.failed_servers),
        )

        if on_complete:
            on_complete.set_result(None)

    async def _initialize_server(self, server: MCPServerState) -> None:
        """Initialize a single MCP server with error handling.

        Args:
            server: The server state to initialize
        """
        import time

        start_time = time.time()

        try:
            from deepagents.mcp.client import MCPClient

            client = MCPClient(server.config)
            await asyncio.wait_for(client.connect(), timeout=30.0)

            server.status = MCPServerStatus.CONNECTED
            server.tool_count = len(client.tools)
            server.connect_time = time.time() - start_time
            server.error_message = None

            logger.info(
                "Connected to MCP server %s: %d tools in %.2fs",
                server.config.name,
                server.tool_count,
                server.connect_time,
            )

            # Disconnect for now - middleware will reconnect
            await client.disconnect()

        except TimeoutError:
            server.status = MCPServerStatus.ERROR
            server.error_message = "Connection timed out (30s)"
            logger.warning("MCP server %s timed out", server.config.name)

        except Exception as e:  # noqa: BLE001
            server.status = MCPServerStatus.ERROR
            # Extract meaningful error message
            error_str = str(e)
            max_error_len = 100
            if "timed out" in error_str.lower():
                server.error_message = "Connection timed out"
            elif "not found" in error_str.lower():
                server.error_message = "Command not found"
            elif "permission" in error_str.lower():
                server.error_message = "Permission denied"
            else:
                # Truncate long error messages
                server.error_message = (
                    error_str[:max_error_len] if len(error_str) > max_error_len else error_str
                )

            logger.warning("MCP server %s failed: %s", server.config.name, server.error_message)

    def get_status_summary(self) -> str:
        """Get a brief status summary string.

        Returns:
            Summary like "3/5 connected" or "initializing..."
        """
        if self.is_initializing:
            connecting = len(
                [s for s in self.servers.values() if s.status == MCPServerStatus.CONNECTING]
            )
            return f"initializing ({connecting} pending)..."

        connected = len(self.connected_servers)
        total = len(self.enabled_servers)

        if connected == total and total > 0:
            return f"{connected} connected, {self.total_tools} tools"
        if connected > 0:
            return f"{connected}/{total} connected"
        if total > 0:
            return "all failed"
        return "none configured"

    async def shutdown(self) -> None:
        """Shutdown all connected servers."""
        import contextlib

        if self._init_task and not self._init_task.done():
            self._init_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._init_task

        # Middleware handles disconnection
        if self.middleware:
            try:
                await self.middleware.shutdown()
            except Exception:
                logger.exception("Error shutting down MCP middleware")


# Global manager instance
_manager: MCPManager | None = None


def get_mcp_manager() -> MCPManager | None:
    """Get the global MCP manager instance."""
    return _manager


def set_mcp_manager(manager: MCPManager) -> None:
    """Set the global MCP manager instance."""
    global _manager  # noqa: PLW0603
    _manager = manager


def clear_mcp_manager() -> None:
    """Clear the global MCP manager instance."""
    global _manager  # noqa: PLW0603
    _manager = None
