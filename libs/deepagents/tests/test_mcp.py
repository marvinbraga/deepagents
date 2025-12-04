"""Unit tests for the MCP (Model Context Protocol) system."""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from langchain_core.tools import BaseTool

from deepagents.mcp.client import MCPClient
from deepagents.mcp.protocol import MCPServerCapabilities, MCPServerConfig, MCPTool
from deepagents.mcp.tool_adapter import MCPToolWrapper, _create_input_model_from_schema, mcp_tool_to_langchain
from deepagents.middleware.mcp import MCPMiddleware


class TestMCPServerConfig:
    """Test MCPServerConfig validation."""

    def test_server_config_creation(self):
        """Test creating a valid MCPServerConfig."""
        config = MCPServerConfig(
            name="test-server",
            command="node",
            args=["server.js"],
            env={"API_KEY": "secret"},
            transport="stdio",
            enabled=True,
        )

        assert config.name == "test-server"
        assert config.command == "node"
        assert config.args == ["server.js"]
        assert config.env == {"API_KEY": "secret"}
        assert config.transport == "stdio"
        assert config.enabled is True

    def test_server_config_defaults(self):
        """Test MCPServerConfig with default values."""
        config = MCPServerConfig(
            name="minimal-server",
            command="python",
        )

        assert config.name == "minimal-server"
        assert config.command == "python"
        assert config.args == []
        assert config.env == {}
        assert config.transport == "stdio"
        assert config.enabled is True

    def test_server_config_invalid_transport(self):
        """Test that invalid transport raises ValueError."""
        with pytest.raises(ValueError, match="Unsupported transport"):
            MCPServerConfig(
                name="test-server",
                command="node",
                transport="http",
            )

    def test_server_config_stdio_only(self):
        """Test that only stdio transport is supported."""
        config = MCPServerConfig(
            name="test-server",
            command="node",
            transport="stdio",
        )

        assert config.transport == "stdio"


