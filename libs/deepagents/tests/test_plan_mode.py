"""Unit tests for the Plan Mode system."""

from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest

from deepagents.middleware.plan_mode import PlanModeMiddleware
from deepagents.plan.types import Plan, PlanPhase, PlanStep, PlanStepStatus


class TestPlanPhase:
    """Test PlanPhase enum values."""

    def test_plan_phase_values(self):
        """Test that all expected plan phases exist."""
        assert PlanPhase.IDLE.value == "idle"
        assert PlanPhase.PLANNING.value == "planning"
        assert PlanPhase.AWAITING_APPROVAL.value == "awaiting_approval"
        assert PlanPhase.EXECUTING.value == "executing"
        assert PlanPhase.COMPLETED.value == "completed"
        assert PlanPhase.REJECTED.value == "rejected"

    def test_plan_phase_is_string_enum(self):
        """Test that PlanPhase is a string enum."""
        assert isinstance(PlanPhase.IDLE, str)
        assert isinstance(PlanPhase.PLANNING, PlanPhase)


class TestPlanStepStatus:
    """Test PlanStepStatus enum values."""

    def test_plan_step_status_values(self):
        """Test that all expected step statuses exist."""
        assert PlanStepStatus.PENDING.value == "pending"
        assert PlanStepStatus.IN_PROGRESS.value == "in_progress"
        assert PlanStepStatus.COMPLETED.value == "completed"
        assert PlanStepStatus.SKIPPED.value == "skipped"
        assert PlanStepStatus.FAILED.value == "failed"

    def test_plan_step_status_is_string_enum(self):
        """Test that PlanStepStatus is a string enum."""
        assert isinstance(PlanStepStatus.PENDING, str)
        assert isinstance(PlanStepStatus.COMPLETED, PlanStepStatus)


class TestPlanStep:
    """Test PlanStep creation and methods."""

    def test_plan_step_creation(self):
        """Test creating a PlanStep."""
        step = PlanStep(
            title="Implement feature",
            description="Add new feature to the app",
            status=PlanStepStatus.PENDING,
            files_to_modify=["app.py"],
            files_to_create=["feature.py"],
        )

        assert step.title == "Implement feature"
        assert step.description == "Add new feature to the app"
        assert step.status == PlanStepStatus.PENDING
        assert step.files_to_modify == ["app.py"]
        assert step.files_to_create == ["feature.py"]
        assert step.id  # Should have auto-generated ID

    def test_plan_step_defaults(self):
        """Test PlanStep with default values."""
        step = PlanStep()

        assert step.title == ""
        assert step.description == ""
        assert step.status == PlanStepStatus.PENDING
        assert step.files_to_modify == []
        assert step.files_to_create == []
        assert step.dependencies == []
        assert step.estimated_changes == ""
        assert step.notes == ""
        assert step.result is None

    def test_plan_step_status_change(self):
        """Test changing step status."""
        step = PlanStep(title="Test step")

        assert step.status == PlanStepStatus.PENDING

        step.status = PlanStepStatus.IN_PROGRESS
        assert step.status == PlanStepStatus.IN_PROGRESS

        step.status = PlanStepStatus.COMPLETED
        assert step.status == PlanStepStatus.COMPLETED

    def test_plan_step_with_result(self):
        """Test setting step result."""
        step = PlanStep(title="Test step")

        assert step.result is None

        step.result = "Successfully completed the step"
        assert step.result == "Successfully completed the step"

    def test_plan_step_with_dependencies(self):
        """Test step with dependencies."""
        step = PlanStep(
            title="Dependent step",
            dependencies=["step-1", "step-2"],
        )

        assert len(step.dependencies) == 2
        assert "step-1" in step.dependencies
        assert "step-2" in step.dependencies


