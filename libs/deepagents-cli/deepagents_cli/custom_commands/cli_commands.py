"""CLI commands for custom slash command management.

These commands are registered with the CLI:
- deepagents commands list --agent <agent> [--project] [--global]
- deepagents commands create <name> [--index <index>] [--project] [--global]
- deepagents commands info <name>
"""

import argparse
import re
from pathlib import Path
from typing import Any

from deepagents_cli.config import COLORS, Settings, console
from deepagents_cli.custom_commands.load import get_command_content, list_commands


def _validate_name(name: str) -> tuple[bool, str]:
    """Validate name to prevent path traversal attacks.

    Args:
        name: The name to validate

    Returns:
        Tuple of (is_valid, error_message). If valid, error_message is empty.
    """
    if not name or not name.strip():
        return False, "cannot be empty"

    if ".." in name:
        return False, "name cannot contain '..' (path traversal)"

    if name.startswith(("/", "\\")):
        return False, "name cannot be an absolute path"

    if "/" in name or "\\" in name:
        return False, "name cannot contain path separators"

    if not re.match(r"^[a-zA-Z0-9_-]+$", name):
        return False, "name can only contain letters, numbers, hyphens, and underscores"

    return True, ""


def _validate_command_path(command_dir: Path, base_dir: Path) -> tuple[bool, str]:
    """Validate that the resolved command directory is within the base directory.

    Args:
        command_dir: The command directory path to validate
        base_dir: The base commands directory that should contain command_dir

    Returns:
        Tuple of (is_valid, error_message). If valid, error_message is empty.
    """
    try:
        resolved_cmd = command_dir.resolve()
        resolved_base = base_dir.resolve()

        if hasattr(resolved_cmd, "is_relative_to"):
            if not resolved_cmd.is_relative_to(resolved_base):
                return False, f"Command directory must be within {base_dir}"
        else:
            try:
                resolved_cmd.relative_to(resolved_base)
            except ValueError:
                return False, f"Command directory must be within {base_dir}"

        return True, ""
    except (OSError, RuntimeError) as e:
        return False, f"Invalid path: {e}"


def _list(agent: str, *, project: bool = False, global_only: bool = False) -> None:
    """List all available custom commands.

    Args:
        agent: Agent identifier for agent-specific commands.
        project: If True, show only project commands.
        global_only: If True, show only global commands.
    """
    settings = Settings.from_environment()
    global_dir = settings.get_global_commands_dir()
    agent_dir = settings.get_user_commands_dir(agent)
    project_dir = settings.get_project_commands_dir()

    # Filter directories based on flags
    if project:
        if not project_dir:
            console.print("[yellow]Not in a project directory.[/yellow]")
            console.print(
                "[dim]Project commands require a .git directory in the project root.[/dim]",
                style=COLORS["dim"],
            )
            return
        commands = list_commands(project_commands_dir=project_dir)
        console.print("\n[bold]Project Commands:[/bold]\n", style=COLORS["primary"])
    elif global_only:
        commands = list_commands(global_commands_dir=global_dir)
        console.print("\n[bold]Global Commands:[/bold]\n", style=COLORS["primary"])
    else:
        commands = list_commands(
            global_commands_dir=global_dir,
            agent_commands_dir=agent_dir,
            project_commands_dir=project_dir,
        )

        if not commands:
            console.print("[yellow]No custom commands found.[/yellow]")
            console.print(
                "[dim]Commands are loaded from:\n"
                f"  Global:  ~/.deepagents/commands/\n"
                f"  Agent:   ~/.deepagents/{agent}/commands/\n"
                f"  Project: .deepagents/commands/[/dim]",
                style=COLORS["dim"],
            )
            console.print(
                "\n[dim]Create your first command:\n  deepagents commands create review[/dim]",
                style=COLORS["dim"],
            )
            return

        console.print("\n[bold]Available Commands:[/bold]\n", style=COLORS["primary"])

    # Group commands by source
    global_cmds = [c for c in commands if c["source"] == "global"]
    agent_cmds = [c for c in commands if c["source"] == "agent"]
    project_cmds = [c for c in commands if c["source"] == "project"]

    def _print_commands(cmds: list, label: str, color: str) -> None:
        if cmds:
            console.print(f"[bold {color}]{label}:[/bold {color}]", style=COLORS["primary"])
            for cmd in cmds:
                cmd_path = Path(cmd["path"])
                index = cmd.get("index", "")
                display_name = f"{index}:{cmd['name']}" if index else cmd["name"]
                aliases = cmd.get("aliases", [])
                alias_names = [f"{index}:{a}" if index else a for a in aliases]
                alias_str = f" (aliases: {', '.join(alias_names)})" if aliases else ""
                console.print(f"  • [bold]/{display_name}[/bold]{alias_str}", style=COLORS["primary"])
                console.print(f"    {cmd['description']}", style=COLORS["dim"])
                console.print(f"    Location: {cmd_path.parent}/", style=COLORS["dim"])
                console.print()

    if not project and not global_only:
        _print_commands(global_cmds, "Global Commands", "blue")
        _print_commands(agent_cmds, "Agent Commands", "cyan")
    _print_commands(project_cmds, "Project Commands", "green")