class TestMCPClient:
    """Test MCPClient initialization and communication."""

    def test_client_initialization(self):
        """Test creating an MCPClient."""
        config = MCPServerConfig(name="test", command="node")
        client = MCPClient(config)

        assert client.config == config
        assert client._process is None
        assert client._tools == []
        assert client._resources == []
        assert client._connected is False

    def test_client_properties(self):
        """Test client property accessors."""
        config = MCPServerConfig(name="test", command="node")
        client = MCPClient(config)

        assert client.tools == []
        assert client.resources == []
        assert client.capabilities == {}
        assert client.is_connected is False

    @pytest.mark.asyncio
    @patch("asyncio.create_subprocess_exec")
    async def test_client_connect(self, mock_subprocess):
        """Test client connection to server."""
        config = MCPServerConfig(name="test", command="node", args=["server.js"])

        # Mock the subprocess
        mock_process = AsyncMock()
        mock_process.stdin = AsyncMock()
        mock_process.stdout = AsyncMock()
        mock_process.stderr = AsyncMock()
        mock_subprocess.return_value = mock_process

        client = MCPClient(config)

        # Mock the internal methods
        client._initialize = AsyncMock()
        client._fetch_tools = AsyncMock()
        client._fetch_resources = AsyncMock()
        client._reader_task = None

        with patch.object(asyncio, "create_task", return_value=AsyncMock()):
            await client.connect()

        assert client.is_connected is True
        client._initialize.assert_called_once()
        client._fetch_tools.assert_called_once()
        client._fetch_resources.assert_called_once()

    @pytest.mark.asyncio
    async def test_client_connect_already_connected(self):
        """Test connecting when already connected."""
        config = MCPServerConfig(name="test", command="node")
        client = MCPClient(config)
        client._connected = True

        # Should not raise, just log warning
        await client.connect()

        assert client.is_connected is True

    @pytest.mark.asyncio
    async def test_client_disconnect(self):
        """Test client disconnection."""
        config = MCPServerConfig(name="test", command="node")
        client = MCPClient(config)

        # Setup mock process
        mock_process = AsyncMock()
        mock_process.returncode = None
        mock_process.terminate = Mock()
        mock_process.wait = AsyncMock()

        client._process = mock_process
        client._connected = True
        client._send_notification = AsyncMock()

        await client.disconnect()

        assert client.is_connected is False
        assert client._process is None
        client._send_notification.assert_called_once_with("shutdown", {})
        mock_process.terminate.assert_called_once()

    @pytest.mark.asyncio
    async def test_call_tool(self):
        """Test calling an MCP tool."""
        config = MCPServerConfig(name="test", command="node")
        client = MCPClient(config)
        client._connected = True

        # Mock _send_request
        client._send_request = AsyncMock(return_value={"content": [{"type": "text", "text": "Result"}]})

        result = await client.call_tool("test_tool", {"arg1": "value1"})

        assert result == [{"type": "text", "text": "Result"}]
        client._send_request.assert_called_once_with(
            "tools/call",
            {"name": "test_tool", "arguments": {"arg1": "value1"}},
        )

    @pytest.mark.asyncio
    async def test_call_tool_not_connected(self):
        """Test calling tool when not connected raises error."""
        config = MCPServerConfig(name="test", command="node")
        client = MCPClient(config)

        with pytest.raises(RuntimeError, match="Not connected"):
            await client.call_tool("test_tool")

    @pytest.mark.asyncio
    async def test_read_resource(self):
        """Test reading an MCP resource."""
        config = MCPServerConfig(name="test", command="node")
        client = MCPClient(config)
        client._connected = True

        # Mock _send_request
        client._send_request = AsyncMock(return_value={"contents": [{"type": "text", "text": "Resource content"}]})

        result = await client.read_resource("file:///test.txt")

        assert result == [{"type": "text", "text": "Resource content"}]
        client._send_request.assert_called_once_with(
            "resources/read",
            {"uri": "file:///test.txt"},
        )

    @pytest.mark.asyncio
    async def test_read_resource_not_connected(self):
        """Test reading resource when not connected raises error."""
        config = MCPServerConfig(name="test", command="node")
        client = MCPClient(config)

        with pytest.raises(RuntimeError, match="Not connected"):
            await client.read_resource("file:///test.txt")

    @pytest.mark.asyncio
    async def test_write_message(self):
        """Test writing message to server."""
        config = MCPServerConfig(name="test", command="node")
        client = MCPClient(config)

        # Mock process with stdin
        mock_stdin = AsyncMock()
        mock_process = AsyncMock()
        mock_process.stdin = mock_stdin
        client._process = mock_process

        message = {"jsonrpc": "2.0", "method": "test", "params": {}}
        await client._write_message(message)

        # Check that message was written with Content-Length header
        mock_stdin.write.assert_called_once()
        written_data = mock_stdin.write.call_args[0][0]

        assert b"Content-Length:" in written_data
        assert b"test" in written_data

    @pytest.mark.asyncio
    async def test_handle_message_response(self):
        """Test handling a response message."""
        config = MCPServerConfig(name="test", command="node")
        client = MCPClient(config)

        # Create a pending request
        future = asyncio.Future()
        client._pending_requests[1] = future

        # Handle a successful response
        message = {"jsonrpc": "2.0", "id": 1, "result": {"data": "test"}}
        await client._handle_message(message)

        assert future.done()
        assert future.result() == {"data": "test"}

    @pytest.mark.asyncio
    async def test_handle_message_error(self):
        """Test handling an error message."""
        config = MCPServerConfig(name="test", command="node")
        client = MCPClient(config)

        # Create a pending request
        future = asyncio.Future()
        client._pending_requests[1] = future

        # Handle an error response
        message = {"jsonrpc": "2.0", "id": 1, "error": {"message": "Test error"}}
        await client._handle_message(message)

        assert future.done()
        with pytest.raises(RuntimeError, match="Test error"):
            future.result()


