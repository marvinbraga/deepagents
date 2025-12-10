# ruff: noqa: T201, BLE001, S108, ERA001
"""Example usage of MCP integration with DeepAgents.

This example demonstrates how to:
1. Configure MCP servers
2. Initialize the middleware
3. Use MCP tools with DeepAgents
"""

import asyncio
import logging
import os

from deepagents.mcp import MCPServerConfig
from deepagents.middleware.mcp import MCPMiddleware

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)


async def example_basic_usage() -> None:
    """Basic example of using MCP middleware."""
    print("\n" + "=" * 60)
    print("Example 1: Basic MCP Middleware Usage")
    print("=" * 60 + "\n")

    # Configure a simple MCP server
    # Note: This example uses a hypothetical filesystem server
    config = MCPServerConfig(
        name="filesystem",
        command="npx",
        args=["-y", "@modelcontextprotocol/server-filesystem", "/tmp"],
        enabled=True,  # Set to False to disable this server
    )

    # Create middleware
    middleware = MCPMiddleware(servers=[config], auto_connect=False)

    try:
        # Connect to servers
        await middleware.initialize()

        # Get available tools
        tools = middleware.get_tools()
        print(f"Available tools: {len(tools)}")
        for tool in tools:
            print(f"  - {tool.name}: {tool.description}")

        # List resources
        resources = middleware.list_resources()
        print("\nAvailable resources:")
        for server_name, server_resources in resources.items():
            print(f"  {server_name}: {len(server_resources)} resources")

        # Get system prompt addition
        prompt_addition = middleware.get_system_prompt_addition()
        if prompt_addition:
            print(f"\nSystem prompt addition:\n{prompt_addition}")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        # Clean up
        await middleware.shutdown()


async def example_multiple_servers() -> None:
    """Example with multiple MCP servers."""
    print("\n" + "=" * 60)
    print("Example 2: Multiple MCP Servers")
    print("=" * 60 + "\n")

    # Configure multiple servers
    servers = [
        MCPServerConfig(
            name="filesystem",
            command="npx",
            args=["-y", "@modelcontextprotocol/server-filesystem", "/tmp"],
        ),
        MCPServerConfig(
            name="github",
            command="npx",
            args=["-y", "@modelcontextprotocol/server-github"],
            env={"GITHUB_TOKEN": os.getenv("GITHUB_TOKEN", "")},
            enabled=bool(os.getenv("GITHUB_TOKEN")),  # Only enable if token exists
        ),
    ]

    # Use context manager for automatic cleanup
    async with MCPMiddleware(servers=servers) as middleware:
        print(f"Connected to {len(middleware.clients)} server(s)")

        for server_name, client in middleware.clients.items():
            print(f"\n{server_name}:")
            print(f"  Tools: {len(client.tools)}")
            print(f"  Resources: {len(client.resources)}")


async def example_with_deepagents() -> None:
    """Example of integrating MCP with DeepAgents (requires langchain)."""
    print("\n" + "=" * 60)
    print("Example 3: Integration with DeepAgents")
    print("=" * 60 + "\n")

    try:
        # Import DeepAgents (will fail if not installed)
        from deepagents import create_deep_agent

        # Configure MCP servers
        servers = [
            MCPServerConfig(
                name="filesystem",
                command="npx",
                args=["-y", "@modelcontextprotocol/server-filesystem", "/tmp"],
            ),
        ]

        # Create and initialize middleware
        mcp_middleware = MCPMiddleware(servers=servers)
        await mcp_middleware.initialize()

        # Create agent with MCP middleware
        _agent = create_deep_agent(
            middleware=[mcp_middleware],
            system_prompt=("You are a helpful assistant with access to MCP tools.\n\n" + mcp_middleware.get_system_prompt_addition()),
        )

        print("Agent created successfully with MCP integration!")
        print(f"Available MCP tools: {len(mcp_middleware.get_tools())}")

        # Don't forget to shutdown
        await mcp_middleware.shutdown()

    except ImportError:
        print("DeepAgents not installed. Skipping this example.")
    except Exception as e:
        print(f"Error: {e}")


async def example_custom_server() -> None:
    """Example with custom server configuration."""
    print("\n" + "=" * 60)
    print("Example 4: Custom Server Configuration")
    print("=" * 60 + "\n")

    # Custom server with environment variables
    config = MCPServerConfig(
        name="custom-api",
        command="python",
        args=["custom_mcp_server.py"],
        env={
            "API_KEY": os.getenv("API_KEY", "default-key"),
            "API_URL": "https://api.example.com",
            "DEBUG": "true",
            "TIMEOUT": "30",
        },
        transport="stdio",
        enabled=True,
    )

    print("Server configuration:")
    print(f"  Name: {config.name}")
    print(f"  Command: {config.command} {' '.join(config.args)}")
    print(f"  Environment variables: {len(config.env)}")
    print(f"  Transport: {config.transport}")
    print(f"  Enabled: {config.enabled}")


async def example_error_handling() -> None:
    """Example demonstrating error handling."""
    print("\n" + "=" * 60)
    print("Example 5: Error Handling")
    print("=" * 60 + "\n")

    # Configure a server that will fail to connect
    config = MCPServerConfig(
        name="nonexistent",
        command="nonexistent-command",
        args=["arg1", "arg2"],
    )

    middleware = MCPMiddleware(servers=[config], auto_connect=False)

    try:
        print("Attempting to connect to nonexistent server...")
        await middleware.initialize()
    except Exception as e:
        print(f"✓ Caught expected error: {type(e).__name__}")
        print(f"  Message: {e}")

    # Middleware should handle failed connections gracefully
    print(f"\nConnected servers: {len(middleware.clients)}")
    tools = middleware.get_tools()
    print(f"Available tools: {len(tools)}")


async def main() -> None:
    """Run all examples."""
    print("\n" + "=" * 60)
    print("MCP Integration Examples")
    print("=" * 60)

    # Example 1: Basic usage
    # await example_basic_usage()

    # Example 2: Multiple servers
    # await example_multiple_servers()

    # Example 3: DeepAgents integration
    # await example_with_deepagents()

    # Example 4: Custom configuration
    await example_custom_server()

    # Example 5: Error handling
    await example_error_handling()

    print("\n" + "=" * 60)
    print("Examples completed!")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
