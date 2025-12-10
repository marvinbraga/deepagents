"""Main entry point and CLI loop for deepagents."""

import argparse
import asyncio
import logging
import os
import sys
from pathlib import Path

# Suppress noisy MCP/SDK warnings during initialization
logging.getLogger("root").setLevel(logging.CRITICAL)
logging.getLogger("mcp").setLevel(logging.CRITICAL)
logging.getLogger("deepagents.mcp").setLevel(logging.CRITICAL)
logging.getLogger("httpx").setLevel(logging.CRITICAL)
logging.getLogger("httpcore").setLevel(logging.CRITICAL)
logging.getLogger("serena").setLevel(logging.CRITICAL)
# Suppress all WARNING level logs by default
logging.basicConfig(level=logging.CRITICAL)

from deepagents.backends.protocol import SandboxBackendProtocol

from deepagents_cli.agent import create_cli_agent, list_agents, reset_agent
from deepagents_cli.commands import execute_bash_command, handle_command
from deepagents_cli.config import (
    COLORS,
    DEEP_AGENTS_ASCII,
    SessionState,
    console,
    create_model,
    settings,
)
from deepagents_cli.custom_commands import create_command_registry
from deepagents_cli.custom_commands.cli_commands import (
    execute_commands_command,
    setup_commands_parser,
)
from deepagents_cli.execution import execute_task
from deepagents_cli.input import create_prompt_session
from deepagents_cli.integrations.sandbox_factory import (
    create_sandbox,
    get_default_working_dir,
)
from deepagents_cli.skills import execute_skills_command, setup_skills_parser
from deepagents_cli.tools import fetch_url, http_request, web_search
from deepagents_cli.ui import TokenTracker, show_help


def check_cli_dependencies() -> None:
    """Check if CLI optional dependencies are installed."""
    missing = []

    try:
        import rich
    except ImportError:
        missing.append("rich")

    try:
        import requests
    except ImportError:
        missing.append("requests")

    try:
        import dotenv
    except ImportError:
        missing.append("python-dotenv")

    # duckduckgo-search is optional - web search will gracefully degrade if not installed

    try:
        import prompt_toolkit
    except ImportError:
        missing.append("prompt-toolkit")

    if missing:
        print("\n❌ Missing required CLI dependencies!")
        print("\nThe following packages are required to use the deepagents CLI:")
        for pkg in missing:
            print(f"  - {pkg}")
        print("\nPlease install them with:")
        print("  pip install deepagents[cli]")
        print("\nOr install all dependencies:")
        print("  pip install 'deepagents[cli]'")
        sys.exit(1)


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="DeepAgents - AI Coding Assistant",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        add_help=False,
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # List command
    subparsers.add_parser("list", help="List all available agents")

    # Help command
    subparsers.add_parser("help", help="Show help information")

    # Reset command
    reset_parser = subparsers.add_parser("reset", help="Reset an agent")
    reset_parser.add_argument("--agent", required=True, help="Name of agent to reset")
    reset_parser.add_argument(
        "--target", dest="source_agent", help="Copy prompt from another agent"
    )

    # Skills command - setup delegated to skills module
    setup_skills_parser(subparsers)

    # Commands command - setup delegated to custom_commands module
    setup_commands_parser(subparsers)

    # Default interactive mode
    parser.add_argument(
        "--agent",
        default="agent",
        help="Agent identifier for separate memory stores (default: agent).",
    )
    parser.add_argument(
        "--auto-approve",
        action="store_true",
        help="Auto-approve tool usage without prompting (disables human-in-the-loop)",
    )
    parser.add_argument(
        "--sandbox",
        choices=["none", "modal", "daytona", "runloop"],
        default="none",
        help="Remote sandbox for code execution (default: none - local only)",
    )
    parser.add_argument(
        "--sandbox-id",
        help="Existing sandbox ID to reuse (skips creation and cleanup)",
    )
    parser.add_argument(
        "--sandbox-setup",
        help="Path to setup script to run in sandbox after creation",
    )
    parser.add_argument(
        "--no-splash",
        action="store_true",
        help="Disable the startup splash screen",
    )
    parser.add_argument(
        "--ultrathink",
        action="store_true",
        help="Enable extended thinking mode (Claude 4+ only)",
    )
    parser.add_argument(
        "--ultrathink-budget",
        type=int,
        default=10000,
        help="Token budget for extended thinking (default: 10000, range: 1024-128000)",
    )

    # Session resumption arguments
    parser.add_argument(
        "--resume",
        "-r",
        nargs="?",
        const="__picker__",
        metavar="SESSION_ID",
        help="Resume a previous session (interactive picker if no ID provided)",
    )
    parser.add_argument(
        "--continue",
        "-c",
        dest="continue_session",
        action="store_true",
        help="Continue the most recent session automatically",
    )

    return parser.parse_args()


