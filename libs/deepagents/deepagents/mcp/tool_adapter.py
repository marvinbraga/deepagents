"""Adapter to convert MCP tools to LangChain tools."""

import logging
from typing import Any, ClassVar

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field, create_model

from deepagents.mcp.client import MCPClient
from deepagents.mcp.protocol import MCPTool

logger = logging.getLogger(__name__)


def _json_schema_to_pydantic_field(name: str, schema: dict[str, Any]) -> tuple[type, Any]:
    """Convert a JSON Schema property to a Pydantic field type and default.

    Args:
        name: The name of the field
        schema: The JSON Schema for this field

    Returns:
        A tuple of (type, Field(...)) suitable for Pydantic model creation
    """
    schema_type = schema.get("type", "string")
    description = schema.get("description", "")
    default = schema.get("default", ...)

    # Map JSON Schema types to Python types
    type_mapping = {
        "string": str,
        "number": float,
        "integer": int,
        "boolean": bool,
        "array": list,
        "object": dict,
    }

    field_type = type_mapping.get(schema_type, Any)

    # Handle arrays with item types
    if schema_type == "array" and "items" in schema:
        items_schema = schema["items"]
        items_type = type_mapping.get(items_schema.get("type", "string"), Any)
        field_type = list[items_type]  # type: ignore[valid-type]

    # Handle enums
    if "enum" in schema:
        # For enums, we still use the base type but the validation will be in the schema
        pass

    # Create the Field with description and default
    if default is ...:
        field_info = Field(description=description)
    else:
        field_info = Field(default=default, description=description)

    return (field_type, field_info)


def _create_input_model_from_schema(tool_name: str, schema: dict[str, Any]) -> type[BaseModel]:
    """Create a Pydantic model from a JSON Schema.

    Args:
        tool_name: The name of the tool (used for the model name)
        schema: The JSON Schema defining the input structure

    Returns:
        A Pydantic model class
    """
    # Get properties and required fields
    properties = schema.get("properties", {})
    required_fields = set(schema.get("required", []))

    # Build field definitions
    field_definitions: dict[str, Any] = {}

    for field_name, field_schema in properties.items():
        field_type, field_info = _json_schema_to_pydantic_field(field_name, field_schema)

        # If the field is not required, make it optional
        if field_name not in required_fields:
            field_type = field_type | None  # type: ignore[assignment]
            if field_info.default is ...:
                field_info.default = None

        field_definitions[field_name] = (field_type, field_info)

    # If no properties, create a simple model with no fields
    if not field_definitions:
        field_definitions["dummy_field"] = (str | None, Field(default=None, description="No input required"))

    # Create the model
    model_name = f"{tool_name.replace('-', '_').replace('.', '_').title()}Input"
    return create_model(model_name, **field_definitions)


class MCPToolWrapper(BaseTool):
    """A LangChain tool that wraps an MCP tool.

    This class provides the bridge between LangChain's tool system
    and MCP tools, handling the conversion of inputs and outputs.
    """

    client: MCPClient
    """The MCP client instance."""

    tool_name: str
    """The name of the MCP tool."""

    name: str = ""
    """The tool name (for LangChain)."""

    description: str = ""
    """The tool description."""

    args_schema: type[BaseModel] | None = None
    """The Pydantic model for tool arguments."""

    # Class variable to track async capability
    _is_async: ClassVar[bool] = True

    def __init__(self, client: MCPClient, mcp_tool: MCPTool, **kwargs: Any) -> None:
        """Initialize the MCP tool wrapper.

        Args:
            client: The MCP client instance
            mcp_tool: The MCP tool definition
            **kwargs: Additional arguments to pass to BaseTool
        """
        # Create the input model from the JSON Schema
        input_schema = mcp_tool.get("inputSchema", {})
        args_schema = _create_input_model_from_schema(mcp_tool["name"], input_schema)

        # Initialize the BaseTool
        super().__init__(
            client=client,
            tool_name=mcp_tool["name"],
            name=mcp_tool["name"],
            description=mcp_tool.get("description", f"MCP tool: {mcp_tool['name']}"),
            args_schema=args_schema,
            **kwargs,
        )

    def _run(self, **kwargs: Any) -> Any:
        """Synchronous run method (not supported for MCP tools).

        MCP tools are async-only, so this method raises an error.

        Args:
            **kwargs: Tool arguments

        Raises:
            NotImplementedError: Always, as MCP tools are async-only
        """
        msg = "MCP tools are async-only. Use _arun instead."
        raise NotImplementedError(msg)

    async def _arun(self, **kwargs: Any) -> Any:
        """Execute the MCP tool asynchronously.

        Args:
            **kwargs: Tool arguments matching the tool's schema

        Returns:
            The result from the MCP tool
        """
        # Filter out the dummy field if it exists
        if "dummy_field" in kwargs:
            kwargs.pop("dummy_field")

        try:
            # Call the MCP tool through the client
            result = await self.client.call_tool(self.tool_name, kwargs)

            # Format the result
            if isinstance(result, list):
                # Combine multiple content items
                formatted_parts = []
                for item in result:
                    if isinstance(item, dict):
                        if item.get("type") == "text":
                            formatted_parts.append(item.get("text", ""))
                        elif item.get("type") == "resource":
                            resource_info = item.get("resource", {})
                            formatted_parts.append(f"Resource: {resource_info.get('uri', 'unknown')}")
                        else:
                            formatted_parts.append(str(item))
                    else:
                        formatted_parts.append(str(item))
                return "\n".join(formatted_parts) if formatted_parts else "Success"
            return str(result)

        except Exception as e:
            logger.exception("Error executing MCP tool %s", self.tool_name)
            return f"Error executing tool {self.tool_name}: {e}"


def mcp_tool_to_langchain(client: MCPClient, mcp_tool: MCPTool) -> BaseTool:
    """Convert an MCP tool to a LangChain BaseTool.

    Args:
        client: The MCP client that will execute the tool
        mcp_tool: The MCP tool definition

    Returns:
        A LangChain BaseTool that wraps the MCP tool
    """
    return MCPToolWrapper(client=client, mcp_tool=mcp_tool)
