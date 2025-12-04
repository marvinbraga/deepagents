"""MCP Protocol types and data structures."""

from dataclasses import dataclass, field
from typing import Any, NotRequired, TypedDict


class MCPToolInput(TypedDict):
    """Represents an input parameter for an MCP tool."""

    type: str
    """The JSON Schema type of the parameter."""

    description: NotRequired[str]
    """Optional description of the parameter."""

    properties: NotRequired[dict[str, Any]]
    """For object types, the nested properties."""

    items: NotRequired[dict[str, Any]]
    """For array types, the item schema."""

    required: NotRequired[list[str]]
    """List of required property names (for object types)."""

    enum: NotRequired[list[Any]]
    """List of allowed values (for enum types)."""


class MCPTool(TypedDict):
    """Represents an MCP tool definition."""

    name: str
    """The name of the tool."""

    description: NotRequired[str]
    """Optional description of what the tool does."""

    inputSchema: dict[str, Any]
    """JSON Schema defining the tool's input parameters."""


class MCPResource(TypedDict):
    """Represents an MCP resource."""

    uri: str
    """The URI of the resource."""

    name: str
    """The name of the resource."""

    description: NotRequired[str]
    """Optional description of the resource."""

    mimeType: NotRequired[str]
    """Optional MIME type of the resource."""


class MCPServerCapabilities(TypedDict):
    """Represents the capabilities of an MCP server."""

    tools: NotRequired[dict[str, Any]]
    """Tool-related capabilities."""

    resources: NotRequired[dict[str, Any]]
    """Resource-related capabilities."""

    prompts: NotRequired[dict[str, Any]]
    """Prompt-related capabilities."""

    logging: NotRequired[dict[str, Any]]
    """Logging-related capabilities."""


@dataclass
class MCPServerConfig:
    """Configuration for an MCP server connection.

    Attributes:
        name: Unique identifier for this server
        command: The command to execute to start the server
        args: Command-line arguments for the server
        env: Environment variables to set for the server process
        transport: The transport mechanism (currently only 'stdio' is supported)
        enabled: Whether this server is enabled
    """

    name: str
    command: str
    args: list[str] = field(default_factory=list)
    env: dict[str, str] = field(default_factory=dict)
    transport: str = "stdio"
    enabled: bool = True

    def __post_init__(self) -> None:
        """Validate the configuration after initialization."""
        if self.transport != "stdio":
            msg = f"Unsupported transport: {self.transport}. Only 'stdio' is currently supported."
            raise ValueError(msg)
