"""UI utilities for rendering plans."""

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from deepagents.plan.types import Plan, PlanPhase, PlanStep, PlanStepStatus


def render_plan(plan: Plan, console: Console | None = None) -> None:
    """Render a plan in a formatted, readable way.

    Args:
        plan: The Plan object to render
        console: Optional Rich Console instance. Creates new one if not provided.

    Example:
        ```python
        from deepagents.plan.types import Plan
        from deepagents_cli.plan import render_plan

        plan = Plan(title="Implement feature X", ...)
        render_plan(plan)
        ```
    """
    if console is None:
        console = Console()

    # Create header
    phase_color = _get_phase_color(plan.phase)
    title = Text()
    title.append(plan.title, style="bold cyan")
    title.append(f" [{plan.phase.value}]", style=f"bold {phase_color}")

    # Create panel content
    content = []

    # Goal
    if plan.goal:
        content.append(Text("Goal: ", style="bold") + Text(plan.goal))
        content.append("")

    # Description
    if plan.description:
        content.append(Text("Description:", style="bold"))
        content.append(Text(plan.description))
        content.append("")

    # Progress
    if plan.steps:
        completed, total = plan.progress
        progress_text = Text("Progress: ", style="bold")
        progress_text.append(f"{completed}/{total} steps completed")

        if plan.phase == PlanPhase.COMPLETED:
            progress_text.append(" ✓", style="green")

        content.append(progress_text)
        content.append("")

    # Steps table
    if plan.steps:
        content.append(Text("Steps:", style="bold"))
        content.append("")

        table = Table(show_header=True, header_style="bold", box=None, padding=(0, 1))
        table.add_column("#", style="dim", width=3)
        table.add_column("Status", width=12)
        table.add_column("Title")
        table.add_column("Files", style="dim")

        for i, step in enumerate(plan.steps, 1):
            status_text = _render_step_status(step.status)
            files_text = _render_step_files(step)

            table.add_row(str(i), status_text, step.title, files_text)

        # Convert table to string and add to content
        from io import StringIO

        string_io = StringIO()
        temp_console = Console(file=string_io, width=console.width - 4)
        temp_console.print(table)
        content.append(Text(string_io.getvalue()))

    # Architecture notes
    if plan.architecture_notes:
        content.append("")
        content.append(Text("Architecture Notes:", style="bold"))
        content.append(Text(plan.architecture_notes, style="dim"))

    # Risks
    if plan.risks:
        content.append("")
        content.append(Text("Risks:", style="bold yellow"))
        for risk in plan.risks:
            content.append(Text(f"  ⚠ {risk}", style="yellow"))

    # Render the panel
    panel = Panel(
        Text("\n").join(content),
        title=title,
        border_style=phase_color,
        padding=(1, 2),
    )
    console.print(panel)


def render_plan_approval_prompt(plan: Plan, console: Console | None = None) -> None:
    """Render a plan approval prompt.

    Args:
        plan: The Plan object awaiting approval
        console: Optional Rich Console instance. Creates new one if not provided.

    Example:
        ```python
        from deepagents.plan.types import Plan
        from deepagents_cli.plan import render_plan_approval_prompt

        plan = Plan(title="Implement feature X", ...)
        render_plan_approval_prompt(plan)
        ```
    """
    if console is None:
        console = Console()

    # Render the full plan
    render_plan(plan, console)

    # Add approval prompt
    console.print()
    console.print("[bold cyan]Plan awaiting approval[/bold cyan]")
    console.print()
    console.print("Commands:")
    console.print("  [bold]/approve[/bold]  - Approve this plan and begin execution")
    console.print("  [bold]/reject[/bold]   - Reject this plan and return to planning")
    console.print("  [bold]/plan-status[/bold] - Show current plan status")
    console.print()


def _get_phase_color(phase: PlanPhase) -> str:
    """Get the color for a plan phase.

    Args:
        phase: The PlanPhase enum value

    Returns:
        Color string for Rich styling
    """
    color_map = {
        PlanPhase.IDLE: "dim",
        PlanPhase.PLANNING: "cyan",
        PlanPhase.AWAITING_APPROVAL: "yellow",
        PlanPhase.EXECUTING: "blue",
        PlanPhase.COMPLETED: "green",
        PlanPhase.REJECTED: "red",
    }
    return color_map.get(phase, "white")


def _render_step_status(status: PlanStepStatus) -> str:
    """Render a step status with icon and color.

    Args:
        status: The PlanStepStatus enum value

    Returns:
        Formatted status string with Rich styling
    """
    status_map = {
        PlanStepStatus.PENDING: "[dim]○ Pending[/dim]",
        PlanStepStatus.IN_PROGRESS: "[blue]◐ In Progress[/blue]",
        PlanStepStatus.COMPLETED: "[green]● Completed[/green]",
        PlanStepStatus.SKIPPED: "[yellow]○ Skipped[/yellow]",
        PlanStepStatus.FAILED: "[red]✗ Failed[/red]",
    }
    return status_map.get(status, str(status))


def _render_step_files(step: PlanStep) -> str:
    """Render the files involved in a step.

    Args:
        step: The PlanStep object

    Returns:
        Formatted string listing files
    """
    files = []

    if step.files_to_create:
        files.extend(f"+{f}" for f in step.files_to_create[:2])

    if step.files_to_modify:
        files.extend(f"~{f}" for f in step.files_to_modify[:2])

    total_files = len(step.files_to_create) + len(step.files_to_modify)
    if total_files > 2:
        files.append(f"... +{total_files - 2} more")

    return ", ".join(files) if files else ""
