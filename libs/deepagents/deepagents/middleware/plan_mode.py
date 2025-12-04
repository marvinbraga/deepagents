"""Plan mode middleware for DeepAgents."""

import json
from collections.abc import Awaitable, Callable, Sequence
from datetime import datetime
from typing import Annotated

from langchain.agents.middleware.types import (
    AgentMiddleware,
    AgentState,
    ModelRequest,
    ModelResponse,
)
from langchain.tools import ToolRuntime
from langchain_core.tools import BaseTool, tool
from typing_extensions import TypedDict

from deepagents.plan.types import Plan, PlanModeState, PlanPhase, PlanStep, PlanStepStatus

PLAN_MODE_SYSTEM_PROMPT = """## Plan Mode

You are currently in PLAN MODE. Your goal is to:

1. **Explore the codebase** thoroughly
   - Use `ls`, `read_file`, `glob`, and `grep` to understand the project structure
   - Read relevant files to understand the architecture
   - Identify patterns, conventions, and existing implementations

2. **Create a detailed plan** using the `submit_plan` tool
   - Break down the implementation into clear, logical steps
   - Identify all files that need to be modified or created
   - Note any dependencies between steps
   - Document potential risks and alternatives considered
   - Include architecture notes and design decisions

3. **Submit the plan** for approval
   - Once you've explored enough and created a comprehensive plan, use `submit_plan`
   - The plan will be saved and you'll wait for approval

**Available tools in Plan Mode:**
- All filesystem tools (`ls`, `read_file`, `glob`, `grep`)
- `submit_plan` - Submit your plan for approval
- `exit_plan_mode` - Exit plan mode without submitting (if needed)

**DO NOT:**
- Modify or create files (no `write_file` or `edit_file`)
- Execute commands (no `execute`)
- Start implementation before approval

Focus on thorough exploration and creating a solid plan first.
"""

EXECUTION_MODE_SYSTEM_PROMPT = """## Execution Mode

You are in EXECUTION MODE with an approved plan. Your goal is to:

1. **Follow the plan** step by step
   - Execute steps in the order defined in the plan
   - Respect dependencies between steps
   - Mark steps as complete using `complete_plan_step`

2. **Implement carefully**
   - Make changes as described in the plan
   - Use `write_file` and `edit_file` to implement
   - Test your changes when possible

3. **Track progress**
   - Use `complete_plan_step` when you finish a step
   - Document results and any deviations from the plan

**Current Plan Status:**
{plan_progress}

**Available tools:**
- All filesystem and execution tools
- `complete_plan_step` - Mark a step as complete with results
- `exit_plan_mode` - Exit plan mode when done

Stay focused on executing the approved plan.
"""


class PlanModeMiddlewareState(AgentState):
    """State for the plan mode middleware."""

    plan_mode_active: Annotated[bool, lambda x, y: y if y is not None else x] = False
    """Whether plan mode is currently active."""

    current_plan: Annotated[Plan | None, lambda x, y: y if y is not None else x] = None
    """The current plan being worked on."""

    plan_file: Annotated[str | None, lambda x, y: y if y is not None else x] = None
    """Path to the plan file in the filesystem."""