class TestMCPToolAdapter:
    """Test MCP tool to LangChain conversion."""

    def test_create_input_model_simple(self):
        """Test creating input model from simple schema."""
        schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "The name"},
                "age": {"type": "integer", "description": "The age"},
            },
            "required": ["name"],
        }

        model = _create_input_model_from_schema("test_tool", schema)

        # Check that model has the right fields
        assert hasattr(model, "model_fields")
        assert "name" in model.model_fields
        assert "age" in model.model_fields

    def test_create_input_model_with_array(self):
        """Test creating input model with array types."""
        schema = {
            "type": "object",
            "properties": {
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of tags",
                },
            },
        }

        model = _create_input_model_from_schema("test_tool", schema)

        assert hasattr(model, "model_fields")
        assert "tags" in model.model_fields

    def test_create_input_model_empty(self):
        """Test creating input model with no properties."""
        schema = {"type": "object", "properties": {}}

        model = _create_input_model_from_schema("test_tool", schema)

        # Should have a dummy field
        assert hasattr(model, "model_fields")
        assert "dummy_field" in model.model_fields

    def test_mcp_tool_to_langchain(self):
        """Test converting MCP tool to LangChain tool."""
        config = MCPServerConfig(name="test", command="node")
        client = MCPClient(config)

        mcp_tool: MCPTool = {
            "name": "test_tool",
            "description": "A test tool",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "input": {"type": "string", "description": "Input text"},
                },
                "required": ["input"],
            },
        }

        langchain_tool = mcp_tool_to_langchain(client, mcp_tool)

        assert isinstance(langchain_tool, BaseTool)
        assert langchain_tool.name == "test_tool"
        assert langchain_tool.description == "A test tool"

    @pytest.mark.asyncio
    async def test_mcp_tool_wrapper_arun(self):
        """Test MCPToolWrapper async execution."""
        config = MCPServerConfig(name="test", command="node")
        client = MCPClient(config)

        # Mock call_tool
        client.call_tool = AsyncMock(return_value=[{"type": "text", "text": "Success"}])

        mcp_tool: MCPTool = {
            "name": "test_tool",
            "description": "A test tool",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "input": {"type": "string"},
                },
            },
        }

        wrapper = MCPToolWrapper(client=client, mcp_tool=mcp_tool)
        result = await wrapper._arun(input="test")

        assert "Success" in result
        client.call_tool.assert_called_once()

    def test_mcp_tool_wrapper_run_not_supported(self):
        """Test that sync run raises NotImplementedError."""
        config = MCPServerConfig(name="test", command="node")
        client = MCPClient(config)

        mcp_tool: MCPTool = {
            "name": "test_tool",
            "description": "A test tool",
            "inputSchema": {"type": "object", "properties": {}},
        }

        wrapper = MCPToolWrapper(client=client, mcp_tool=mcp_tool)

        with pytest.raises(NotImplementedError, match="async-only"):
            wrapper._run()