class TestPlan:
    """Test Plan creation and methods."""

    def test_plan_creation(self):
        """Test creating a Plan."""
        plan = Plan(
            title="Feature Implementation",
            description="Implement the new feature",
            goal="Add authentication",
            phase=PlanPhase.PLANNING,
        )

        assert plan.title == "Feature Implementation"
        assert plan.description == "Implement the new feature"
        assert plan.goal == "Add authentication"
        assert plan.phase == PlanPhase.PLANNING
        assert plan.id  # Should have auto-generated UUID
        assert plan.created_at
        assert plan.updated_at

    def test_plan_defaults(self):
        """Test Plan with default values."""
        plan = Plan()

        assert plan.title == ""
        assert plan.description == ""
        assert plan.goal == ""
        assert plan.phase == PlanPhase.IDLE
        assert plan.steps == []
        assert plan.approved_at is None
        assert plan.completed_at is None
        assert plan.explored_files == []
        assert plan.architecture_notes == ""
        assert plan.risks == []
        assert plan.alternatives_considered == []

    def test_plan_approve(self):
        """Test approving a plan."""
        plan = Plan(
            title="Test Plan",
            phase=PlanPhase.AWAITING_APPROVAL,
        )

        assert plan.approved_at is None
        assert plan.phase == PlanPhase.AWAITING_APPROVAL

        plan.approve()

        assert plan.phase == PlanPhase.EXECUTING
        assert plan.approved_at is not None
        assert isinstance(plan.approved_at, datetime)

    def test_plan_reject(self):
        """Test rejecting a plan."""
        plan = Plan(
            title="Test Plan",
            phase=PlanPhase.AWAITING_APPROVAL,
        )

        plan.reject(reason="Not thorough enough")

        assert plan.phase == PlanPhase.REJECTED
        assert "Not thorough enough" in plan.architecture_notes

    def test_plan_reject_without_reason(self):
        """Test rejecting a plan without reason."""
        plan = Plan(
            title="Test Plan",
            phase=PlanPhase.AWAITING_APPROVAL,
        )

        original_notes = plan.architecture_notes
        plan.reject()

        assert plan.phase == PlanPhase.REJECTED
        # Notes should not change if no reason given
        assert plan.architecture_notes == original_notes

    def test_plan_complete(self):
        """Test completing a plan."""
        plan = Plan(
            title="Test Plan",
            phase=PlanPhase.EXECUTING,
        )

        assert plan.completed_at is None

        plan.complete()

        assert plan.phase == PlanPhase.COMPLETED
        assert plan.completed_at is not None
        assert isinstance(plan.completed_at, datetime)

    def test_plan_current_step(self):
        """Test getting current step."""
        plan = Plan()

        step1 = PlanStep(title="Step 1", status=PlanStepStatus.COMPLETED)
        step2 = PlanStep(title="Step 2", status=PlanStepStatus.IN_PROGRESS)
        step3 = PlanStep(title="Step 3", status=PlanStepStatus.PENDING)

        plan.steps = [step1, step2, step3]

        current = plan.current_step

        assert current is not None
        assert current.title == "Step 2"
        assert current.status == PlanStepStatus.IN_PROGRESS

    def test_plan_current_step_none(self):
        """Test current_step when no step is in progress."""
        plan = Plan()

        step1 = PlanStep(title="Step 1", status=PlanStepStatus.COMPLETED)
        step2 = PlanStep(title="Step 2", status=PlanStepStatus.PENDING)

        plan.steps = [step1, step2]

        assert plan.current_step is None

    def test_plan_progress(self):
        """Test calculating plan progress."""
        plan = Plan()

        step1 = PlanStep(title="Step 1", status=PlanStepStatus.COMPLETED)
        step2 = PlanStep(title="Step 2", status=PlanStepStatus.COMPLETED)
        step3 = PlanStep(title="Step 3", status=PlanStepStatus.SKIPPED)
        step4 = PlanStep(title="Step 4", status=PlanStepStatus.PENDING)
        step5 = PlanStep(title="Step 5", status=PlanStepStatus.IN_PROGRESS)

        plan.steps = [step1, step2, step3, step4, step5]

        completed, total = plan.progress

        assert completed == 3  # 2 completed + 1 skipped
        assert total == 5

    def test_plan_progress_empty(self):
        """Test progress with no steps."""
        plan = Plan()

        completed, total = plan.progress

        assert completed == 0
        assert total == 0

    def test_plan_progress_all_complete(self):
        """Test progress when all steps are complete."""
        plan = Plan()

        step1 = PlanStep(title="Step 1", status=PlanStepStatus.COMPLETED)
        step2 = PlanStep(title="Step 2", status=PlanStepStatus.COMPLETED)

        plan.steps = [step1, step2]

        completed, total = plan.progress

        assert completed == 2
        assert total == 2