def _create(
    command_name: str,
    agent: str,
    *,
    index: str = "custom",
    project: bool = False,
    global_cmd: bool = False,
) -> None:
    """Create a new custom command with a template markdown file.

    Args:
        command_name: Name of the command to create.
        agent: Agent identifier for agent-specific commands.
        index: Index directory name (default: "custom").
        project: If True, create in project commands directory.
        global_cmd: If True, create in global commands directory.
    """
    # Validate command name
    is_valid, error_msg = _validate_name(command_name)
    if not is_valid:
        console.print(f"[bold red]Error:[/bold red] Invalid command name: {error_msg}")
        console.print(
            "[dim]Command names must only contain letters, numbers, hyphens, and underscores.[/dim]",
            style=COLORS["dim"],
        )
        return

    # Validate index name
    is_valid, error_msg = _validate_name(index)
    if not is_valid:
        console.print(f"[bold red]Error:[/bold red] Invalid index name: {error_msg}")
        return

    # Determine target directory
    settings = Settings.from_environment()
    if project:
        if not settings.project_root:
            console.print("[bold red]Error:[/bold red] Not in a project directory.")
            console.print(
                "[dim]Project commands require a .git directory in the project root.[/dim]",
                style=COLORS["dim"],
            )
            return
        commands_dir = settings.ensure_project_commands_dir()
    elif global_cmd:
        commands_dir = settings.ensure_global_commands_dir()
    else:
        commands_dir = settings.ensure_user_commands_dir(agent)

    index_dir = commands_dir / index
    command_file = index_dir / f"{command_name}.md"

    # Validate the resolved path is within commands_dir
    is_valid_path, path_error = _validate_command_path(command_file, commands_dir)
    if not is_valid_path:
        console.print(f"[bold red]Error:[/bold red] {path_error}")
        return

    if command_file.exists():
        console.print(
            f"[bold red]Error:[/bold red] Command '{command_name}' already exists at {command_file}"
        )
        return

    # Create index directory if needed
    index_dir.mkdir(parents=True, exist_ok=True)

    # Create template command file
    template = f"""---
name: {command_name}
description: [Brief description of what this command does]
aliases: []
args:
  - name: target
    description: Target file or directory
    required: false
    default: "."
---

# {command_name.title().replace("-", " ")} Command

[Your command prompt template goes here]

This content will be expanded and sent to the agent when you run /{command_name}.

## Template Variables

You can use these variables in your prompt:
- {{target}} - Replaced with the first argument (or default value)
- {{project_root}} - Current project root directory
- {{cwd}} - Current working directory

## Example

When you type `/{command_name} src/main.py`, this template will be expanded
with `{{target}}` replaced by `src/main.py`.

---

[Replace this content with your actual command instructions]
"""

    command_file.write_text(template)

    location_type = "project" if project else ("global" if global_cmd else "agent")
    display_name = f"{index}:{command_name}"
    console.print(
        f"✓ Command '/{display_name}' created successfully! ({location_type})",
        style=COLORS["primary"],
    )
    console.print(f"Location: {command_file}\n", style=COLORS["dim"])
    console.print(
        f"[dim]Edit the command file to customize:\n"
        f"  1. Update the description in YAML frontmatter\n"
        f"  2. Add aliases if desired\n"
        f"  3. Define arguments with defaults\n"
        f"  4. Write your prompt template\n"
        f"\n"
        f"  nano {command_file}\n"
        f"\n"
        f"Then use: /{display_name} [args]\n",
        style=COLORS["dim"],
    )