async def simple_cli(
    agent,
    assistant_id: str | None,
    session_state,
    baseline_tokens: int = 0,
    backend=None,
    sandbox_type: str | None = None,
    setup_script_path: str | None = None,
    no_splash: bool = False,
    enable_ultrathink: bool = False,
    ultrathink_budget: int = 10000,
    agent_name: str = "agent",
    command_registry=None,
    session_manager=None,
    session_id: str | None = None,
) -> None:
    """Main CLI loop.

    Args:
        backend: Backend for file operations (CompositeBackend)
        sandbox_type: Type of sandbox being used (e.g., "modal", "runloop", "daytona").
                     If None, running in local mode.
        sandbox_id: ID of the active sandbox
        setup_script_path: Path to setup script that was run (if any)
        no_splash: If True, skip displaying the startup splash screen
        enable_ultrathink: Whether extended thinking mode is enabled
        ultrathink_budget: Token budget for extended thinking
        agent_name: Agent identifier for loading agent-specific commands
        command_registry: CommandRegistry instance for custom slash commands
        session_manager: SessionManager for persistent session tracking
        session_id: Current session ID for updating metadata
    """
    console.clear()
    if not no_splash:
        console.print(DEEP_AGENTS_ASCII, style=f"bold {COLORS['primary']}")
        console.print()

    # Extract sandbox ID from backend if using sandbox mode
    sandbox_id: str | None = None
    if backend:
        from deepagents.backends.composite import CompositeBackend

        # Check if it's a CompositeBackend with a sandbox default backend
        if isinstance(backend, CompositeBackend):
            if isinstance(backend.default, SandboxBackendProtocol):
                sandbox_id = backend.default.id
        elif isinstance(backend, SandboxBackendProtocol):
            sandbox_id = backend.id

    # Display sandbox info persistently (survives console.clear())
    if sandbox_type and sandbox_id:
        console.print(f"[yellow]⚡ {sandbox_type.capitalize()} sandbox: {sandbox_id}[/yellow]")
        if setup_script_path:
            console.print(
                f"[green]✓ Setup script ({setup_script_path}) completed successfully[/green]"
            )
        console.print()

    # Check if web search is available (duckduckgo-search installed)
    try:
        from deepagents.middleware.web import web_search_sync  # noqa: F401

        web_search_available = True
    except ImportError:
        web_search_available = False

    if not web_search_available:
        console.print(
            "[yellow]⚠ Web search disabled:[/yellow] duckduckgo-search not installed.",
            style=COLORS["dim"],
        )
        console.print("  To enable web search (no API key required):", style=COLORS["dim"])
        console.print("    pip install duckduckgo-search", style=COLORS["dim"])
        console.print()

    console.print("... Ready to code! What would you like to build?", style=COLORS["agent"])

    if sandbox_type:
        working_dir = get_default_working_dir(sandbox_type)
        console.print(f"  [dim]Local CLI directory: {Path.cwd()}[/dim]")
        console.print(f"  [dim]Code execution: Remote sandbox ({working_dir})[/dim]")
    else:
        console.print(f"  [dim]Working directory: {Path.cwd()}[/dim]")

    console.print()

    if session_state.auto_approve:
        console.print(
            "  [yellow]⚡ Auto-approve: ON[/yellow] [dim](tools run without confirmation)[/dim]"
        )
        console.print()

    if enable_ultrathink:
        console.print(
            f"  [cyan]🧠 Ultrathink: ON[/cyan] [dim](budget: {ultrathink_budget:,} tokens)[/dim]"
        )
        console.print()

    # Localize modifier names and show key symbols (macOS vs others)
    if sys.platform == "darwin":
        tips = (
            "  Tips: ⏎ Enter to submit, ⌥ Option + ⏎ Enter for newline (or Esc+Enter), "
            "⌃E to open editor, ⌃T to toggle auto-approve, ⌃C to interrupt"
        )
    else:
        tips = (
            "  Tips: Enter to submit, Alt+Enter (or Esc+Enter) for newline, "
            "Ctrl+E to open editor, Ctrl+T to toggle auto-approve, Ctrl+C to interrupt"
        )
    console.print(tips, style=f"dim {COLORS['dim']}")

    console.print()

    # Use provided command registry or create one if not provided
    if command_registry is None:
        command_registry = create_command_registry(settings, agent_name)

    # Create prompt session and token tracker
    session = create_prompt_session(assistant_id, session_state, command_registry)
    token_tracker = TokenTracker()
    token_tracker.set_baseline(baseline_tokens)

    # Track message count for session updates
    message_count = 0
    first_user_message = None

    while True:
        try:
            user_input = await session.prompt_async()
            if session_state.exit_hint_handle:
                session_state.exit_hint_handle.cancel()
                session_state.exit_hint_handle = None
            session_state.exit_hint_until = None
            user_input = user_input.strip()
        except EOFError:
            break
        except KeyboardInterrupt:
            console.print("\nGoodbye!", style=COLORS["primary"])
            break

        if not user_input:
            continue

        # Check for slash commands first
        if user_input.startswith("/"):
            result = await handle_command(user_input, agent, token_tracker, command_registry)
            if result == "exit":
                console.print("\nGoodbye!", style=COLORS["primary"])
                break
            # Check if result is a tuple
            if isinstance(result, tuple) and len(result) == 2:
                signal, value = result
                # Handle resume signal - return to restart with new session
                if signal == "resume":
                    return ("resume", value)
                # Handle custom command with expanded prompt
                if signal is True and value:
                    await execute_task(
                        value,
                        agent,
                        assistant_id,
                        session_state,
                        token_tracker,
                        backend=backend,
                    )
                continue
            if result:
                # Command was handled, continue to next input
                continue

        # Check for bash commands (!)
        if user_input.startswith("!"):
            execute_bash_command(user_input)
            continue

        # Handle regular quit keywords
        if user_input.lower() in ["quit", "exit", "q"]:
            console.print("\nGoodbye!", style=COLORS["primary"])
            break

        # Update session tracking
        message_count += 1
        if first_user_message is None:
            first_user_message = user_input[:100]  # Truncate for summary
            # Update session summary with first message
            if session_manager and session_id:
                session_manager.update_session(
                    session_id,
                    summary=first_user_message,
                    message_count=message_count,
                )

        await execute_task(
            user_input, agent, assistant_id, session_state, token_tracker, backend=backend
        )

        # Update message count periodically
        if session_manager and session_id and message_count % 5 == 0:
            session_manager.update_session(session_id, message_count=message_count)