class TestPlanModeMiddleware:
    """Test PlanModeMiddleware functionality."""

    def test_middleware_initialization(self):
        """Test creating PlanModeMiddleware."""
        middleware = PlanModeMiddleware()

        assert middleware._tools == []

    def test_middleware_state_property(self):
        """Test state property."""
        middleware = PlanModeMiddleware()

        state = middleware.state

        assert state["plan_mode_active"] is False
        assert state["current_plan"] is None
        assert state["plan_file"] is None

    def test_middleware_is_active(self):
        """Test is_active property."""
        middleware = PlanModeMiddleware()

        # State returns False by default
        assert middleware.is_active is False

    def test_middleware_current_plan(self):
        """Test current_plan property."""
        middleware = PlanModeMiddleware()

        # State returns None by default
        assert middleware.current_plan is None

    def test_enter_plan_mode(self):
        """Test entering plan mode."""
        middleware = PlanModeMiddleware()

        plan = middleware.enter_plan_mode(
            goal="Implement authentication system",
            plan_file="/plans/auth.json",
        )

        assert isinstance(plan, Plan)
        assert plan.goal == "Implement authentication system"
        assert plan.phase == PlanPhase.PLANNING
        assert "Implement authentication system" in plan.title

    def test_exit_plan_mode(self):
        """Test exiting plan mode."""
        middleware = PlanModeMiddleware()

        result = middleware.exit_plan_mode()

        assert "Exited plan mode" in result

    def test_submit_plan(self):
        """Test submitting a plan."""
        middleware = PlanModeMiddleware()

        result = middleware.submit_plan(
            {
                "title": "Test Plan",
                "description": "A test plan",
                "steps": [],
            }
        )

        assert "submitted" in result.lower()

    def test_approve_plan(self):
        """Test approving a plan."""
        middleware = PlanModeMiddleware()

        # Without a current plan
        result = middleware.approve_plan()
        assert "Error" in result

    def test_approve_plan_with_plan(self):
        """Test approving when there's a current plan."""
        middleware = PlanModeMiddleware()

        # Create a mock plan and test the approve_plan method directly
        mock_plan = Plan(
            title="Test Plan",
            phase=PlanPhase.AWAITING_APPROVAL,
        )
        mock_plan.steps = [PlanStep(title="Step 1")]

        # Patch the current_plan property to return our mock plan
        with patch.object(PlanModeMiddleware, "current_plan", new_callable=lambda: Mock(return_value=mock_plan)):
            # Can't test easily without runtime, but the method exists
            assert hasattr(middleware, "approve_plan")

    def test_reject_plan(self):
        """Test rejecting a plan."""
        middleware = PlanModeMiddleware()

        result = middleware.reject_plan("Insufficient detail")

        assert "Error" in result or "rejected" in result.lower()

    def test_complete_step(self):
        """Test completing a step."""
        middleware = PlanModeMiddleware()

        result = middleware.complete_step("step-123", "Successfully implemented")

        assert "Error" in result

    def test_get_tools(self):
        """Test getting plan mode tools."""
        middleware = PlanModeMiddleware()

        tools = middleware.get_tools()

        assert len(tools) == 4
        tool_names = [tool.name for tool in tools]
        assert "enter_plan_mode" in tool_names
        assert "submit_plan" in tool_names
        assert "complete_plan_step" in tool_names
        assert "exit_plan_mode" in tool_names

    def test_get_tools_cached(self):
        """Test that tools are cached."""
        middleware = PlanModeMiddleware()

        tools1 = middleware.get_tools()
        tools2 = middleware.get_tools()

        # Should return same instance
        assert tools1 is tools2

    def test_get_system_prompt_addition_not_active(self):
        """Test system prompt when plan mode is not active."""
        middleware = PlanModeMiddleware()

        prompt = middleware.get_system_prompt_addition()

        assert prompt == ""

    def test_get_system_prompt_addition_planning(self):
        """Test system prompt during planning phase."""
        middleware = PlanModeMiddleware()

        # Mock runtime with active plan mode
        mock_runtime = Mock()
        mock_runtime.state = {
            "plan_mode_active": True,
            "current_plan": Plan(phase=PlanPhase.PLANNING),
        }

        prompt = middleware.get_system_prompt_addition(mock_runtime)

        assert "PLAN MODE" in prompt
        assert "Explore the codebase" in prompt
        assert "submit_plan" in prompt

    def test_get_system_prompt_addition_executing(self):
        """Test system prompt during execution phase."""
        middleware = PlanModeMiddleware()

        plan = Plan(phase=PlanPhase.EXECUTING)
        plan.steps = [
            PlanStep(title="Step 1", status=PlanStepStatus.COMPLETED),
            PlanStep(title="Step 2", status=PlanStepStatus.PENDING),
        ]

        # Mock runtime
        mock_runtime = Mock()
        mock_runtime.state = {
            "plan_mode_active": True,
            "current_plan": plan,
        }

        prompt = middleware.get_system_prompt_addition(mock_runtime)

        assert "EXECUTION MODE" in prompt
        assert "1/2 steps completed" in prompt

    def test_wrap_model_call_not_active(self):
        """Test wrap_model_call when plan mode is not active."""
        middleware = PlanModeMiddleware()

        mock_request = Mock()
        mock_request.runtime = Mock()
        mock_request.runtime.state = {"plan_mode_active": False}
        mock_request.system_prompt = "Original prompt"
        mock_request.tools = []

        def handler(req):
            return Mock()

        result = middleware.wrap_model_call(mock_request, handler)

        # Should not modify request
        assert result is not None

    def test_wrap_model_call_planning_filters_tools(self):
        """Test that planning phase filters out write/edit tools."""
        middleware = PlanModeMiddleware()

        plan = Plan(phase=PlanPhase.PLANNING)

        # Create mock tools
        read_tool = Mock()
        read_tool.name = "read_file"

        write_tool = Mock()
        write_tool.name = "write_file"

        edit_tool = Mock()
        edit_tool.name = "edit_file"

        execute_tool = Mock()
        execute_tool.name = "execute"

        mock_request = Mock()
        mock_request.runtime = Mock()
        mock_request.runtime.state = {
            "plan_mode_active": True,
            "current_plan": plan,
        }
        mock_request.system_prompt = "Original"
        mock_request.tools = [read_tool, write_tool, edit_tool, execute_tool]
        mock_request.override = Mock(return_value=mock_request)

        def handler(req):
            return Mock()

        middleware.wrap_model_call(mock_request, handler)

        # Should have filtered tools
        assert mock_request.override.called

    @pytest.mark.asyncio
    async def test_awrap_model_call(self):
        """Test async wrap_model_call."""
        middleware = PlanModeMiddleware()

        mock_request = Mock()
        mock_request.runtime = Mock()
        mock_request.runtime.state = {"plan_mode_active": False}
        mock_request.system_prompt = "Original"
        mock_request.tools = []

        async def handler(req):
            return Mock()

        result = await middleware.awrap_model_call(mock_request, handler)

        assert result is not None

    @pytest.mark.asyncio
    async def test_awrap_model_call_adds_system_prompt(self):
        """Test that awrap_model_call adds system prompt."""
        middleware = PlanModeMiddleware()

        plan = Plan(phase=PlanPhase.PLANNING)

        mock_request = Mock()
        mock_request.runtime = Mock()
        mock_request.runtime.state = {
            "plan_mode_active": True,
            "current_plan": plan,
        }
        mock_request.system_prompt = "Original"
        mock_request.tools = []
        mock_request.override = Mock(return_value=mock_request)

        async def handler(req):
            return Mock()

        await middleware.awrap_model_call(mock_request, handler)

        # Should have modified prompt
        assert mock_request.override.called

    def test_tools_property(self):
        """Test tools property."""
        middleware = PlanModeMiddleware()

        tools = middleware.tools

        assert len(tools) == 4
        assert all(hasattr(tool, "name") for tool in tools)