def _info(command_name: str, *, agent: str = "agent", project: bool = False) -> None:
    """Show detailed information about a specific command.

    Args:
        command_name: Name of the command to show info for.
        agent: Agent identifier for commands.
        project: If True, only search in project commands.
    """
    settings = Settings.from_environment()
    global_dir = settings.get_global_commands_dir()
    agent_dir = settings.get_user_commands_dir(agent)
    project_dir = settings.get_project_commands_dir()

    # Load commands based on --project flag
    if project:
        if not project_dir:
            console.print("[bold red]Error:[/bold red] Not in a project directory.")
            return
        commands = list_commands(project_commands_dir=project_dir)
    else:
        commands = list_commands(
            global_commands_dir=global_dir,
            agent_commands_dir=agent_dir,
            project_commands_dir=project_dir,
        )

    # Find the command (by name or alias)
    # Support both short name (code-review) and full name (review:code-review)
    command = None
    for cmd in commands:
        index = cmd.get("index", "")
        full_name = f"{index}:{cmd['name']}" if index else cmd["name"]
        full_aliases = [f"{index}:{a}" if index else a for a in cmd.get("aliases", [])]

        # Match by short name, full name, short alias, or full alias
        if (cmd["name"] == command_name or
            full_name == command_name or
            command_name in cmd.get("aliases", []) or
            command_name in full_aliases):
            command = cmd
            break

    if not command:
        console.print(f"[bold red]Error:[/bold red] Command '/{command_name}' not found.")
        console.print("\n[dim]Available commands:[/dim]", style=COLORS["dim"])
        for cmd in commands:
            index = cmd.get("index", "")
            display_name = f"{index}:{cmd['name']}" if index else cmd["name"]
            console.print(f"  - /{display_name}", style=COLORS["dim"])
        return

    # Get command content
    command_content = get_command_content(command["path"])

    # Determine source label and color
    source_labels = {
        "global": ("Global Command", "blue"),
        "agent": ("Agent Command", "cyan"),
        "project": ("Project Command", "green"),
    }
    source_label, source_color = source_labels.get(command["source"], ("Command", "white"))

    index = command.get("index", "")
    display_name = f"{index}:{command['name']}" if index else command["name"]
    console.print(
        f"\n[bold]Command: /{display_name}[/bold] "
        f"[bold {source_color}]({source_label})[/bold {source_color}]\n",
        style=COLORS["primary"],
    )
    console.print(f"[bold]Description:[/bold] {command['description']}\n", style=COLORS["dim"])

    # Show aliases
    aliases = command.get("aliases", [])
    if aliases:
        alias_names = [f"/{index}:{a}" if index else f"/{a}" for a in aliases]
        console.print(f"[bold]Aliases:[/bold] {', '.join(alias_names)}\n", style=COLORS["dim"])

    # Show arguments
    args = command.get("args", [])
    if args:
        console.print("[bold]Arguments:[/bold]", style=COLORS["dim"])
        for arg in args:
            name = arg.get("name", "?")
            desc = arg.get("description", "")
            required = "required" if arg.get("required", False) else "optional"
            default = arg.get("default", "")
            if default:
                console.print(f"  • {name}: {desc} ({required}, default: {default})", style=COLORS["dim"])
            else:
                console.print(f"  • {name}: {desc} ({required})", style=COLORS["dim"])
        console.print()

    command_path = Path(command["path"])
    console.print(f"[bold]Location:[/bold] {command_path}\n", style=COLORS["dim"])

    # Show the command content
    console.print("[bold]Command Template:[/bold]\n", style=COLORS["primary"])
    if command_content:
        console.print(command_content, style=COLORS["dim"])
    else:
        console.print("[dim](Unable to read command content)[/dim]")
    console.print()