async def _run_agent_session(
    model,
    assistant_id: str,
    session_state,
    sandbox_backend=None,
    sandbox_type: str | None = None,
    setup_script_path: str | None = None,
    enable_ultrathink: bool = False,
    ultrathink_budget: int = 10000,
    resume_session_id: str | None = None,
) -> None:
    """Helper to create agent and run CLI session.

    Extracted to avoid duplication between sandbox and local modes.
    Supports session switching via /resume command.

    Args:
        model: LLM model to use
        assistant_id: Agent identifier for memory storage
        session_state: Session state with auto-approve settings
        sandbox_backend: Optional sandbox backend for remote execution
        sandbox_type: Type of sandbox being used
        setup_script_path: Path to setup script that was run (if any)
        enable_ultrathink: Whether to enable extended thinking mode
        ultrathink_budget: Token budget for extended thinking
        resume_session_id: Optional session ID to resume
    """
    from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

    from deepagents_cli.custom_commands import create_slash_command_tool
    from deepagents_cli.sessions import create_session_manager

    # Create command registry for custom slash commands
    command_registry = create_command_registry(settings, assistant_id)

    # Create agent with tools (web_search uses DuckDuckGo, no API key needed)
    tools = [http_request, fetch_url, web_search]

    # Add SlashCommandTool for programmatic command execution
    project_root = str(settings.project_root) if settings.project_root else str(Path.cwd())
    slash_command_tool = create_slash_command_tool(
        registry=command_registry,
        project_root=project_root,
        cwd=str(Path.cwd()),
    )
    tools.append(slash_command_tool)

    # Initialize MCP servers asynchronously (non-blocking)
    mcp_middleware = None
    try:
        from deepagents_cli.mcp import (
            MCPManager,
            load_mcp_config,
            set_mcp_manager,
        )

        mcp_configs = load_mcp_config()
        if mcp_configs:
            enabled_count = sum(1 for c in mcp_configs if c.enabled)
            if enabled_count > 0:
                console.print(f"[dim]Starting {enabled_count} MCP server(s) in background...[/dim]")
                manager = MCPManager.from_configs(mcp_configs)
                set_mcp_manager(manager)
                # Start async initialization - does not block
                manager.start_async_init()
    except ImportError:
        pass  # MCP not available
    except Exception as e:
        console.print(f"[yellow]⚠ MCP setup error: {e}[/yellow]")

    # Setup session management for persistence
    session_mgr = create_session_manager()

    # Session loop - allows switching sessions via /resume
    current_resume_id = resume_session_id
    is_first_session = True

    while True:
        current_session_id = None
        db_path = None

        if current_resume_id:
            # Resume existing session
            db_path = session_mgr.get_session_db_path_by_id(current_resume_id)
            if db_path:
                current_session_id = current_resume_id
                session_state.thread_id = current_resume_id
                # Show resume message
                info = session_mgr.get_session_info(current_resume_id)
                if info:
                    console.print()
                    console.print(f"[cyan]↩ Resuming session:[/cyan] {info.summary[:50]}...")
                    console.print(
                        f"[dim]  ID: {current_session_id[:8]}... | "
                        f"{info.message_count} messages[/dim]"
                    )
                    console.print()
            else:
                console.print(
                    f"[yellow]Warning: Could not load session {current_resume_id}[/yellow]"
                )

        if not db_path:
            # Create new persistent session
            current_session_id, db_path = session_mgr.create_session(
                agent_name=assistant_id,
                project_path=project_root,
            )
            session_state.thread_id = current_session_id

        # Use AsyncSqliteSaver as async context manager for persistent checkpointing
        async with AsyncSqliteSaver.from_conn_string(str(db_path)) as checkpointer:
            agent, composite_backend = create_cli_agent(
                model=model,
                assistant_id=assistant_id,
                tools=tools,
                sandbox=sandbox_backend,
                sandbox_type=sandbox_type,
                auto_approve=session_state.auto_approve,
                enable_mcp=mcp_middleware is not None,
                enable_ultrathink=enable_ultrathink,
                ultrathink_budget=ultrathink_budget,
                checkpointer=checkpointer,
                mcp_middleware=mcp_middleware,
            )

            # Calculate baseline token count for accurate token tracking
            from .agent import get_system_prompt
            from .token_utils import calculate_baseline_tokens

            agent_dir = settings.get_agent_dir(assistant_id)
            system_prompt = get_system_prompt(assistant_id=assistant_id, sandbox_type=sandbox_type)
            baseline_tokens = calculate_baseline_tokens(
                model, agent_dir, system_prompt, assistant_id
            )

            # Run CLI and check for session switch signal
            result = await simple_cli(
                agent,
                assistant_id,
                session_state,
                baseline_tokens,
                backend=composite_backend,
                sandbox_type=sandbox_type,
                setup_script_path=setup_script_path if is_first_session else None,
                no_splash=session_state.no_splash or not is_first_session,
                enable_ultrathink=enable_ultrathink,
                ultrathink_budget=ultrathink_budget,
                agent_name=assistant_id,
                command_registry=command_registry,
                session_manager=session_mgr,
                session_id=current_session_id,
            )

            # Check if we need to switch sessions
            if isinstance(result, tuple) and result[0] == "resume":
                current_resume_id = result[1]
                is_first_session = False
                continue  # Loop to start new session

            # Normal exit
            break


