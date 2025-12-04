"""Loader for MCP configuration files."""

import json
import logging
from pathlib import Path

from deepagents.mcp.protocol import MCPServerConfig

logger = logging.getLogger(__name__)


def load_mcp_config() -> list[MCPServerConfig]:
    """Load MCP server configurations from config file.

    Searches for mcp_config.json in the following locations (in order):
    1. .deepagents/mcp_config.json (project-level)
    2. ~/.deepagents/mcp_config.json (user-level)

    Returns:
        List of MCPServerConfig objects. Returns empty list if no config found.

    Example config file format:
        ```json
        {
            "servers": [
                {
                    "name": "filesystem",
                    "command": "mcp-server-filesystem",
                    "args": ["/path/to/workspace"],
                    "enabled": true
                },
                {
                    "name": "github",
                    "command": "mcp-server-github",
                    "env": {
                        "GITHUB_TOKEN": "ghp_xxxxx"
                    },
                    "enabled": false
                }
            ]
        }
        ```
    """
    # Check project-level config first
    project_config = Path(".deepagents/mcp_config.json")
    if project_config.exists():
        logger.info("Loading MCP config from project: %s", project_config)
        return _load_config_file(project_config)

    # Fall back to user-level config
    user_config = Path.home() / ".deepagents" / "mcp_config.json"
    if user_config.exists():
        logger.info("Loading MCP config from user home: %s", user_config)
        return _load_config_file(user_config)

    logger.debug("No MCP config file found")
    return []


def _load_config_file(config_path: Path) -> list[MCPServerConfig]:
    """Load and parse MCP config file.

    Args:
        config_path: Path to the config file

    Returns:
        List of MCPServerConfig objects

    Raises:
        ValueError: If the config file is invalid
    """
    try:
        with config_path.open() as f:
            data = json.load(f)

        if not isinstance(data, dict) or "servers" not in data:
            msg = f"Invalid MCP config file: {config_path}. Expected 'servers' key."
            raise ValueError(msg)

        servers = data["servers"]
        if not isinstance(servers, list):
            msg = f"Invalid MCP config file: {config_path}. 'servers' must be a list."
            raise ValueError(msg)

        configs = []
        for server_data in servers:
            try:
                # Extract and validate required fields
                name = server_data.get("name")
                command = server_data.get("command")

                if not name or not command:
                    logger.warning("Skipping MCP server config without name or command: %s", server_data)
                    continue

                # Create config with all fields
                config = MCPServerConfig(
                    name=name,
                    command=command,
                    args=server_data.get("args", []),
                    env=server_data.get("env", {}),
                    enabled=server_data.get("enabled", True),
                )
                configs.append(config)
                logger.debug("Loaded MCP server config: %s", name)

            except Exception as e:
                logger.exception("Error parsing MCP server config: %s", e)
                continue

        logger.info("Loaded %d MCP server configs from %s", len(configs), config_path)
        return configs

    except json.JSONDecodeError as e:
        msg = f"Invalid JSON in MCP config file {config_path}: {e}"
        raise ValueError(msg) from e
    except Exception as e:
        logger.exception("Error loading MCP config file %s: %s", config_path, e)
        return []