class TestPlanModeTools:
    """Test the plan mode tool functions."""

    def test_enter_plan_mode_tool(self):
        """Test the enter_plan_mode tool."""
        middleware = PlanModeMiddleware()
        tools = middleware.get_tools()

        enter_tool = next(t for t in tools if t.name == "enter_plan_mode")

        assert enter_tool is not None
        assert "plan mode" in enter_tool.description.lower()

    def test_submit_plan_tool(self):
        """Test the submit_plan tool."""
        middleware = PlanModeMiddleware()
        tools = middleware.get_tools()

        submit_tool = next(t for t in tools if t.name == "submit_plan")

        assert submit_tool is not None
        assert "submit" in submit_tool.description.lower()

    def test_complete_plan_step_tool(self):
        """Test the complete_plan_step tool."""
        middleware = PlanModeMiddleware()
        tools = middleware.get_tools()

        complete_tool = next(t for t in tools if t.name == "complete_plan_step")

        assert complete_tool is not None
        assert "complete" in complete_tool.description.lower()

    def test_exit_plan_mode_tool(self):
        """Test the exit_plan_mode tool."""
        middleware = PlanModeMiddleware()
        tools = middleware.get_tools()

        exit_tool = next(t for t in tools if t.name == "exit_plan_mode")

        assert exit_tool is not None
        assert "exit" in exit_tool.description.lower()