async def main(
    assistant_id: str,
    session_state,
    sandbox_type: str = "none",
    sandbox_id: str | None = None,
    setup_script_path: str | None = None,
    enable_ultrathink: bool = False,
    ultrathink_budget: int = 10000,
    resume_session_id: str | None = None,
) -> None:
    """Main entry point with conditional sandbox support.

    Args:
        assistant_id: Agent identifier for memory storage
        session_state: Session state with auto-approve settings
        sandbox_type: Type of sandbox ("none", "modal", "runloop", "daytona")
        sandbox_id: Optional existing sandbox ID to reuse
        setup_script_path: Optional path to setup script to run in sandbox
        enable_ultrathink: Whether to enable extended thinking mode
        ultrathink_budget: Token budget for extended thinking
        resume_session_id: Optional session ID to resume
    """
    model = create_model()

    # Branch 1: User wants a sandbox
    if sandbox_type != "none":
        # Try to create sandbox
        try:
            console.print()
            with create_sandbox(
                sandbox_type, sandbox_id=sandbox_id, setup_script_path=setup_script_path
            ) as sandbox_backend:
                console.print(f"[yellow]⚡ Remote execution enabled ({sandbox_type})[/yellow]")
                console.print()

                await _run_agent_session(
                    model,
                    assistant_id,
                    session_state,
                    sandbox_backend,
                    sandbox_type=sandbox_type,
                    setup_script_path=setup_script_path,
                    enable_ultrathink=enable_ultrathink,
                    ultrathink_budget=ultrathink_budget,
                    resume_session_id=resume_session_id,
                )
        except (ImportError, ValueError, RuntimeError, NotImplementedError) as e:
            # Sandbox creation failed - fail hard (no silent fallback)
            console.print()
            console.print("[red]❌ Sandbox creation failed[/red]")
            console.print(f"[dim]{e}[/dim]")
            sys.exit(1)
        except KeyboardInterrupt:
            console.print("\n\n[yellow]Interrupted[/yellow]")
            sys.exit(0)
        except Exception as e:
            console.print(f"\n[bold red]❌ Error:[/bold red] {e}\n")
            console.print_exception()
            sys.exit(1)

    # Branch 2: User wants local mode (none or default)
    else:
        try:
            await _run_agent_session(
                model,
                assistant_id,
                session_state,
                sandbox_backend=None,
                enable_ultrathink=enable_ultrathink,
                ultrathink_budget=ultrathink_budget,
                resume_session_id=resume_session_id,
            )
        except KeyboardInterrupt:
            console.print("\n\n[yellow]Interrupted[/yellow]")
            sys.exit(0)
        except Exception as e:
            console.print(f"\n[bold red]❌ Error:[/bold red] {e}\n")
            console.print_exception()
            sys.exit(1)


