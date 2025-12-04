"""Plan mode slash commands for the CLI."""

import logging
from typing import TYPE_CHECKING, Any

from deepagents.plan.types import PlanPhase

if TYPE_CHECKING:
    from rich.console import Console

logger = logging.getLogger(__name__)


def register_plan_commands() -> dict[str, Any]:
    """Register plan mode slash commands.

    Returns:
        Dictionary mapping command names to handler functions.

    Example:
        ```python
        from deepagents_cli.plan import register_plan_commands

        commands = register_plan_commands()
        handler = commands.get("plan")
        ```
    """
    return {
        "plan": handle_plan_command,
        "approve": handle_approve_command,
        "reject": handle_reject_command,
        "plan-status": handle_plan_status_command,
    }


def handle_plan_command(agent: Any, console: "Console", *args: str) -> bool:
    """Handle the /plan command to show current plan.

    Args:
        agent: The agent instance
        console: Rich Console instance for output
        args: Additional command arguments

    Returns:
        True to indicate command was handled
    """
    from deepagents_cli.plan.ui import render_plan

    # Try to get current plan from agent state
    current_plan = None
    if hasattr(agent, "checkpointer") and agent.checkpointer:
        try:
            # Get the latest state
            state = agent.get_state()
            if hasattr(state, "values"):
                current_plan = state.values.get("current_plan")
        except Exception as e:
            logger.debug("Could not retrieve plan from agent state: %s", e)

    if current_plan:
        console.print()
        render_plan(current_plan, console)
        console.print()
    else:
        console.print()
        console.print("[yellow]No active plan found.[/yellow]")
        console.print()
        console.print("[dim]Use the 'enter_plan_mode' tool to create a new plan.[/dim]")
        console.print()

    return True


def handle_approve_command(agent: Any, console: "Console", *args: str) -> bool:
    """Handle the /approve command to approve a plan.

    Args:
        agent: The agent instance
        console: Rich Console instance for output
        args: Additional command arguments

    Returns:
        True to indicate command was handled
    """
    # Try to get current plan from agent state
    current_plan = None
    if hasattr(agent, "checkpointer") and agent.checkpointer:
        try:
            state = agent.get_state()
            if hasattr(state, "values"):
                current_plan = state.values.get("current_plan")
        except Exception as e:
            logger.debug("Could not retrieve plan from agent state: %s", e)

    if not current_plan:
        console.print()
        console.print("[yellow]No active plan to approve.[/yellow]")
        console.print()
        return True

    if current_plan.phase != PlanPhase.AWAITING_APPROVAL:
        console.print()
        console.print(f"[yellow]Plan is in '{current_plan.phase.value}' phase, not awaiting approval.[/yellow]")
        console.print()
        return True

    # Approve the plan
    current_plan.approve()

    # Update the agent state
    try:
        state = agent.get_state()
        if hasattr(state, "values"):
            state.values["current_plan"] = current_plan
    except Exception as e:
        logger.warning("Could not update agent state with approved plan: %s", e)

    console.print()
    console.print("[green]✓ Plan approved![/green]")
    console.print()
    console.print(f"Ready to execute [bold]{len(current_plan.steps)}[/bold] steps.")
    console.print()
    console.print("[dim]The agent will now proceed with execution.[/dim]")
    console.print()

    return True


def handle_reject_command(agent: Any, console: "Console", *args: str) -> bool:
    """Handle the /reject command to reject a plan.

    Args:
        agent: The agent instance
        console: Rich Console instance for output
        args: Additional command arguments (reason for rejection)

    Returns:
        True to indicate command was handled
    """
    # Try to get current plan from agent state
    current_plan = None
    if hasattr(agent, "checkpointer") and agent.checkpointer:
        try:
            state = agent.get_state()
            if hasattr(state, "values"):
                current_plan = state.values.get("current_plan")
        except Exception as e:
            logger.debug("Could not retrieve plan from agent state: %s", e)

    if not current_plan:
        console.print()
        console.print("[yellow]No active plan to reject.[/yellow]")
        console.print()
        return True

    if current_plan.phase != PlanPhase.AWAITING_APPROVAL:
        console.print()
        console.print(f"[yellow]Plan is in '{current_plan.phase.value}' phase, not awaiting approval.[/yellow]")
        console.print()
        return True

    # Get rejection reason from args
    reason = " ".join(args) if args else "No reason provided"

    # Reject the plan
    current_plan.reject(reason)

    # Update the agent state
    try:
        state = agent.get_state()
        if hasattr(state, "values"):
            state.values["current_plan"] = current_plan
    except Exception as e:
        logger.warning("Could not update agent state with rejected plan: %s", e)

    console.print()
    console.print("[red]✗ Plan rejected.[/red]")
    console.print()
    console.print(f"Reason: {reason}")
    console.print()
    console.print("[dim]You can ask the agent to revise the plan or create a new one.[/dim]")
    console.print()

    return True


def handle_plan_status_command(agent: Any, console: "Console", *args: str) -> bool:
    """Handle the /plan-status command to show plan status.

    Args:
        agent: The agent instance
        console: Rich Console instance for output
        args: Additional command arguments

    Returns:
        True to indicate command was handled
    """
    from deepagents_cli.plan.ui import render_plan

    # Try to get current plan from agent state
    current_plan = None
    plan_mode_active = False

    if hasattr(agent, "checkpointer") and agent.checkpointer:
        try:
            state = agent.get_state()
            if hasattr(state, "values"):
                current_plan = state.values.get("current_plan")
                plan_mode_active = state.values.get("plan_mode_active", False)
        except Exception as e:
            logger.debug("Could not retrieve plan from agent state: %s", e)

    console.print()

    if not plan_mode_active:
        console.print("[dim]Plan mode is not active.[/dim]")
        console.print()
        return True

    if current_plan:
        render_plan(current_plan, console)

        # Show next steps based on phase
        if current_plan.phase == PlanPhase.PLANNING:
            console.print()
            console.print("[cyan]Currently in planning phase.[/cyan]")
            console.print("[dim]Agent is exploring the codebase and creating a plan.[/dim]")

        elif current_plan.phase == PlanPhase.AWAITING_APPROVAL:
            console.print()
            console.print("[yellow]Plan is awaiting approval.[/yellow]")
            console.print("[dim]Use /approve to approve or /reject to reject.[/dim]")

        elif current_plan.phase == PlanPhase.EXECUTING:
            console.print()
            console.print("[blue]Plan is being executed.[/blue]")
            completed, total = current_plan.progress
            console.print(f"[dim]Progress: {completed}/{total} steps completed[/dim]")

        elif current_plan.phase == PlanPhase.COMPLETED:
            console.print()
            console.print("[green]Plan execution completed![/green]")

        elif current_plan.phase == PlanPhase.REJECTED:
            console.print()
            console.print("[red]Plan was rejected.[/red]")

    else:
        console.print("[yellow]Plan mode is active but no plan found.[/yellow]")
        console.print("[dim]Ask the agent to create a plan using enter_plan_mode.[/dim]")

    console.print()
    return True
