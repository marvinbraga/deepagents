"""Middleware for integrating MCP servers with DeepAgents."""

import logging
from collections.abc import Sequence
from typing import Any

from langchain.agents.middleware.types import AgentMiddleware, ModelRequest, ModelResponse
from langchain_core.messages import BaseMessage
from langchain_core.tools import BaseTool

from deepagents.mcp.client import MCPClient
from deepagents.mcp.protocol import MCPServerConfig
from deepagents.mcp.tool_adapter import mcp_tool_to_langchain

logger = logging.getLogger(__name__)


class MCPMiddleware(AgentMiddleware):
    """Middleware for managing MCP server connections and providing MCP tools.

    This middleware handles:
    - Connecting to multiple MCP servers
    - Converting MCP tools to LangChain tools
    - Managing server lifecycle
    - Providing resource access
    - Adding system prompt information about connected servers
    """

    def __init__(
        self,
        servers: list[MCPServerConfig],
        *,
        auto_connect: bool = True,
    ) -> None:
        """Initialize the MCP middleware.

        Args:
            servers: List of MCP server configurations
            auto_connect: Whether to automatically connect during initialization
        """
        self.server_configs = [s for s in servers if s.enabled]
        self.clients: dict[str, MCPClient] = {}
        self._initialized = False
        self._auto_connect = auto_connect

    async def initialize(self) -> None:
        """Connect to all enabled MCP servers.

        This should be called before using the middleware to establish
        connections to all configured servers.
        """
        if self._initialized:
            logger.warning("MCP middleware already initialized")
            return

        logger.info("Initializing MCP middleware with %d servers", len(self.server_configs))

        for config in self.server_configs:
            try:
                client = MCPClient(config)
                await client.connect()
                self.clients[config.name] = client
                logger.info("Connected to MCP server: %s (%d tools, %d resources)", config.name, len(client.tools), len(client.resources))
            except Exception as e:
                logger.exception("Failed to connect to MCP server %s: %s", config.name, e)

        self._initialized = True

    async def shutdown(self) -> None:
        """Disconnect from all MCP servers.

        This should be called when the middleware is no longer needed
        to clean up server connections.
        """
        logger.info("Shutting down MCP middleware")

        for name, client in self.clients.items():
            try:
                await client.disconnect()
                logger.info("Disconnected from MCP server: %s", name)
            except Exception as e:
                logger.exception("Error disconnecting from MCP server %s: %s", name, e)

        self.clients.clear()
        self._initialized = False

    def get_tools(self) -> list[BaseTool]:
        """Get all MCP tools as LangChain tools.

        Returns:
            List of LangChain tools wrapping all MCP tools from connected servers
        """
        if not self._initialized:
            logger.warning("MCP middleware not initialized, returning empty tool list")
            return []

        tools: list[BaseTool] = []

        for server_name, client in self.clients.items():
            for mcp_tool in client.tools:
                try:
                    langchain_tool = mcp_tool_to_langchain(client, mcp_tool)
                    tools.append(langchain_tool)
                    logger.debug("Added tool %s from server %s", mcp_tool["name"], server_name)
                except Exception as e:
                    logger.exception("Failed to convert MCP tool %s from server %s: %s", mcp_tool["name"], server_name, e)

        logger.info("Providing %d MCP tools from %d servers", len(tools), len(self.clients))
        return tools

    def enhance_tools(self, existing_tools: Sequence[BaseTool]) -> list[BaseTool]:
        """Add MCP tools to an existing list of tools.

        Args:
            existing_tools: The existing tools to enhance

        Returns:
            Combined list of existing tools and MCP tools
        """
        mcp_tools = self.get_tools()
        return [*existing_tools, *mcp_tools]

    async def read_resource(self, server_name: str, uri: str) -> Any:
        """Read a resource from a specific MCP server.

        Args:
            server_name: The name of the server to read from
            uri: The URI of the resource to read

        Returns:
            The resource content

        Raises:
            ValueError: If the server is not connected
        """
        if server_name not in self.clients:
            msg = f"Server {server_name} is not connected"
            raise ValueError(msg)

        client = self.clients[server_name]
        return await client.read_resource(uri)

    def list_resources(self) -> dict[str, list[dict[str, Any]]]:
        """List all available resources from all connected servers.

        Returns:
            Dictionary mapping server names to their resource lists
        """
        resources: dict[str, list[dict[str, Any]]] = {}

        for server_name, client in self.clients.items():
            resources[server_name] = [
                {
                    "uri": resource["uri"],
                    "name": resource["name"],
                    "description": resource.get("description", ""),
                    "mimeType": resource.get("mimeType", ""),
                }
                for resource in client.resources
            ]

        return resources

    def get_system_prompt_addition(self) -> str:
        """Get system prompt text describing connected MCP servers.

        This can be added to the agent's system prompt to inform it
        about available MCP tools and resources.

        Returns:
            Formatted text describing connected servers and their capabilities
        """
        if not self.clients:
            return ""

        lines = ["You have access to the following MCP (Model Context Protocol) servers:\n"]

        for server_name, client in self.clients.items():
            lines.append(f"\n## {server_name}")

            if client.tools:
                lines.append(f"\nTools ({len(client.tools)}):")
                for tool in client.tools[:5]:  # Show first 5 tools
                    tool_name = tool["name"]
                    tool_desc = tool.get("description", "No description")
                    lines.append(f"  - {tool_name}: {tool_desc}")
                if len(client.tools) > 5:
                    lines.append(f"  ... and {len(client.tools) - 5} more tools")

            if client.resources:
                lines.append(f"\nResources ({len(client.resources)}):")
                for resource in client.resources[:3]:  # Show first 3 resources
                    resource_name = resource["name"]
                    resource_uri = resource["uri"]
                    resource_desc = resource.get("description", "No description")
                    lines.append(f"  - {resource_name} ({resource_uri}): {resource_desc}")
                if len(client.resources) > 3:
                    lines.append(f"  ... and {len(client.resources) - 3} more resources")

        return "\n".join(lines)

    async def on_model_request(self, request: ModelRequest) -> ModelRequest:
        """Process a model request before it's sent to the model.

        This hook can be used to modify requests, but currently passes through unchanged.

        Args:
            request: The model request

        Returns:
            The possibly modified request
        """
        # Auto-connect on first request if not initialized
        if not self._initialized and self._auto_connect:
            await self.initialize()

        return request

    async def on_model_response(self, response: ModelResponse) -> ModelResponse:
        """Process a model response before it's returned.

        This hook can be used to modify responses, but currently passes through unchanged.

        Args:
            response: The model response

        Returns:
            The possibly modified response
        """
        return response

    async def on_messages_update(self, messages: list[BaseMessage]) -> list[BaseMessage]:
        """Process messages before they're added to state.

        This hook can be used to modify messages, but currently passes through unchanged.

        Args:
            messages: The messages to process

        Returns:
            The possibly modified messages
        """
        return messages

    async def __aenter__(self) -> "MCPMiddleware":
        """Async context manager entry.

        Returns:
            Self
        """
        if self._auto_connect:
            await self.initialize()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit.

        Args:
            exc_type: Exception type if an error occurred
            exc_val: Exception value if an error occurred
            exc_tb: Exception traceback if an error occurred
        """
        await self.shutdown()