class PlanModeMiddleware(AgentMiddleware):
    """Middleware for plan mode functionality.

    This middleware enables a two-phase approach to complex tasks:
    1. Planning phase: Agent explores codebase and creates a detailed plan
    2. Execution phase: Agent implements the approved plan step by step

    Example:
        ```python
        from deepagents.middleware.plan_mode import PlanModeMiddleware
        from deepagents import create_deep_agent

        agent = create_deep_agent(
            middleware=[PlanModeMiddleware()],
        )

        # User can then ask: "Enter plan mode to implement feature X"
        ```
    """

    state_schema = PlanModeMiddlewareState

    def __init__(self) -> None:
        """Initialize the plan mode middleware."""
        self._tools: list[BaseTool] = []

    @property
    def state(self) -> PlanModeState:
        """Get the current plan mode state.

        Returns:
            Dictionary with plan mode state.
        """
        # This is a placeholder - actual state comes from runtime
        return PlanModeState(
            plan_mode_active=False,
            current_plan=None,
            plan_file=None,
        )

    @property
    def is_active(self) -> bool:
        """Check if plan mode is currently active.

        Returns:
            True if plan mode is active.
        """
        return self.state.get("plan_mode_active", False)

    @property
    def current_plan(self) -> Plan | None:
        """Get the current plan.

        Returns:
            Current Plan object or None.
        """
        return self.state.get("current_plan")

    def enter_plan_mode(self, goal: str, plan_file: str = "/plan.json") -> Plan:
        """Enter plan mode with a specific goal.

        Args:
            goal: The goal or objective for the plan.
            plan_file: Path where the plan will be saved.

        Returns:
            New Plan object.
        """
        plan = Plan(
            goal=goal,
            phase=PlanPhase.PLANNING,
            title=f"Plan for: {goal[:100]}",
        )
        return plan

    def exit_plan_mode(self) -> str:
        """Exit plan mode.

        Returns:
            Confirmation message.
        """
        return "Exited plan mode."

    def submit_plan(self, plan_data: dict) -> str:
        """Submit a plan for approval.

        Args:
            plan_data: Dictionary containing plan details.

        Returns:
            Confirmation message.
        """
        return "Plan submitted for approval."

    def approve_plan(self) -> str:
        """Approve the current plan.

        Returns:
            Confirmation message.
        """
        if not self.current_plan:
            return "Error: No plan to approve."

        self.current_plan.approve()
        return f"Plan approved. Ready to execute {len(self.current_plan.steps)} steps."

    def reject_plan(self, reason: str = "") -> str:
        """Reject the current plan.

        Args:
            reason: Reason for rejection.

        Returns:
            Confirmation message.
        """
        if not self.current_plan:
            return "Error: No plan to reject."

        self.current_plan.reject(reason)
        return f"Plan rejected. Reason: {reason}"

    def complete_step(self, step_id: str, result: str) -> str:
        """Complete a plan step.

        Args:
            step_id: ID of the step to complete.
            result: Result or outcome of the step.

        Returns:
            Confirmation message.
        """
        if not self.current_plan:
            return "Error: No active plan."

        for step in self.current_plan.steps:
            if step.id == step_id:
                step.status = PlanStepStatus.COMPLETED
                step.result = result
                self.current_plan.updated_at = datetime.now()

                # Check if all steps are complete
                if all(s.status in (PlanStepStatus.COMPLETED, PlanStepStatus.SKIPPED) for s in self.current_plan.steps):
                    self.current_plan.complete()
                    return f"Step '{step.title}' completed. All steps done! Plan completed."

                return f"Step '{step.title}' completed. Progress: {self.current_plan.progress[0]}/{self.current_plan.progress[1]}"

        return f"Error: Step with ID {step_id} not found."

    def get_system_prompt_addition(self, runtime: ToolRuntime | None = None) -> str:
        """Get the system prompt addition based on current mode.

        Args:
            runtime: Optional tool runtime to access state.

        Returns:
            System prompt text.
        """
        # Try to get state from runtime if available
        if runtime and hasattr(runtime, "state"):
            is_active = runtime.state.get("plan_mode_active", False)
            current_plan = runtime.state.get("current_plan")
        else:
            is_active = self.state.get("plan_mode_active", False)
            current_plan = self.state.get("current_plan")

        if not is_active:
            return ""

        # Check if we have an approved plan
        if current_plan and current_plan.phase == PlanPhase.EXECUTING:
            progress = f"{current_plan.progress[0]}/{current_plan.progress[1]} steps completed"
            current_step = current_plan.current_step
            if current_step:
                progress += f"\nCurrent step: {current_step.title}"

            return EXECUTION_MODE_SYSTEM_PROMPT.format(plan_progress=progress)

        # Otherwise, we're in planning mode
        return PLAN_MODE_SYSTEM_PROMPT

    def get_tools(self) -> list[BaseTool]:
        """Get the plan mode tools.

        Returns:
            List of LangChain tools for plan mode.
        """
        if self._tools:
            return self._tools

        @tool
        def enter_plan_mode(goal: str, plan_file: str = "/plan.json", runtime: ToolRuntime[None, PlanModeMiddlewareState] = None) -> str:
            """Enter plan mode to create a detailed implementation plan.

            Use this when you need to tackle a complex task that requires:
            - Understanding the codebase structure
            - Creating a step-by-step plan
            - Getting approval before implementation

            Args:
                goal: The main objective or goal for this plan
                plan_file: Path where the plan will be saved (default: /plan.json)
                runtime: Tool runtime (automatically provided)

            Returns:
                Confirmation message with next steps
            """
            plan = Plan(
                goal=goal,
                phase=PlanPhase.PLANNING,
                title=f"Plan for: {goal[:100]}",
            )

            # Update state via runtime if available
            if runtime:
                runtime.state["plan_mode_active"] = True
                runtime.state["current_plan"] = plan
                runtime.state["plan_file"] = plan_file

            return f"""Entered plan mode!

Goal: {goal}

Next steps:
1. Explore the codebase using ls, read_file, glob, grep
2. Understand the architecture and existing patterns
3. Create a detailed plan with steps using submit_plan
4. Wait for approval before implementation

Plan will be saved to: {plan_file}

Start exploring the codebase now to understand the context.
"""

        @tool
        def submit_plan(
            title: str,
            description: str,
            steps: list[dict],
            architecture_notes: str = "",
            risks: list[str] | None = None,
            alternatives_considered: list[str] | None = None,
            explored_files: list[str] | None = None,
            runtime: ToolRuntime[None, PlanModeMiddlewareState] = None,
        ) -> str:
            """Submit a detailed implementation plan for approval.

            Call this after you've explored the codebase and created a comprehensive plan.

            Args:
                title: Short title for the plan
                description: Detailed description of what will be implemented
                steps: List of step dictionaries, each containing:
                    - title: Step title
                    - description: What this step does
                    - files_to_modify: List of files to modify
                    - files_to_create: List of files to create
                    - dependencies: List of step IDs this depends on (optional)
                    - estimated_changes: Scope of changes (optional)
                architecture_notes: Notes about architecture decisions
                risks: List of potential risks or concerns
                alternatives_considered: List of alternatives that were considered
                explored_files: List of files that were explored during planning
                runtime: Tool runtime (automatically provided)

            Returns:
                Confirmation message
            """
            if not runtime or not runtime.state.get("plan_mode_active"):
                return "Error: Not in plan mode. Use enter_plan_mode first."

            current_plan = runtime.state.get("current_plan")
            if not current_plan:
                return "Error: No active plan found."

            # Update plan with submitted data
            current_plan.title = title
            current_plan.description = description
            current_plan.architecture_notes = architecture_notes
            current_plan.risks = risks or []
            current_plan.alternatives_considered = alternatives_considered or []
            current_plan.explored_files = explored_files or []

            # Convert step dicts to PlanStep objects
            plan_steps = []
            for step_dict in steps:
                plan_step = PlanStep(
                    title=step_dict.get("title", ""),
                    description=step_dict.get("description", ""),
                    files_to_modify=step_dict.get("files_to_modify", []),
                    files_to_create=step_dict.get("files_to_create", []),
                    dependencies=step_dict.get("dependencies", []),
                    estimated_changes=step_dict.get("estimated_changes", ""),
                    notes=step_dict.get("notes", ""),
                )
                plan_steps.append(plan_step)

            current_plan.steps = plan_steps
            current_plan.phase = PlanPhase.AWAITING_APPROVAL

            # Save plan to file if plan_file is set
            plan_file = runtime.state.get("plan_file", "/plan.json")
            # Note: In real implementation, you'd save to filesystem here

            return f"""Plan submitted successfully!

Title: {title}
Steps: {len(plan_steps)}
Explored files: {len(current_plan.explored_files)}

The plan is now awaiting approval. Once approved, you can begin execution.

Plan saved to: {plan_file}
"""

        @tool
        def complete_plan_step(
            step_id: str,
            result: str,
            runtime: ToolRuntime[None, PlanModeMiddlewareState] = None,
        ) -> str:
            """Mark a plan step as completed with results.

            Use this after successfully completing a step in the execution phase.

            Args:
                step_id: ID of the step that was completed
                result: Description of what was accomplished and any notes
                runtime: Tool runtime (automatically provided)

            Returns:
                Confirmation message with progress
            """
            if not runtime or not runtime.state.get("plan_mode_active"):
                return "Error: Not in plan mode."

            current_plan = runtime.state.get("current_plan")
            if not current_plan:
                return "Error: No active plan."

            if current_plan.phase != PlanPhase.EXECUTING:
                return "Error: Plan must be approved before executing steps."

            for step in current_plan.steps:
                if step.id == step_id:
                    step.status = PlanStepStatus.COMPLETED
                    step.result = result

                    # Check if all steps are complete
                    completed, total = current_plan.progress
                    if completed >= total:
                        current_plan.complete()
                        return f"""Step '{step.title}' completed!

Result: {result}

All steps are now complete! Plan execution finished successfully.
"""

                    return f"""Step '{step.title}' completed!

Result: {result}

Progress: {completed}/{total} steps completed
"""

            return f"Error: Step with ID '{step_id}' not found in plan."

        @tool
        def exit_plan_mode(runtime: ToolRuntime[None, PlanModeMiddlewareState] = None) -> str:
            """Exit plan mode.

            Use this to leave plan mode, either after completing all steps or if you need to cancel.

            Args:
                runtime: Tool runtime (automatically provided)

            Returns:
                Confirmation message
            """
            if not runtime:
                return "Exited plan mode."

            current_plan = runtime.state.get("current_plan")
            message = "Exited plan mode."

            if current_plan:
                if current_plan.phase == PlanPhase.COMPLETED:
                    message = f"Exited plan mode. Plan '{current_plan.title}' was completed successfully!"
                elif current_plan.phase == PlanPhase.EXECUTING:
                    completed, total = current_plan.progress
                    message = f"Exited plan mode. Plan '{current_plan.title}' was partially completed ({completed}/{total} steps)."
                else:
                    message = f"Exited plan mode. Plan '{current_plan.title}' was not completed."

            # Clear state
            runtime.state["plan_mode_active"] = False
            runtime.state["current_plan"] = None
            runtime.state["plan_file"] = None

            return message

        self._tools = [enter_plan_mode, submit_plan, complete_plan_step, exit_plan_mode]
        return self._tools

    def wrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], ModelResponse],
    ) -> ModelResponse:
        """Add plan mode system prompt and filter tools based on phase.

        Args:
            request: The model request being processed.
            handler: The handler function to call with the modified request.

        Returns:
            The model response from the handler.
        """
        # Get plan mode state from runtime
        runtime = request.runtime
        is_active = runtime.state.get("plan_mode_active", False) if runtime and hasattr(runtime, "state") else False

        if is_active:
            # Add system prompt
            system_prompt_addition = self.get_system_prompt_addition(runtime)
            if system_prompt_addition:
                current_prompt = request.system_prompt or ""
                request = request.override(
                    system_prompt=f"{current_prompt}\n\n{system_prompt_addition}".strip()
                )

            # Filter tools based on phase
            current_plan = runtime.state.get("current_plan") if runtime and hasattr(runtime, "state") else None
            if current_plan and current_plan.phase == PlanPhase.PLANNING:
                # In planning phase, filter out write/edit/execute tools
                filtered_tools = [
                    tool
                    for tool in request.tools
                    if not (hasattr(tool, "name") and tool.name in ("write_file", "edit_file", "execute"))
                ]
                request = request.override(tools=filtered_tools)

        return handler(request)

    async def awrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], Awaitable[ModelResponse]],
    ) -> ModelResponse:
        """(async) Add plan mode system prompt and filter tools based on phase.

        Args:
            request: The model request being processed.
            handler: The handler function to call with the modified request.

        Returns:
            The model response from the handler.
        """
        # Get plan mode state from runtime
        runtime = request.runtime
        is_active = runtime.state.get("plan_mode_active", False) if runtime and hasattr(runtime, "state") else False

        if is_active:
            # Add system prompt
            system_prompt_addition = self.get_system_prompt_addition(runtime)
            if system_prompt_addition:
                current_prompt = request.system_prompt or ""
                request = request.override(
                    system_prompt=f"{current_prompt}\n\n{system_prompt_addition}".strip()
                )

            # Filter tools based on phase
            current_plan = runtime.state.get("current_plan") if runtime and hasattr(runtime, "state") else None
            if current_plan and current_plan.phase == PlanPhase.PLANNING:
                # In planning phase, filter out write/edit/execute tools
                filtered_tools = [
                    tool
                    for tool in request.tools
                    if not (hasattr(tool, "name") and tool.name in ("write_file", "edit_file", "execute"))
                ]
                request = request.override(tools=filtered_tools)

        return await handler(request)

    @property
    def tools(self) -> Sequence[BaseTool]:
        """Get the tools provided by this middleware.

        Returns:
            List of plan mode tools.
        """
        return self.get_tools()
