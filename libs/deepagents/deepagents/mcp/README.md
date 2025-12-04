# MCP (Model Context Protocol) Integration

This module provides integration with the Model Context Protocol (MCP) for DeepAgents, allowing agents to connect to MCP servers and use their tools and resources.

## Overview

The MCP integration consists of four main components:

1. **Protocol Types** (`protocol.py`) - TypedDicts and dataclasses for MCP protocol
2. **Client** (`client.py`) - JSON-RPC client for communicating with MCP servers
3. **Tool Adapter** (`tool_adapter.py`) - Converts MCP tools to LangChain tools
4. **Middleware** (`middleware/mcp.py`) - Integrates MCP into DeepAgents

## Quick Start

### Basic Usage

```python
import asyncio
from deepagents.mcp import MCPClient, MCPServerConfig
from deepagents.middleware.mcp import MCPMiddleware

# Configure an MCP server
server_config = MCPServerConfig(
    name="my-server",
    command="node",
    args=["path/to/mcp-server.js"],
    env={"API_KEY": "your-api-key"},
)

# Create and initialize middleware
async def main():
    middleware = MCPMiddleware(servers=[server_config])

    async with middleware:
        # Get available tools
        tools = middleware.get_tools()
        print(f"Available tools: {[t.name for t in tools]}")

        # List resources
        resources = middleware.list_resources()
        print(f"Resources: {resources}")

        # Read a resource
        content = await middleware.read_resource("my-server", "file://example.txt")
        print(f"Resource content: {content}")

asyncio.run(main())
```

### Integration with DeepAgents

```python
from deepagents import create_deep_agent
from deepagents.mcp import MCPServerConfig
from deepagents.middleware.mcp import MCPMiddleware

# Configure MCP servers
mcp_servers = [
    MCPServerConfig(
        name="filesystem",
        command="npx",
        args=["-y", "@modelcontextprotocol/server-filesystem", "/path/to/data"],
    ),
    MCPServerConfig(
        name="github",
        command="npx",
        args=["-y", "@modelcontextprotocol/server-github"],
        env={"GITHUB_TOKEN": "your-token"},
    ),
]

# Create middleware
mcp_middleware = MCPMiddleware(servers=mcp_servers)

# Initialize middleware before creating agent
import asyncio
async def setup():
    await mcp_middleware.initialize()

    # Create agent with MCP tools
    agent = create_deep_agent(
        middleware=[mcp_middleware],
        system_prompt=mcp_middleware.get_system_prompt_addition(),
    )

    # The agent now has access to all MCP tools
    return agent

agent = asyncio.run(setup())
```

## API Reference

### MCPServerConfig

Dataclass for configuring an MCP server connection.

**Attributes:**
- `name` (str): Unique identifier for the server
- `command` (str): Command to execute to start the server
- `args` (list[str]): Command-line arguments (default: `[]`)
- `env` (dict[str, str]): Environment variables (default: `{}`)
- `transport` (str): Transport mechanism (default: `"stdio"`, only supported value)
- `enabled` (bool): Whether the server is enabled (default: `True`)

**Example:**
```python
config = MCPServerConfig(
    name="my-server",
    command="node",
    args=["server.js"],
    env={"NODE_ENV": "production"},
)
```

### MCPClient

Client for JSON-RPC communication with an MCP server via stdio.

**Methods:**
- `async connect()`: Start the server process and initialize
- `async disconnect()`: Terminate the server process
- `async call_tool(name, arguments)`: Call an MCP tool
- `async read_resource(uri)`: Read an MCP resource

**Properties:**
- `tools`: List of available tools from the server
- `resources`: List of available resources
- `capabilities`: Server capabilities
- `is_connected`: Connection status

**Example:**
```python
client = MCPClient(config)
await client.connect()

# Call a tool
result = await client.call_tool("search", {"query": "example"})

# Read a resource
content = await client.read_resource("file://data.json")

await client.disconnect()
```

### MCPMiddleware

Middleware for managing MCP server connections in DeepAgents.

**Methods:**
- `async initialize()`: Connect to all enabled servers
- `async shutdown()`: Disconnect from all servers
- `get_tools()`: Get all MCP tools as LangChain tools
- `enhance_tools(existing_tools)`: Add MCP tools to existing tools
- `async read_resource(server_name, uri)`: Read a resource from a specific server
- `list_resources()`: List all resources from all servers
- `get_system_prompt_addition()`: Get prompt text about connected servers

**Example:**
```python
middleware = MCPMiddleware(
    servers=[config1, config2],
    auto_connect=True,  # Auto-connect on first use
)

# Use as context manager
async with middleware:
    tools = middleware.get_tools()
    resources = middleware.list_resources()
```

