"""Command handlers for slash commands and bash execution."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

from langgraph.checkpoint.memory import InMemorySaver

from .config import COLORS, DEEP_AGENTS_ASCII, console, settings
from .plan.commands import register_plan_commands
from .ui import TokenTracker, show_interactive_help

if TYPE_CHECKING:
    from .custom_commands import CommandRegistry

# Register plan commands
PLAN_COMMANDS = register_plan_commands()


def handle_command(
    command: str,
    agent,
    token_tracker: TokenTracker,
    command_registry: "CommandRegistry | None" = None,
) -> str | bool | tuple[bool, str]:
    """Handle slash commands.

    Args:
        command: The command string (with leading slash).
        agent: The agent instance.
        token_tracker: Token usage tracker.
        command_registry: Optional registry for custom commands.

    Returns:
        - 'exit' to exit the CLI
        - True if command was handled (no further action needed)
        - False to pass to agent (not used currently)
        - (True, prompt) for custom commands that expand to a prompt
    """
    from .custom_commands import handle_custom_command, parse_command_line

    # Parse command and arguments
    cmd_name, cmd_args = parse_command_line(command)

    # Built-in commands (highest priority)
    if cmd_name in ["quit", "exit", "q"]:
        return "exit"

    if cmd_name == "clear":
        # Reset agent conversation state
        agent.checkpointer = InMemorySaver()

        # Reset token tracking to baseline
        token_tracker.reset()

        # Clear screen and show fresh UI
        console.clear()
        console.print(DEEP_AGENTS_ASCII, style=f"bold {COLORS['primary']}")
        console.print()
        console.print(
            "... Fresh start! Screen cleared and conversation reset.", style=COLORS["agent"]
        )
        console.print()
        return True

    if cmd_name == "help":
        show_interactive_help(command_registry=command_registry)
        return True

    if cmd_name == "tokens":
        token_tracker.display_session()
        return True

    # Check plan commands
    if cmd_name in PLAN_COMMANDS:
        handler = PLAN_COMMANDS[cmd_name]
        return handler(agent, console)

    # Check custom commands
    if command_registry:
        handled, expanded_prompt = handle_custom_command(
            command_name=cmd_name,
            args=cmd_args,
            registry=command_registry,
            console=console,
            project_root=str(settings.project_root) if settings.project_root else None,
            cwd=str(Path.cwd()),
        )
        if handled:
            if expanded_prompt:
                return (True, expanded_prompt)
            return True

    console.print()
    console.print(f"[yellow]Unknown command: /{cmd_name}[/yellow]")
    console.print("[dim]Type /help for available commands.[/dim]")
    console.print()
    return True


def execute_bash_command(command: str) -> bool:
    """Execute a bash command and display output. Returns True if handled."""
    cmd = command.strip().lstrip("!")

    if not cmd:
        return True

    try:
        console.print()
        console.print(f"[dim]$ {cmd}[/dim]")

        # Execute the command
        result = subprocess.run(
            cmd, check=False, shell=True, capture_output=True, text=True, timeout=30, cwd=Path.cwd()
        )

        # Display output
        if result.stdout:
            console.print(result.stdout, style=COLORS["dim"], markup=False)
        if result.stderr:
            console.print(result.stderr, style="red", markup=False)

        # Show return code if non-zero
        if result.returncode != 0:
            console.print(f"[dim]Exit code: {result.returncode}[/dim]")

        console.print()
        return True

    except subprocess.TimeoutExpired:
        console.print("[red]Command timed out after 30 seconds[/red]")
        console.print()
        return True
    except Exception as e:
        console.print(f"[red]Error executing command: {e}[/red]")
        console.print()
        return True