class TestMCPMiddleware:
    """Test MCPMiddleware integration."""

    def test_middleware_initialization(self):
        """Test creating MCPMiddleware."""
        config = MCPServerConfig(name="test", command="node")
        middleware = MCPMiddleware(servers=[config])

        assert len(middleware.server_configs) == 1
        assert middleware.server_configs[0].name == "test"
        assert middleware._initialized is False

    def test_middleware_filters_disabled_servers(self):
        """Test that disabled servers are filtered out."""
        config1 = MCPServerConfig(name="enabled", command="node", enabled=True)
        config2 = MCPServerConfig(name="disabled", command="node", enabled=False)

        middleware = MCPMiddleware(servers=[config1, config2])

        assert len(middleware.server_configs) == 1
        assert middleware.server_configs[0].name == "enabled"

    @pytest.mark.asyncio
    async def test_middleware_initialize(self):
        """Test middleware initialization."""
        config = MCPServerConfig(name="test", command="node")
        middleware = MCPMiddleware(servers=[config], auto_connect=False)

        # Mock client connection
        with patch.object(MCPClient, "connect", new_callable=AsyncMock) as mock_connect:
            with patch.object(MCPClient, "__init__", return_value=None):
                mock_client = Mock(spec=MCPClient)
                mock_client.tools = []
                mock_client.resources = []

                with patch("deepagents.middleware.mcp.MCPClient", return_value=mock_client):
                    await middleware.initialize()

        assert middleware._initialized is True

    @pytest.mark.asyncio
    async def test_middleware_shutdown(self):
        """Test middleware shutdown."""
        config = MCPServerConfig(name="test", command="node")
        middleware = MCPMiddleware(servers=[config], auto_connect=False)

        # Setup a mock client
        mock_client = AsyncMock(spec=MCPClient)
        middleware.clients["test"] = mock_client
        middleware._initialized = True

        await middleware.shutdown()

        mock_client.disconnect.assert_called_once()
        assert middleware._initialized is False
        assert len(middleware.clients) == 0

    def test_get_tools_not_initialized(self):
        """Test getting tools when not initialized."""
        config = MCPServerConfig(name="test", command="node")
        middleware = MCPMiddleware(servers=[config], auto_connect=False)

        tools = middleware.get_tools()

        assert tools == []

    def test_get_tools(self):
        """Test getting tools from connected servers."""
        config = MCPServerConfig(name="test", command="node")
        middleware = MCPMiddleware(servers=[config], auto_connect=False)
        middleware._initialized = True

        # Create mock client with tools
        mock_client = Mock(spec=MCPClient)
        mock_client.tools = [
            {
                "name": "tool1",
                "description": "First tool",
                "inputSchema": {"type": "object", "properties": {}},
            }
        ]

        middleware.clients["test"] = mock_client

        tools = middleware.get_tools()

        assert len(tools) == 1
        assert isinstance(tools[0], BaseTool)

    def test_enhance_tools(self):
        """Test enhancing existing tools with MCP tools."""
        config = MCPServerConfig(name="test", command="node")
        middleware = MCPMiddleware(servers=[config], auto_connect=False)
        middleware._initialized = True

        # Create mock client
        mock_client = Mock(spec=MCPClient)
        mock_client.tools = [
            {
                "name": "mcp_tool",
                "description": "MCP tool",
                "inputSchema": {"type": "object", "properties": {}},
            }
        ]
        middleware.clients["test"] = mock_client

        # Create existing tools
        existing_tool = Mock(spec=BaseTool)
        existing_tool.name = "existing_tool"

        enhanced = middleware.enhance_tools([existing_tool])

        assert len(enhanced) == 2
        assert enhanced[0] == existing_tool

    @pytest.mark.asyncio
    async def test_read_resource(self):
        """Test reading a resource from a server."""
        config = MCPServerConfig(name="test", command="node")
        middleware = MCPMiddleware(servers=[config], auto_connect=False)

        # Setup mock client
        mock_client = AsyncMock(spec=MCPClient)
        mock_client.read_resource.return_value = [{"type": "text", "text": "Content"}]
        middleware.clients["test"] = mock_client

        result = await middleware.read_resource("test", "file:///test.txt")

        assert result == [{"type": "text", "text": "Content"}]
        mock_client.read_resource.assert_called_once_with("file:///test.txt")

    @pytest.mark.asyncio
    async def test_read_resource_server_not_connected(self):
        """Test reading resource from non-connected server raises error."""
        config = MCPServerConfig(name="test", command="node")
        middleware = MCPMiddleware(servers=[config], auto_connect=False)

        with pytest.raises(ValueError, match="not connected"):
            await middleware.read_resource("nonexistent", "file:///test.txt")

    def test_list_resources(self):
        """Test listing resources from all servers."""
        config = MCPServerConfig(name="test", command="node")
        middleware = MCPMiddleware(servers=[config], auto_connect=False)

        # Setup mock client
        mock_client = Mock(spec=MCPClient)
        mock_client.resources = [
            {
                "uri": "file:///test.txt",
                "name": "test.txt",
                "description": "A test file",
                "mimeType": "text/plain",
            }
        ]
        middleware.clients["test"] = mock_client

        resources = middleware.list_resources()

        assert "test" in resources
        assert len(resources["test"]) == 1
        assert resources["test"][0]["uri"] == "file:///test.txt"

    def test_get_system_prompt_addition(self):
        """Test generating system prompt addition."""
        config = MCPServerConfig(name="test", command="node")
        middleware = MCPMiddleware(servers=[config], auto_connect=False)

        # Setup mock client
        mock_client = Mock(spec=MCPClient)
        mock_client.tools = [
            {
                "name": "tool1",
                "description": "First tool",
                "inputSchema": {},
            }
        ]
        mock_client.resources = [
            {
                "uri": "file:///test.txt",
                "name": "test.txt",
                "description": "A test file",
            }
        ]
        middleware.clients["test"] = mock_client

        prompt = middleware.get_system_prompt_addition()

        assert "test" in prompt
        assert "tool1" in prompt
        assert "test.txt" in prompt

    def test_get_system_prompt_addition_no_clients(self):
        """Test system prompt when no clients are connected."""
        middleware = MCPMiddleware(servers=[], auto_connect=False)

        prompt = middleware.get_system_prompt_addition()

        assert prompt == ""

    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Test using MCPMiddleware as async context manager."""
        config = MCPServerConfig(name="test", command="node")
        middleware = MCPMiddleware(servers=[config], auto_connect=True)

        middleware.initialize = AsyncMock()
        middleware.shutdown = AsyncMock()

        async with middleware as m:
            assert m == middleware
            middleware.initialize.assert_called_once()

        middleware.shutdown.assert_called_once()