### mcp_tool_to_langchain()

Converts an MCP tool definition to a LangChain BaseTool.

**Parameters:**
- `client` (MCPClient): The client that will execute the tool
- `mcp_tool` (MCPTool): The MCP tool definition

**Returns:**
- `BaseTool`: A LangChain tool wrapping the MCP tool

**Example:**
```python
from deepagents.mcp.tool_adapter import mcp_tool_to_langchain

mcp_tool = {
    "name": "search",
    "description": "Search for information",
    "inputSchema": {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search query"}
        },
        "required": ["query"]
    }
}

langchain_tool = mcp_tool_to_langchain(client, mcp_tool)
```

## Protocol Details

### Message Format

The MCP protocol uses JSON-RPC 2.0 over stdio with Content-Length headers (similar to LSP):

```
Content-Length: <bytes>\r\n
\r\n
<JSON payload>
```

### Initialization Handshake

1. Client sends `initialize` request
2. Server responds with capabilities
3. Client sends `notifications/initialized` notification

### Tool Invocation

```python
# Request
{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/call",
    "params": {
        "name": "tool_name",
        "arguments": {"param": "value"}
    }
}

# Response
{
    "jsonrpc": "2.0",
    "id": 1,
    "result": {
        "content": [
            {"type": "text", "text": "Result text"}
        ]
    }
}
```

### Resource Reading

```python
# Request
{
    "jsonrpc": "2.0",
    "id": 2,
    "method": "resources/read",
    "params": {
        "uri": "file://path/to/resource"
    }
}

# Response
{
    "jsonrpc": "2.0",
    "id": 2,
    "result": {
        "contents": [
            {"uri": "file://path/to/resource", "text": "content"}
        ]
    }
}
```

## Error Handling

The MCP integration includes comprehensive error handling:

```python
try:
    await client.connect()
except RuntimeError as e:
    print(f"Failed to connect: {e}")

try:
    result = await client.call_tool("nonexistent", {})
except RuntimeError as e:
    print(f"Tool call failed: {e}")
```

## Logging

The MCP integration uses Python's standard logging module:

```python
import logging

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("deepagents.mcp")
```

## Best Practices

1. **Use Context Managers**: Always use `async with` to ensure proper cleanup
   ```python
   async with middleware:
       # Use middleware
       pass
   # Automatic cleanup
   ```

2. **Handle Connection Failures**: MCP servers may fail to start
   ```python
   try:
       await middleware.initialize()
   except Exception as e:
       logger.error(f"Failed to initialize: {e}")
   ```

3. **Disable Unused Servers**: Use `enabled=False` to disable servers
   ```python
   config = MCPServerConfig(name="unused", command="cmd", enabled=False)
   ```

4. **Add System Prompts**: Include MCP information in agent prompts
   ```python
   system_prompt = base_prompt + "\n" + middleware.get_system_prompt_addition()
   ```

## Troubleshooting

### Server Won't Start

- Check that the command and args are correct
- Verify environment variables are set
- Check server logs (stderr is captured)

### Tools Not Appearing

- Ensure server supports tools (check capabilities)
- Verify server is connected (`client.is_connected`)
- Check middleware is initialized (`middleware._initialized`)

### Resource Read Fails

- Verify the URI format matches server expectations
- Check server supports resources capability
- Ensure you have proper permissions

## Examples

### Example 1: Filesystem Server

```python
from deepagents.mcp import MCPServerConfig
from deepagents.middleware.mcp import MCPMiddleware

config = MCPServerConfig(
    name="fs",
    command="npx",
    args=["-y", "@modelcontextprotocol/server-filesystem", "/tmp"],
)

async def use_filesystem():
    async with MCPMiddleware(servers=[config]) as mw:
        tools = mw.get_tools()
        # Tools: read_file, write_file, list_directory, etc.
```

### Example 2: Multiple Servers

```python
servers = [
    MCPServerConfig(name="github", command="mcp-github"),
    MCPServerConfig(name="slack", command="mcp-slack"),
    MCPServerConfig(name="db", command="mcp-database"),
]

middleware = MCPMiddleware(servers=servers)
await middleware.initialize()

# All tools from all servers are now available
all_tools = middleware.get_tools()
```

### Example 3: Custom Environment

```python
config = MCPServerConfig(
    name="api",
    command="python",
    args=["mcp_server.py"],
    env={
        "API_KEY": os.getenv("MY_API_KEY"),
        "API_URL": "https://api.example.com",
        "DEBUG": "true",
    },
)
```

## License

MIT
