"""MCP Client for JSON-RPC communication via stdio."""

import asyncio
import json
import logging
import os
from collections.abc import Mapping
from typing import Any

from deepagents.mcp.protocol import MCPResource, MCPServerCapabilities, MCPServerConfig, MCPTool

logger = logging.getLogger(__name__)


class MCPClient:
    """MCP client that communicates with MCP servers via JSON-RPC over stdio.

    The protocol uses Content-Length headers similar to LSP (Language Server Protocol).
    Each message is formatted as:
        Content-Length: <bytes>\r\n
        \r\n
        <JSON payload>
    """

    def __init__(self, config: MCPServerConfig) -> None:
        """Initialize the MCP client.

        Args:
            config: The server configuration
        """
        self.config = config
        self._process: asyncio.subprocess.Process | None = None
        self._tools: list[MCPTool] = []
        self._resources: list[MCPResource] = []
        self._capabilities: MCPServerCapabilities = {}
        self._request_id = 0
        self._pending_requests: dict[int, asyncio.Future[Any]] = {}
        self._reader_task: asyncio.Task[None] | None = None
        self._connected = False

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
            # Build environment
            env = os.environ.copy()
            env.update(self.config.env)

            # Start the subprocess
            self._process = await asyncio.create_subprocess_exec(
                self.config.command,
                *self.config.args,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
            )

            # Start the response reader task
            self._reader_task = asyncio.create_task(self._read_responses())

            # Perform initialization handshake
            await self._initialize()

            # Fetch available tools and resources
            await self._fetch_tools()
            await self._fetch_resources()

            self._connected = True
            logger.info("Successfully connected to MCP server: %s", self.config.name)

        except Exception as e:
            logger.exception("Failed to connect to MCP server %s", self.config.name)
            await self.disconnect()
            raise RuntimeError(f"Failed to connect to MCP server {self.config.name}: {e}") from e

    async def disconnect(self) -> None:
        """Terminate the server process and clean up resources."""
        if not self._connected and self._process is None:
            return

        self._connected = False

        # Cancel pending requests
        for future in self._pending_requests.values():
            if not future.done():
                future.cancel()
        self._pending_requests.clear()

        # Cancel reader task
        if self._reader_task and not self._reader_task.done():
            self._reader_task.cancel()
            try:
                await self._reader_task
            except asyncio.CancelledError:
                pass

        # Terminate the process
        if self._process:
            try:
                # Send shutdown notification
                await self._send_notification("shutdown", {})
                await asyncio.sleep(0.1)  # Give it a moment to process

                # Terminate the process
                if self._process.returncode is None:
                    self._process.terminate()
                    try:
                        await asyncio.wait_for(self._process.wait(), timeout=5.0)
                    except asyncio.TimeoutError:
                        logger.warning("Process did not terminate gracefully, killing it")
                        self._process.kill()
                        await self._process.wait()

            except Exception as e:
                logger.exception("Error during disconnect: %s", e)

            self._process = None

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
        if not self._connected:
            msg = f"Not connected to server {self.config.name}"
            raise RuntimeError(msg)

        params = {
            "name": name,
            "arguments": arguments or {},
        }

        try:
            response = await self._send_request("tools/call", params)
            return response.get("content", [])
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
        if not self._connected:
            msg = f"Not connected to server {self.config.name}"
            raise RuntimeError(msg)

        params = {"uri": uri}

        try:
            response = await self._send_request("resources/read", params)
            return response.get("contents", [])
        except Exception as e:
            logger.exception("Failed to read resource %s on server %s", uri, self.config.name)
            raise RuntimeError(f"Failed to read resource {uri}: {e}") from e

    async def _initialize(self) -> None:
        """Perform the initialization handshake with the server."""
        params = {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {
                "name": "deepagents-mcp-client",
                "version": "0.1.0",
            },
        }

        response = await self._send_request("initialize", params)
        self._capabilities = response.get("capabilities", {})
        logger.debug("Server capabilities: %s", self._capabilities)

        # Send initialized notification
        await self._send_notification("notifications/initialized", {})

    async def _fetch_tools(self) -> None:
        """Fetch the list of available tools from the server."""
        if "tools" not in self._capabilities:
            logger.debug("Server %s does not support tools", self.config.name)
            return

        try:
            response = await self._send_request("tools/list", {})
            self._tools = response.get("tools", [])
            logger.debug("Fetched %d tools from server %s", len(self._tools), self.config.name)
        except Exception as e:
            logger.exception("Failed to fetch tools from server %s", self.config.name)
            raise RuntimeError(f"Failed to fetch tools: {e}") from e

    async def _fetch_resources(self) -> None:
        """Fetch the list of available resources from the server."""
        if "resources" not in self._capabilities:
            logger.debug("Server %s does not support resources", self.config.name)
            return

        try:
            response = await self._send_request("resources/list", {})
            self._resources = response.get("resources", [])
            logger.debug("Fetched %d resources from server %s", len(self._resources), self.config.name)
        except Exception as e:
            logger.exception("Failed to fetch resources from server %s", self.config.name)
            raise RuntimeError(f"Failed to fetch resources: {e}") from e

    async def _send_request(self, method: str, params: Mapping[str, Any]) -> Any:
        """Send a JSON-RPC request and wait for the response.

        Args:
            method: The JSON-RPC method name
            params: The parameters for the method

        Returns:
            The result from the response

        Raises:
            RuntimeError: If the request fails
        """
        self._request_id += 1
        request_id = self._request_id

        message = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
            "params": params,
        }

        # Create a future for this request
        future: asyncio.Future[Any] = asyncio.Future()
        self._pending_requests[request_id] = future

        try:
            await self._write_message(message)
            # Wait for the response with a timeout
            return await asyncio.wait_for(future, timeout=30.0)
        except asyncio.TimeoutError as e:
            msg = f"Request {method} timed out"
            raise RuntimeError(msg) from e
        finally:
            self._pending_requests.pop(request_id, None)

    async def _send_notification(self, method: str, params: Mapping[str, Any]) -> None:
        """Send a JSON-RPC notification (no response expected).

        Args:
            method: The JSON-RPC method name
            params: The parameters for the notification
        """
        message = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
        }

        await self._write_message(message)

    async def _write_message(self, message: dict[str, Any]) -> None:
        """Write a message to the server using Content-Length header format.

        Args:
            message: The message to send

        Raises:
            RuntimeError: If the process is not running or stdin is not available
        """
        if not self._process or not self._process.stdin:
            msg = "Process not running or stdin not available"
            raise RuntimeError(msg)

        # Serialize the message
        content = json.dumps(message, ensure_ascii=False)
        content_bytes = content.encode("utf-8")

        # Build the message with Content-Length header
        header = f"Content-Length: {len(content_bytes)}\r\n\r\n"
        full_message = header.encode("utf-8") + content_bytes

        # Write to stdin
        self._process.stdin.write(full_message)
        await self._process.stdin.drain()

        logger.debug("Sent message: %s", message.get("method", message.get("id")))

    async def _read_responses(self) -> None:
        """Continuously read responses from the server."""
        if not self._process or not self._process.stdout:
            return

        try:
            while True:
                # Read the Content-Length header
                header_line = await self._process.stdout.readline()
                if not header_line:
                    break  # EOF

                header = header_line.decode("utf-8").strip()
                if not header.startswith("Content-Length:"):
                    logger.warning("Invalid header: %s", header)
                    continue

                # Extract content length
                try:
                    content_length = int(header.split(":", 1)[1].strip())
                except (ValueError, IndexError) as e:
                    logger.exception("Failed to parse Content-Length: %s", header)
                    continue

                # Read the empty line
                await self._process.stdout.readline()

                # Read the content
                content_bytes = await self._process.stdout.readexactly(content_length)
                content = content_bytes.decode("utf-8")

                # Parse the JSON
                try:
                    message = json.loads(content)
                    await self._handle_message(message)
                except json.JSONDecodeError as e:
                    logger.exception("Failed to parse JSON: %s", content)

        except asyncio.CancelledError:
            logger.debug("Response reader cancelled")
        except Exception as e:
            logger.exception("Error reading responses: %s", e)

    async def _handle_message(self, message: dict[str, Any]) -> None:
        """Handle a message from the server.

        Args:
            message: The JSON-RPC message
        """
        # Check if this is a response to a request
        if "id" in message and message["id"] in self._pending_requests:
            future = self._pending_requests[message["id"]]

            if "error" in message:
                error = message["error"]
                error_msg = error.get("message", "Unknown error")
                future.set_exception(RuntimeError(f"JSON-RPC error: {error_msg}"))
            elif "result" in message:
                future.set_result(message["result"])
            else:
                future.set_exception(RuntimeError("Invalid response: missing result or error"))

        # Check if this is a notification or request from the server
        elif "method" in message:
            logger.debug("Received notification/request: %s", message["method"])
            # We don't handle server-initiated requests/notifications yet
        else:
            logger.warning("Received unknown message: %s", message)
