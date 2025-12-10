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


async def _handle_delete_session_async(args: list[str]) -> bool:
    """Handle /delete command to remove a session (async version).

    Args:
        args: Command arguments (session ID prefix or search term, or empty for picker).

    Returns:
        True when handled.
    """
    from deepagents_cli.sessions import create_session_manager
    from deepagents_cli.sessions.picker import pick_session_for_delete_async

    sm = create_session_manager()
    sessions = sm.list_sessions(limit=50)

    if not sessions:
        console.print()
        console.print("[yellow]No sessions found.[/yellow]")
        console.print()
        return True

    target_session = None

    # If no args, show interactive picker
    if not args:
        target_session = await pick_session_for_delete_async(sessions)
        if not target_session:
            console.print("[dim]No session selected.[/dim]")
            console.print()
            return True
    else:
        # Try to match by ID prefix or summary
        search_term = " ".join(args).lower()

        # First try matching by ID prefix
        for session in sessions:
            if session.session_id.lower().startswith(search_term):
                target_session = session
                break

        # Then try matching by summary content
        if not target_session:
            for session in sessions:
                if search_term in session.summary.lower():
                    target_session = session
                    break

        if not target_session:
            console.print()
            console.print(f"[yellow]No session found matching: {search_term}[/yellow]")
            console.print("[dim]Type /sessions to list, or /delete for picker.[/dim]")
            console.print()
            return True

    # Delete the session
    console.print()
    console.print(f"[red]Deleting session:[/red] {target_session.summary[:50]}...")
    console.print(f"[dim]  ID: {target_session.session_id[:8]}...[/dim]")

    if sm.delete_session(target_session.session_id):
        console.print("[green]✓ Session deleted successfully.[/green]")
    else:
        console.print("[red]✗ Failed to delete session.[/red]")

    console.print()
    return True


async def _handle_resume_command_async(args: list[str]) -> tuple[str, str] | bool:
    """Handle /resume command with optional session ID or picker (async version).

    Args:
        args: Command arguments (session ID prefix or empty for picker).

    Returns:
        - ("resume", session_id) to signal session switch
        - True if handled without switching
    """
    from deepagents_cli.sessions import create_session_manager
    from deepagents_cli.sessions.picker import pick_session_async

    sm = create_session_manager()
    sessions = sm.list_sessions(limit=20)

    if not sessions:
        console.print()
        console.print("[yellow]No previous sessions found.[/yellow]")
        console.print()
        return True

    # If no args, show interactive picker
    if not args:
        selected = await pick_session_async(sessions)
        if selected:
            return ("resume", selected.session_id)
        console.print("[dim]No session selected.[/dim]")
        console.print()
        return True

    # Try to match session by ID prefix or summary
    search_term = " ".join(args).lower()

    # First try matching by ID prefix
    for session in sessions:
        if session.session_id.lower().startswith(search_term):
            return ("resume", session.session_id)

    # Then try matching by summary content
    for session in sessions:
        if search_term in session.summary.lower():
            return ("resume", session.session_id)

    console.print()
    console.print(f"[yellow]No session found matching: {search_term}[/yellow]")
    console.print("[dim]Type /sessions to list available sessions.[/dim]")
    console.print()
    return True


def _show_sessions_list() -> None:
    """Show list of recent sessions."""
    from deepagents_cli.sessions import create_session_manager

    console.print()
    console.print("[bold cyan]Recent Sessions[/bold cyan]")
    console.print()

    sm = create_session_manager()
    sessions = sm.list_sessions(limit=10)

    if not sessions:
        console.print("[dim]No previous sessions found.[/dim]")
        console.print()
        return

    for i, session in enumerate(sessions):
        # Format time ago
        from datetime import datetime

        try:
            dt = datetime.fromisoformat(session.updated_at)
            now = datetime.now()
            delta = now - dt
            if delta.days > 0:
                time_ago = f"{delta.days}d ago"
            elif delta.seconds > 3600:
                time_ago = f"{delta.seconds // 3600}h ago"
            elif delta.seconds > 60:
                time_ago = f"{delta.seconds // 60}m ago"
            else:
                time_ago = "just now"
        except (ValueError, TypeError):
            time_ago = "unknown"

        # Truncate summary
        summary = session.summary[:45]
        if len(session.summary) > 45:
            summary += "..."

        # Show session info
        prefix = "→ " if i == 0 else "  "
        console.print(
            f"{prefix}[cyan]{session.session_id[:8]}[/cyan] "
            f"{summary} [dim]({session.message_count} msgs, {time_ago})[/dim]"
        )

    console.print()
    console.print("[dim]To resume: deepagents --resume {session_id}[/dim]")
    console.print("[dim]Or use: deepagents --resume (interactive picker)[/dim]")
    console.print()


async def handle_command(
    command: str,
    agent,
    token_tracker: TokenTracker,
    command_registry: "CommandRegistry | None" = None,
) -> str | bool | tuple[str, str] | tuple[bool, str]:
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
        - ("resume", session_id) to switch sessions
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

    if cmd_name == "resume":
        return await _handle_resume_command_async(cmd_args)

    if cmd_name == "sessions":
        _show_sessions_list()
        return True

    if cmd_name == "delete":
        return await _handle_delete_session_async(cmd_args)

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
