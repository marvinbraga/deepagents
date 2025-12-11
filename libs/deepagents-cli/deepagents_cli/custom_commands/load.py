"""Command loader for parsing and loading custom slash commands from .md files.

This module implements custom slash commands with YAML frontmatter parsing.
Each command is a markdown file within an index directory containing:
- YAML frontmatter (name, description required; aliases, args optional)
- Markdown content that serves as the prompt template

Commands are organized in three levels (precedence: project > agent > global):
- Global: ~/.deepagents/commands/{index_name}/{command_name}.md
- Agent: ~/.deepagents/{agent}/commands/{index_name}/{command_name}.md
- Project: {project}/.deepagents/commands/{index_name}/{command_name}.md

Example command file structure:
```markdown
---
name: review-code
description: Review code for quality and best practices
aliases: [review, cr]
args:
  - name: file
    description: File to review
    required: false
    default: "."
---

Review the code in {file} for:
1. Quality and best practices
2. Potential bugs
...
```
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, TypedDict

# Maximum size for command files (100KB)
MAX_COMMAND_FILE_SIZE = 100 * 1024


class CommandArg(TypedDict, total=False):
    """Argument specification for a command."""

    name: str
    """Name of the argument."""

    description: str
    """Description of what the argument is for."""

    required: bool
    """Whether the argument is required."""

    default: str
    """Default value if not provided."""


class CommandMetadata(TypedDict):
    """Metadata for a custom command."""

    name: str
    """Name of the command (used as /command-name)."""

    description: str
    """Description of what the command does."""

    path: str
    """Absolute path to the command .md file."""

    source: str
    """Source of the command ('global', 'agent', or 'project')."""

    index: str
    """Index/namespace directory name (e.g., 'review', 'docs', 'custom')."""

    aliases: list[str]
    """Alternative names for the command."""

    args: list[CommandArg]
    """Argument specifications for the command."""


def _is_safe_path(path: Path, base_dir: Path) -> bool:
    """Check if a path is safely contained within base_dir.

    This prevents directory traversal attacks via symlinks or path manipulation.
    The function resolves both paths to their canonical form (following symlinks)
    and verifies that the target path is within the base directory.

    Args:
        path: The path to validate
        base_dir: The base directory that should contain the path

    Returns:
        True if the path is safely within base_dir, False otherwise
    """
    try:
        resolved_path = path.resolve()
        resolved_base = base_dir.resolve()
        resolved_path.relative_to(resolved_base)
        return True
    except ValueError:
        return False
    except (OSError, RuntimeError):
        return False


def _parse_yaml_list(value: str) -> list[str]:
    """Parse a simple YAML list from a string.

    Supports formats:
    - [item1, item2, item3]
    - item1, item2, item3

    Args:
        value: The string value to parse

    Returns:
        List of string items
    """
    value = value.strip()
    if value.startswith("[") and value.endswith("]"):
        value = value[1:-1]
    items = [item.strip().strip("'\"") for item in value.split(",")]
    return [item for item in items if item]


def _parse_yaml_args(lines: list[str], start_idx: int) -> list[CommandArg]:
    """Parse YAML args list from frontmatter lines.

    Args:
        lines: All frontmatter lines
        start_idx: Index where 'args:' was found

    Returns:
        List of CommandArg dictionaries
    """
    args: list[CommandArg] = []
    current_arg: dict[str, Any] = {}
    i = start_idx + 1

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # Check for new top-level key (not indented or less indented)
        if stripped and not line.startswith(" ") and not line.startswith("\t"):
            break

        # Check for list item start
        if stripped.startswith("- "):
            if current_arg:
                args.append(CommandArg(**current_arg))  # type: ignore[typeddict-item]
            current_arg = {}
            # Parse inline key if present: "- name: value"
            rest = stripped[2:].strip()
            kv_match = re.match(r"^(\w+):\s*(.+)$", rest)
            if kv_match:
                key, val = kv_match.groups()
                if key == "required":
                    current_arg[key] = val.lower() == "true"
                else:
                    current_arg[key] = val.strip().strip("'\"")
        elif stripped and ":" in stripped:
            # Parse key: value within current arg
            kv_match = re.match(r"^(\w+):\s*(.*)$", stripped)
            if kv_match:
                key, val = kv_match.groups()
                if key == "required":
                    current_arg[key] = val.lower() == "true"
                else:
                    current_arg[key] = val.strip().strip("'\"")

        i += 1

    if current_arg:
        args.append(CommandArg(**current_arg))  # type: ignore[typeddict-item]

    return args


def _parse_command_metadata(
    command_md_path: Path, source: str, index_name: str = ""
) -> CommandMetadata | None:
    """Parse YAML frontmatter from a command markdown file.

    Args:
        command_md_path: Path to the command .md file.
        source: Source of the command ('global', 'agent', or 'project').
        index_name: Name of the index/namespace directory.

    Returns:
        CommandMetadata with parsed fields, or None if parsing fails.
    """
    try:
        file_size = command_md_path.stat().st_size
        if file_size > MAX_COMMAND_FILE_SIZE:
            return None

        content = command_md_path.read_text(encoding="utf-8")

        # Match YAML frontmatter between --- delimiters
        frontmatter_pattern = r"^---\s*\n(.*?)\n---\s*\n"
        match = re.match(frontmatter_pattern, content, re.DOTALL)

        if not match:
            return None

        frontmatter = match.group(1)
        lines = frontmatter.split("\n")

        # Parse key-value pairs from YAML
        metadata: dict[str, Any] = {
            "aliases": [],
            "args": [],
        }

        i = 0
        while i < len(lines):
            line = lines[i].strip()

            # Skip empty lines
            if not line:
                i += 1
                continue

            # Match simple "key: value" pattern
            kv_match = re.match(r"^(\w+):\s*(.*)$", line)
            if kv_match:
                key, value = kv_match.groups()
                value = value.strip()

                if key == "aliases" and value:
                    metadata["aliases"] = _parse_yaml_list(value)
                elif key == "args":
                    metadata["args"] = _parse_yaml_args(lines, i)
                    # Skip to end since args spans multiple lines
                    break
                elif value:
                    metadata[key] = value

            i += 1

        # Validate required fields
        if "name" not in metadata or "description" not in metadata:
            return None

        return CommandMetadata(
            name=metadata["name"],
            description=metadata["description"],
            path=str(command_md_path),
            source=source,
            index=index_name,
            aliases=metadata.get("aliases", []),
            args=metadata.get("args", []),
        )

    except (OSError, UnicodeDecodeError):
        return None


def _list_commands_from_dir(commands_dir: Path, source: str) -> list[CommandMetadata]:
    """List all commands from a single commands directory.

    Commands are organized as:
    commands/
    ├── index-name/
    │   ├── command-name.md      # Command file with YAML frontmatter
    │   └── another-command.md

    Args:
        commands_dir: Path to the commands directory.
        source: Source of the commands ('global', 'agent', or 'project').

    Returns:
        List of command metadata dictionaries.
    """
    commands_dir = commands_dir.expanduser()
    if not commands_dir.exists():
        return []

    try:
        resolved_base = commands_dir.resolve()
    except (OSError, RuntimeError):
        return []

    commands: list[CommandMetadata] = []

    # Iterate through index directories
    for index_dir in commands_dir.iterdir():
        if not _is_safe_path(index_dir, resolved_base):
            continue

        if not index_dir.is_dir():
            continue

        # Look for .md files in the index directory
        index_name = index_dir.name
        for command_file in index_dir.iterdir():
            if not command_file.suffix == ".md":
                continue

            if not _is_safe_path(command_file, resolved_base):
                continue

            metadata = _parse_command_metadata(command_file, source=source, index_name=index_name)
            if metadata:
                commands.append(metadata)

    return commands


def list_commands(
    *,
    global_commands_dir: Path | None = None,
    agent_commands_dir: Path | None = None,
    project_commands_dir: Path | None = None,
) -> list[CommandMetadata]:
    """List commands from global, agent, and project directories.

    Precedence order (higher overrides lower):
    1. Project commands (highest)
    2. Agent commands
    3. Global commands (lowest)

    Args:
        global_commands_dir: Path to global commands directory.
        agent_commands_dir: Path to agent-specific commands directory.
        project_commands_dir: Path to project-level commands directory.

    Returns:
        Merged list of command metadata with proper override semantics.
    """
    all_commands: dict[str, CommandMetadata] = {}

    # Load global commands first (lowest priority)
    if global_commands_dir:
        global_cmds = _list_commands_from_dir(global_commands_dir, source="global")
        for cmd in global_cmds:
            all_commands[cmd["name"]] = cmd
            # Also index by aliases
            for alias in cmd.get("aliases", []):
                if alias not in all_commands:
                    all_commands[alias] = cmd

    # Load agent commands second (medium priority)
    if agent_commands_dir:
        agent_cmds = _list_commands_from_dir(agent_commands_dir, source="agent")
        for cmd in agent_cmds:
            all_commands[cmd["name"]] = cmd
            for alias in cmd.get("aliases", []):
                all_commands[alias] = cmd

    # Load project commands last (highest priority)
    if project_commands_dir:
        project_cmds = _list_commands_from_dir(project_commands_dir, source="project")
        for cmd in project_cmds:
            all_commands[cmd["name"]] = cmd
            for alias in cmd.get("aliases", []):
                all_commands[alias] = cmd

    # Return unique commands (deduplicate by name, not aliases)
    seen_names: set[str] = set()
    unique_commands: list[CommandMetadata] = []
    for cmd in all_commands.values():
        if cmd["name"] not in seen_names:
            seen_names.add(cmd["name"])
            unique_commands.append(cmd)

    return unique_commands


def get_command_content(command_path: str | Path) -> str | None:
    """Get the content of a command file (excluding YAML frontmatter).

    Args:
        command_path: Path to the command .md file.

    Returns:
        The command content after the frontmatter, or None if reading fails.
    """
    try:
        path = Path(command_path)
        if not path.exists():
            return None

        file_size = path.stat().st_size
        if file_size > MAX_COMMAND_FILE_SIZE:
            return None

        content = path.read_text(encoding="utf-8")

        # Remove YAML frontmatter
        frontmatter_pattern = r"^---\s*\n.*?\n---\s*\n"
        content = re.sub(frontmatter_pattern, "", content, count=1, flags=re.DOTALL)

        return content.strip()

    except (OSError, UnicodeDecodeError):
        return None


def expand_command_template(
    template: str,
    positional_args: list[str],
    metadata: CommandMetadata,
    *,
    project_root: str | None = None,
    cwd: str | None = None,
) -> str:
    """Expand template variables in command content.

    Supported variables:
    - {arg_name} - replaced with argument value (positional or default)
    - {project_root} - current project root
    - {cwd} - current working directory

    Args:
        template: The command template content.
        positional_args: List of positional arguments from command line.
        metadata: Command metadata with arg specifications.
        project_root: Optional project root path.
        cwd: Optional current working directory.

    Returns:
        Template with variables expanded.
    """
    result = template

    # Build argument values map
    arg_values: dict[str, str] = {}
    arg_specs = metadata.get("args", [])

    for i, arg_spec in enumerate(arg_specs):
        arg_name = arg_spec.get("name", f"arg{i}")
        if i < len(positional_args):
            arg_values[arg_name] = positional_args[i]
        elif "default" in arg_spec:
            arg_values[arg_name] = arg_spec["default"]

    # Replace argument variables
    for arg_name, arg_value in arg_values.items():
        result = result.replace(f"{{{arg_name}}}", arg_value)

    # Replace special variables
    if project_root:
        result = result.replace("{project_root}", project_root)
    if cwd:
        result = result.replace("{cwd}", cwd)

    return result