def setup_commands_parser(subparsers: Any) -> argparse.ArgumentParser:
    """Setup the commands subcommand parser with all its subcommands."""
    commands_parser = subparsers.add_parser(
        "commands",
        help="Manage custom slash commands",
        description="Manage custom slash commands - create, list, and view command information",
    )
    commands_subparsers = commands_parser.add_subparsers(
        dest="commands_command", help="Commands subcommand"
    )

    # Commands list
    list_parser = commands_subparsers.add_parser(
        "list", help="List all available custom commands", description="List all available custom commands"
    )
    list_parser.add_argument(
        "--agent",
        default="agent",
        help="Agent identifier for commands (default: agent)",
    )
    list_parser.add_argument(
        "--project",
        action="store_true",
        help="Show only project-level commands",
    )
    list_parser.add_argument(
        "--global",
        dest="global_only",
        action="store_true",
        help="Show only global commands",
    )

    # Commands create
    create_parser = commands_subparsers.add_parser(
        "create",
        help="Create a new custom command",
        description="Create a new custom command with a template markdown file",
    )
    create_parser.add_argument("name", help="Name of the command to create (e.g., review)")
    create_parser.add_argument(
        "--index",
        default="custom",
        help="Index directory name (default: custom)",
    )
    create_parser.add_argument(
        "--agent",
        default="agent",
        help="Agent identifier for commands (default: agent)",
    )
    create_parser.add_argument(
        "--project",
        action="store_true",
        help="Create command in project directory instead of user directory",
    )
    create_parser.add_argument(
        "--global",
        dest="global_cmd",
        action="store_true",
        help="Create command in global directory (shared across agents)",
    )

    # Commands info
    info_parser = commands_subparsers.add_parser(
        "info",
        help="Show detailed information about a command",
        description="Show detailed information about a specific custom command",
    )
    info_parser.add_argument("name", help="Name of the command to show info for")
    info_parser.add_argument(
        "--agent",
        default="agent",
        help="Agent identifier for commands (default: agent)",
    )
    info_parser.add_argument(
        "--project",
        action="store_true",
        help="Search only in project commands",
    )

    return commands_parser


def execute_commands_command(args: argparse.Namespace) -> None:
    """Execute commands subcommands based on parsed arguments.

    Args:
        args: Parsed command line arguments with commands_command attribute
    """
    # Validate agent argument
    if hasattr(args, "agent") and args.agent:
        is_valid, error_msg = _validate_name(args.agent)
        if not is_valid:
            console.print(f"[bold red]Error:[/bold red] Invalid agent name: {error_msg}")
            console.print(
                "[dim]Agent names must only contain letters, numbers, hyphens, and underscores.[/dim]",
                style=COLORS["dim"],
            )
            return

    if args.commands_command == "list":
        _list(
            agent=args.agent,
            project=args.project,
            global_only=getattr(args, "global_only", False),
        )
    elif args.commands_command == "create":
        _create(
            args.name,
            agent=args.agent,
            index=args.index,
            project=args.project,
            global_cmd=getattr(args, "global_cmd", False),
        )
    elif args.commands_command == "info":
        _info(args.name, agent=args.agent, project=args.project)
    else:
        # No subcommand provided, show help
        console.print("[yellow]Please specify a commands subcommand: list, create, or info[/yellow]")
        console.print("\n[bold]Usage:[/bold]", style=COLORS["primary"])
        console.print("  deepagents commands <command> [options]\n")
        console.print("[bold]Available commands:[/bold]", style=COLORS["primary"])
        console.print("  list              List all available custom commands")
        console.print("  create <name>     Create a new custom command")
        console.print("  info <name>       Show detailed information about a command")
        console.print("\n[bold]Examples:[/bold]", style=COLORS["primary"])
        console.print("  deepagents commands list")
        console.print("  deepagents commands create review")
        console.print("  deepagents commands create deploy --project")
        console.print("  deepagents commands info review")
        console.print("\n[dim]For more help on a specific command:[/dim]", style=COLORS["dim"])
        console.print("  deepagents commands <command> --help", style=COLORS["dim"])


__all__ = [
    "execute_commands_command",
    "setup_commands_parser",
]
