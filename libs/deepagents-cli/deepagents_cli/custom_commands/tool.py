"""LangChain tool for invoking custom slash commands programmatically.

This tool allows the agent to discover and execute custom slash commands,
similar to how Claude Code's SlashCommand tool works.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from deepagents_cli.custom_commands.registry import CommandRegistry


class SlashCommandInput(BaseModel):
    """Input schema for the SlashCommand tool."""

    command: str = Field(
        description="The slash command to execute (without leading slash). "
        "For example: 'review', 'deploy', 'test'"
    )
    args: list[str] = Field(
        default_factory=list,
        description="Optional list of arguments to pass to the command. "
        "For example: ['src/main.py', '--verbose']",
    )


class SlashCommandTool(BaseTool):
    """Tool for executing custom slash commands.

    This tool allows the agent to:
    1. List available custom commands
    2. Execute a specific command with arguments
    3. Get expanded prompts from command templates

    The tool integrates with the CommandRegistry to discover and execute
    commands from global, agent, and project levels.
    """

    name: str = "slash_command"
    description: str = (
        "Execute a custom slash command. Use this tool to run predefined "
        "command templates that expand into full prompts. First use with "
        "command='list' to see available commands, then execute specific "
        "commands with their required arguments."
    )
    args_schema: type[BaseModel] = SlashCommandInput

    # Internal attributes (not part of Pydantic schema)
    _registry: "CommandRegistry | None" = None
    _project_root: str | None = None
    _cwd: str | None = None

    def __init__(
        self,
        registry: "CommandRegistry | None" = None,
        project_root: str | None = None,
        cwd: str | None = None,
        **kwargs: Any,
    ) -> None:
        """Initialize the SlashCommand tool.

        Args:
            registry: CommandRegistry instance for command lookup.
            project_root: Project root path for template expansion.
            cwd: Current working directory for template expansion.
            **kwargs: Additional arguments passed to BaseTool.
        """
        super().__init__(**kwargs)
        object.__setattr__(self, "_registry", registry)
        object.__setattr__(self, "_project_root", project_root)
        object.__setattr__(self, "_cwd", cwd)

    def _run(self, command: str, args: list[str] | None = None) -> str:
        """Execute the slash command.

        Args:
            command: Command name (without leading slash) or 'list'.
            args: Optional arguments for the command.

        Returns:
            For 'list': A formatted list of available commands.
            For other commands: The expanded prompt text.
        """
        if args is None:
            args = []

        # Handle special 'list' command
        if command.lower() == "list":
            return self._list_commands()

        # Handle special 'info' command
        if command.lower() == "info" and args:
            return self._get_command_info(args[0])

        # Execute the command
        return self._execute_command(command, args)

    async def _arun(self, command: str, args: list[str] | None = None) -> str:
        """Async version - delegates to sync implementation."""
        return self._run(command, args)

    def _list_commands(self) -> str:
        """List all available custom commands.

        Returns:
            Formatted string with command names and descriptions.
        """
        if not self._registry:
            return "No command registry available. Custom commands are not configured."

        commands = self._registry.get_all_commands()
        if not commands:
            return (
                "No custom commands found.\n\n"
                "Custom commands can be created in:\n"
                "  - Global: ~/.deepagents/commands/{index}/{name}.md\n"
                "  - Agent: ~/.deepagents/{agent}/commands/{index}/{name}.md\n"
                "  - Project: .deepagents/commands/{index}/{name}.md"
            )

        lines = ["Available custom commands:\n"]
        for cmd_name, cmd_desc in sorted(commands.items()):
            lines.append(f"  /{cmd_name} - {cmd_desc}")

        lines.append("\nUse slash_command with command='info' and args=['command_name'] for details.")
        return "\n".join(lines)

    def _get_command_info(self, command_name: str) -> str:
        """Get detailed information about a command.

        Args:
            command_name: Name of the command to get info for.

        Returns:
            Detailed command information.
        """
        if not self._registry:
            return "No command registry available."

        metadata = self._registry.get_custom_command(command_name)
        if not metadata:
            return f"Command '/{command_name}' not found. Use command='list' to see available commands."

        lines = [
            f"Command: /{metadata['name']}",
            f"Description: {metadata['description']}",
            f"Source: {metadata['source']}",
        ]

        # Add aliases
        aliases = metadata.get("aliases", [])
        if aliases:
            lines.append(f"Aliases: {', '.join('/' + a for a in aliases)}")

        # Add arguments
        args = metadata.get("args", [])
        if args:
            lines.append("\nArguments:")
            for arg in args:
                name = arg.get("name", "?")
                desc = arg.get("description", "")
                required = "required" if arg.get("required", False) else "optional"
                default = arg.get("default", "")
                if default:
                    lines.append(f"  - {name}: {desc} ({required}, default: {default})")
                else:
                    lines.append(f"  - {name}: {desc} ({required})")

        lines.append(f"\nLocation: {metadata['path']}")
        return "\n".join(lines)

    def _execute_command(self, command_name: str, args: list[str]) -> str:
        """Execute a custom command and return the expanded prompt.

        Args:
            command_name: Name of the command to execute.
            args: Arguments to pass to the command.

        Returns:
            The expanded prompt text from the command template.
        """
        from pathlib import Path

        from deepagents_cli.custom_commands.load import (
            expand_command_template,
            get_command_content,
        )

        if not self._registry:
            return "No command registry available. Cannot execute commands."

        # Look up command
        metadata = self._registry.get_custom_command(command_name)
        if not metadata:
            return (
                f"Command '/{command_name}' not found.\n\n"
                f"Use command='list' to see available commands."
            )

        # Get command content
        content = get_command_content(metadata["path"])
        if not content:
            return f"Error: Could not read command file at {metadata['path']}"

        # Validate required arguments
        arg_specs = metadata.get("args", [])
        for i, arg_spec in enumerate(arg_specs):
            if arg_spec.get("required", False) and i >= len(args):
                arg_name = arg_spec.get("name", f"arg{i}")
                return (
                    f"Missing required argument: {arg_name}\n"
                    f"Description: {arg_spec.get('description', 'No description')}\n\n"
                    f"Use command='info' with args=['{command_name}'] for full usage."
                )

        # Expand template
        project_root = self._project_root or str(Path.cwd())
        cwd = self._cwd or str(Path.cwd())

        expanded = expand_command_template(
            template=content,
            positional_args=args,
            metadata=metadata,
            project_root=project_root,
            cwd=cwd,
        )

        return expanded


def create_slash_command_tool(
    registry: "CommandRegistry | None" = None,
    project_root: str | None = None,
    cwd: str | None = None,
) -> SlashCommandTool:
    """Factory function to create a SlashCommandTool.

    Args:
        registry: CommandRegistry instance for command lookup.
        project_root: Project root path for template expansion.
        cwd: Current working directory for template expansion.

    Returns:
        Configured SlashCommandTool instance.
    """
    return SlashCommandTool(
        registry=registry,
        project_root=project_root,
        cwd=cwd,
    )


__all__ = [
    "SlashCommandTool",
    "SlashCommandInput",
    "create_slash_command_tool",
]
