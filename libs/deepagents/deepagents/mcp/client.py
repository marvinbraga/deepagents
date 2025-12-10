"""MCP Client using the official Anthropic MCP SDK."""

import logging
import subprocess
from typing import Any

from deepagents.mcp.protocol import MCPResource, MCPServerCapabilities, MCPServerConfig, MCPTool

logger = logging.getLogger(__name__)


class MCPClient:
    """MCP client that communicates with MCP servers using the official MCP SDK.

    This client wraps the official `mcp` package from Anthropic to provide
    a simplified interface for connecting to MCP servers via stdio transport.
    """

    def __init__(self, config: MCPServerConfig) -> None:
        """Initialize the MCP client.

        Args:
            config: The server configuration
        """
        self.config = config
        self._tools: list[MCPTool] = []
        self._resources: list[MCPResource] = []
        self._capabilities: MCPServerCapabilities = {}
        self._connected = False
        self._session = None
        self._read_stream = None
        self._write_stream = None
        self._context_manager = None

    @property
    def tools(self) -> list[MCPTool]:
        """Get the list of available tools from the server."""
        return self._tools

    @property
    def resources(self) -> list[MCPResource]:
        """Get the list of available resources from the server."""
        return self._resources

    @property
    def capabilities(self) -> MCPServerCapabilities:
        """Get the server capabilities."""
        return self._capabilities

    @property
    def is_connected(self) -> bool:
        """Check if the client is connected to the server."""
        return self._connected

    async def connect(self) -> None:
        """Start the server process, perform handshake, and fetch tools/resources."""
        if self._connected:
            logger.warning("Client already connected to server %s", self.config.name)
            return

        try:
            from mcp import ClientSession, StdioServerParameters
            from mcp.client.stdio import stdio_client

            # Build server parameters - redirect stderr to suppress server logs
            server_params = StdioServerParameters(
                command=self.config.command,
                args=self.config.args,
                env=self.config.env if self.config.env else None,
                stderr=subprocess.DEVNULL,  # Suppress server stderr output
            )

            # Create stdio client context manager
            self._context_manager = stdio_client(server_params)

            # Enter context manager to get streams
            self._read_stream, self._write_stream = await self._context_manager.__aenter__()

            # Create and initialize session
            self._session = ClientSession(self._read_stream, self._write_stream)
            await self._session.__aenter__()

            # Initialize the connection
            result = await self._session.initialize()
            self._capabilities = result.capabilities.model_dump() if result.capabilities else {}

            logger.debug("Server capabilities: %s", self._capabilities)

            # Fetch available tools
            await self._fetch_tools()

            # Fetch available resources
            await self._fetch_resources()

            self._connected = True
            logger.info(
                "Successfully connected to MCP server %s: %d tools, %d resources",
                self.config.name,
                len(self._tools),
                len(self._resources),
            )

        except ImportError as e:
            msg = "MCP SDK not installed. Install with: pip install mcp"
            raise RuntimeError(msg) from e
        except Exception as e:
            logger.exception("Failed to connect to MCP server %s", self.config.name)
            await self.disconnect()
            raise RuntimeError(f"Failed to connect to MCP server {self.config.name}: {e}") from e

    async def disconnect(self) -> None:
        """Terminate the server process and clean up resources."""
        if not self._connected and self._session is None:
            return

        self._connected = False

        # Exit session context
        if self._session:
            try:
                await self._session.__aexit__(None, None, None)
            except Exception as e:
                logger.debug("Error closing session: %s", e)
            self._session = None

        # Exit stdio client context
        if self._context_manager:
            try:
                await self._context_manager.__aexit__(None, None, None)
            except Exception as e:
                logger.debug("Error closing stdio client: %s", e)
            self._context_manager = None

        self._read_stream = None
        self._write_stream = None

        logger.info("Disconnected from MCP server: %s", self.config.name)

    async def call_tool(self, name: str, arguments: dict[str, Any] | None = None) -> Any:
        """Call an MCP tool.

        Args:
            name: The name of the tool to call
            arguments: The arguments to pass to the tool

        Returns:
            The result from the tool invocation

        Raises:
            RuntimeError: If not connected or if the tool call fails
        """
        if not self._connected or not self._session:
            msg = f"Not connected to server {self.config.name}"
            raise RuntimeError(msg)

        try:
            result = await self._session.call_tool(name, arguments or {})
            # Convert result content to list of dicts
            return [
                {"type": content.type, "text": getattr(content, "text", None)}
                for content in result.content
            ]
        except Exception as e:
            logger.exception("Failed to call tool %s on server %s", name, self.config.name)
            raise RuntimeError(f"Failed to call tool {name}: {e}") from e

    async def read_resource(self, uri: str) -> Any:
        """Read an MCP resource.

        Args:
            uri: The URI of the resource to read

        Returns:
            The resource content

        Raises:
            RuntimeError: If not connected or if the resource read fails
        """
        if not self._connected or not self._session:
            msg = f"Not connected to server {self.config.name}"
            raise RuntimeError(msg)

        try:
            result = await self._session.read_resource(uri)
            return [
                {"uri": content.uri, "text": getattr(content, "text", None)}
                for content in result.contents
            ]
        except Exception as e:
            logger.exception("Failed to read resource %s on server %s", uri, self.config.name)
            raise RuntimeError(f"Failed to read resource {uri}: {e}") from e

    async def _fetch_tools(self) -> None:
        """Fetch the list of available tools from the server."""
        if not self._session:
            return

        try:
            result = await self._session.list_tools()
            self._tools = [
                {
                    "name": tool.name,
                    "description": tool.description or "",
                    "inputSchema": tool.inputSchema,
                }
                for tool in result.tools
            ]
            logger.debug("Fetched %d tools from server %s", len(self._tools), self.config.name)
        except Exception as e:
            logger.warning("Failed to fetch tools from server %s: %s", self.config.name, e)
            self._tools = []

    async def _fetch_resources(self) -> None:
        """Fetch the list of available resources from the server."""
        if not self._session:
            return

        try:
            result = await self._session.list_resources()
            self._resources = [
                {
                    "uri": resource.uri,
                    "name": resource.name,
                    "description": getattr(resource, "description", None),
                    "mimeType": getattr(resource, "mimeType", None),
                }
                for resource in result.resources
            ]
            logger.debug("Fetched %d resources from server %s", len(self._resources), self.config.name)
        except Exception as e:
            logger.warning("Failed to fetch resources from server %s: %s", self.config.name, e)
            self._resources = []