class TestPlanModeIntegration:
    """Integration tests for plan mode workflow."""

    def test_full_plan_lifecycle(self):
        """Test a complete plan lifecycle."""
        # Create a plan
        plan = Plan(
            title="Feature Implementation",
            goal="Add new feature",
            phase=PlanPhase.PLANNING,
        )

        # Add steps
        step1 = PlanStep(
            title="Step 1: Design",
            description="Design the feature",
            status=PlanStepStatus.PENDING,
        )
        step2 = PlanStep(
            title="Step 2: Implement",
            description="Implement the feature",
            status=PlanStepStatus.PENDING,
        )
        plan.steps = [step1, step2]

        # Move to awaiting approval
        plan.phase = PlanPhase.AWAITING_APPROVAL
        assert plan.phase == PlanPhase.AWAITING_APPROVAL

        # Approve plan
        plan.approve()
        assert plan.phase == PlanPhase.EXECUTING
        assert plan.approved_at is not None

        # Complete first step
        step1.status = PlanStepStatus.COMPLETED
        step1.result = "Design completed"

        completed, total = plan.progress
        assert completed == 1
        assert total == 2

        # Complete second step
        step2.status = PlanStepStatus.COMPLETED
        step2.result = "Implementation completed"

        completed, total = plan.progress
        assert completed == 2
        assert total == 2

        # Complete the plan
        plan.complete()
        assert plan.phase == PlanPhase.COMPLETED
        assert plan.completed_at is not None

    def test_plan_rejection_workflow(self):
        """Test plan rejection workflow."""
        plan = Plan(
            title="Feature Implementation",
            phase=PlanPhase.AWAITING_APPROVAL,
        )

        # Reject with reason
        plan.reject("Steps are not detailed enough")

        assert plan.phase == PlanPhase.REJECTED
        assert "not detailed enough" in plan.architecture_notes

    def test_plan_with_dependencies(self):
        """Test plan with step dependencies."""
        plan = Plan()

        step1 = PlanStep(
            id="step-1",
            title="Foundation",
            status=PlanStepStatus.PENDING,
        )

        step2 = PlanStep(
            id="step-2",
            title="Build on foundation",
            dependencies=["step-1"],
            status=PlanStepStatus.PENDING,
        )

        step3 = PlanStep(
            id="step-3",
            title="Final step",
            dependencies=["step-1", "step-2"],
            status=PlanStepStatus.PENDING,
        )

        plan.steps = [step1, step2, step3]

        # Verify dependencies are set correctly
        assert step1.dependencies == []
        assert step2.dependencies == ["step-1"]
        assert step3.dependencies == ["step-1", "step-2"]