def cli_main() -> None:
    """Entry point for console script."""
    # Fix for gRPC fork issue on macOS
    # https://github.com/grpc/grpc/issues/37642
    if sys.platform == "darwin":
        os.environ["GRPC_ENABLE_FORK_SUPPORT"] = "0"

    # Check dependencies first
    check_cli_dependencies()

    try:
        args = parse_args()

        if args.command == "help":
            show_help()
        elif args.command == "list":
            list_agents()
        elif args.command == "reset":
            reset_agent(args.agent, args.source_agent)
        elif args.command == "skills":
            execute_skills_command(args)
        elif args.command == "commands":
            execute_commands_command(args)
        else:
            # Create session state from args
            session_state = SessionState(auto_approve=args.auto_approve, no_splash=args.no_splash)

            # Handle session resume/continue
            resume_session_id = None
            if args.continue_session:
                # Continue most recent session
                from deepagents_cli.sessions import create_session_manager

                session_mgr = create_session_manager()
                recent = session_mgr.get_most_recent_session(agent_name=args.agent)
                if recent:
                    resume_session_id = recent.session_id
                    console.print(f"[dim]Continuing session: {recent.summary[:50]}...[/dim]")
                else:
                    console.print(
                        "[yellow]No previous session found. Starting new session.[/yellow]"
                    )

            elif args.resume:
                from deepagents_cli.sessions import create_session_manager
                from deepagents_cli.sessions.picker import pick_session

                session_mgr = create_session_manager()

                if args.resume == "__picker__":
                    # Interactive picker
                    sessions = session_mgr.list_sessions(limit=20, agent_name=args.agent)
                    if sessions:
                        selected = pick_session(sessions)
                        if selected:
                            resume_session_id = selected.session_id
                            console.print(f"[dim]Resuming: {selected.summary[:50]}...[/dim]")
                        else:
                            console.print(
                                "[yellow]No session selected. Starting new session.[/yellow]"
                            )
                    else:
                        console.print(
                            "[yellow]No previous sessions found. Starting new session.[/yellow]"
                        )
                else:
                    # Resume specific session by ID
                    info = session_mgr.get_session_info(args.resume)
                    if info:
                        resume_session_id = args.resume
                        console.print(f"[dim]Resuming: {info.summary[:50]}...[/dim]")
                    else:
                        console.print(f"[red]Session not found: {args.resume}[/red]")
                        sys.exit(1)

            # API key validation happens in create_model()
            asyncio.run(
                main(
                    args.agent,
                    session_state,
                    args.sandbox,
                    args.sandbox_id,
                    args.sandbox_setup,
                    enable_ultrathink=args.ultrathink,
                    ultrathink_budget=args.ultrathink_budget,
                    resume_session_id=resume_session_id,
                )
            )
    except KeyboardInterrupt:
        # Clean exit on Ctrl+C - suppress ugly traceback
        console.print("\n\n[yellow]Interrupted[/yellow]")
        sys.exit(0)


if __name__ == "__main__":
    cli_main()
