"""Plan mode types and data structures."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import NotRequired
from uuid import UUID, uuid4

from typing_extensions import TypedDict


class PlanPhase(str, Enum):
    """Current phase of the plan lifecycle."""

    IDLE = "idle"
    PLANNING = "planning"
    AWAITING_APPROVAL = "awaiting_approval"
    EXECUTING = "executing"
    COMPLETED = "completed"
    REJECTED = "rejected"


class PlanStepStatus(str, Enum):
    """Status of a single plan step."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    SKIPPED = "skipped"
    FAILED = "failed"


@dataclass
class PlanStep:
    """A single step in a plan."""

    id: str = field(default_factory=lambda: str(uuid4()))
    """Unique identifier for the step."""

    title: str = ""
    """Short title describing the step."""

    description: str = ""
    """Detailed description of what this step involves."""

    status: PlanStepStatus = PlanStepStatus.PENDING
    """Current status of the step."""

    files_to_modify: list[str] = field(default_factory=list)
    """List of files that will be modified in this step."""

    files_to_create: list[str] = field(default_factory=list)
    """List of files that will be created in this step."""

    dependencies: list[str] = field(default_factory=list)
    """List of step IDs that must be completed before this step."""

    estimated_changes: str = ""
    """Estimated scope of changes for this step."""

    notes: str = ""
    """Additional notes or context for the step."""

    result: str | None = None
    """Result or outcome after step completion."""


@dataclass
class Plan:
    """A complete implementation plan."""

    id: UUID = field(default_factory=uuid4)
    """Unique identifier for the plan."""

    title: str = ""
    """Short title of the plan."""

    description: str = ""
    """Detailed description of what the plan aims to achieve."""

    goal: str = ""
    """The main goal or objective of the plan."""

    phase: PlanPhase = PlanPhase.IDLE
    """Current phase of the plan."""

    steps: list[PlanStep] = field(default_factory=list)
    """List of steps to execute."""

    created_at: datetime = field(default_factory=datetime.now)
    """Timestamp when the plan was created."""

    updated_at: datetime = field(default_factory=datetime.now)
    """Timestamp when the plan was last updated."""

    approved_at: datetime | None = None
    """Timestamp when the plan was approved."""

    completed_at: datetime | None = None
    """Timestamp when the plan was completed."""

    explored_files: list[str] = field(default_factory=list)
    """List of files that were explored during planning."""

    architecture_notes: str = ""
    """Notes about the architecture and design decisions."""

    risks: list[str] = field(default_factory=list)
    """List of potential risks or concerns."""

    alternatives_considered: list[str] = field(default_factory=list)
    """Alternative approaches that were considered."""

    def approve(self) -> None:
        """Approve the plan and move to executing phase."""
        self.phase = PlanPhase.EXECUTING
        self.approved_at = datetime.now()
        self.updated_at = datetime.now()

    def reject(self, reason: str = "") -> None:
        """Reject the plan.

        Args:
            reason: Optional reason for rejection.
        """
        self.phase = PlanPhase.REJECTED
        self.updated_at = datetime.now()
        if reason:
            self.architecture_notes += f"\n\nRejection reason: {reason}"

    def complete(self) -> None:
        """Mark the plan as completed."""
        self.phase = PlanPhase.COMPLETED
        self.completed_at = datetime.now()
        self.updated_at = datetime.now()

    @property
    def current_step(self) -> PlanStep | None:
        """Get the current step being executed.

        Returns:
            The first step with status IN_PROGRESS, or None if no step is in progress.
        """
        for step in self.steps:
            if step.status == PlanStepStatus.IN_PROGRESS:
                return step
        return None

    @property
    def progress(self) -> tuple[int, int]:
        """Get the progress of the plan.

        Returns:
            Tuple of (completed_steps, total_steps).
        """
        completed = sum(1 for step in self.steps if step.status in (PlanStepStatus.COMPLETED, PlanStepStatus.SKIPPED))
        return (completed, len(self.steps))


class PlanModeState(TypedDict):
    """State dictionary for plan mode middleware."""

    plan_mode_active: NotRequired[bool]
    """Whether plan mode is currently active."""

    current_plan: NotRequired[Plan | None]
    """The current plan being worked on."""

    plan_file: NotRequired[str | None]
    """Path to the plan file in the filesystem."""
