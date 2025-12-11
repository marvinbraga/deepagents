"""Runtime execution of custom slash commands.

This module handles the parsing and execution of custom slash commands,
including argument parsing and template expansion.
"""

from __future__ import annotations

import shlex
from pathlib import Path
from typing import TYPE_CHECKING

from deepagents_cli.custom_commands.load import (
    CommandMetadata,
    expand_command_template,
    get_command_content,
)

if TYPE_CHECKING:
    from rich.console import Console

    from deepagents_cli.custom_commands.registry import CommandRegistry


def parse_command_line(input_str: str) -> tuple[str, list[str]]:
    """Parse a slash command input into command name and arguments.

    Handles quoted arguments and escape sequences properly.

    Args:
        input_str: The full command input (e.g., "/review src/main.py")

    Returns:
        Tuple of (command_name, [args]).
        Command name is without the leading slash.

    Examples:
        >>> parse_command_line("/review")
        ("review", [])
        >>> parse_command_line("/review src/main.py")
        ("review", ["src/main.py"])
        >>> parse_command_line('/search "hello world"')
        ("search", ["hello world"])
    """
    # Remove leading slash and strip whitespace
    clean_input = input_str.strip().lstrip("/")

    if not clean_input:
        return "", []

    try:
        # Use shlex to properly handle quoted strings
        parts = shlex.split(clean_input)
    except ValueError:
        # If shlex fails (e.g., unclosed quotes), fall back to simple split
        parts = clean_input.split()

    if not parts:
        return "", []

    command_name = parts[0].lower()
    args = parts[1:] if len(parts) > 1 else []

    return command_name, args


def handle_custom_command(
    command_name: str,
    args: list[str],
    registry: "CommandRegistry",
    console: "Console",
    *,
    project_root: str | None = None,
    cwd: str | None = None,
) -> tuple[bool, str | None]:
    """Execute a custom slash command.

    Looks up the command in the registry, reads its content,
    expands template variables, and returns the expanded prompt.

    Args:
        command_name: Name of the command (without leading slash).
        args: List of arguments passed to the command.
        registry: CommandRegistry instance.
        console: Rich Console for output.
        project_root: Optional project root path for template expansion.
        cwd: Optional current working directory for template expansion.

    Returns:
        Tuple of (handled, expanded_prompt):
        - (True, prompt) - Command was found and executed, prompt is ready
        - (True, None) - Command was found but produced no output
        - (False, None) - Command was not found in registry
    """
    # Look up command
    metadata = registry.get_custom_command(command_name)
    if metadata is None:
        return False, None

    # Get command content
    content = get_command_content(metadata["path"])
    if content is None:
        console.print(f"[red]Error reading command file: {metadata['path']}[/red]")
        return True, None

    # Validate required arguments
    arg_specs = metadata.get("args", [])
    for i, arg_spec in enumerate(arg_specs):
        if arg_spec.get("required", False) and i >= len(args):
            arg_name = arg_spec.get("name", f"arg{i}")
            console.print(
                f"[red]Missing required argument: {arg_name}[/red]\n"
                f"[dim]Description: {arg_spec.get('description', 'No description')}[/dim]"
            )
            return True, None

    # Expand template
    expanded = expand_command_template(
        template=content,
        positional_args=args,
        metadata=metadata,
        project_root=project_root or str(Path.cwd()),
        cwd=cwd or str(Path.cwd()),
    )

    # Show command execution feedback
    source_label = _get_source_label(metadata["source"])
    index = metadata.get("index", "")
    display_name = f"{index}:{metadata['name']}" if index else metadata["name"]
    console.print(f"\n[dim]Executing /{display_name} ({source_label})...[/dim]\n")

    return True, expanded


def _get_source_label(source: str) -> str:
    """Get human-readable label for command source.

    Args:
        source: Source identifier ('global', 'agent', or 'project').

    Returns:
        Human-readable label.
    """
    labels = {
        "global": "global command",
        "agent": "agent command",
        "project": "project command",
    }
    return labels.get(source, source)


def get_command_help(metadata: CommandMetadata) -> str:
    """Generate help text for a command.

    Args:
        metadata: Command metadata.

    Returns:
        Formatted help text string.
    """
    index = metadata.get("index", "")
    display_name = f"{index}:{metadata['name']}" if index else metadata["name"]
    lines = [
        f"/{display_name} - {metadata['description']}",
    ]

    # Add aliases
    aliases = metadata.get("aliases", [])
    if aliases:
        alias_names = [f"/{index}:{a}" if index else f"/{a}" for a in aliases]
        lines.append(f"  Aliases: {', '.join(alias_names)}")

    # Add arguments
    args = metadata.get("args", [])
    if args:
        lines.append("  Arguments:")
        for arg in args:
            name = arg.get("name", "?")
            desc = arg.get("description", "")
            required = "required" if arg.get("required", False) else "optional"
            default = arg.get("default", "")
            if default:
                lines.append(f"    {name}: {desc} ({required}, default: {default})")
            else:
                lines.append(f"    {name}: {desc} ({required})")

    # Add source
    source_label = _get_source_label(metadata["source"])
    lines.append(f"  Source: {source_label}")

    return "\n".join(lines)
