"""Type definitions for the hooks system.

This module defines the core types and protocols used by the hooks system,
including event types, context data, result structures, and hook protocols.
"""

import abc
from dataclasses import dataclass
from enum import Enum
from typing import Any, NotRequired

from typing_extensions import TypedDict


class HookEvent(str, Enum):
    """Events that can trigger hooks in the agent lifecycle."""

    PRE_TOOL_CALL = "pre_tool_call"
    """Triggered before a tool is called."""

    POST_TOOL_CALL = "post_tool_call"
    """Triggered after a tool has been called."""

    USER_PROMPT_SUBMIT = "user_prompt_submit"
    """Triggered when a user submits a prompt."""

    AGENT_RESPONSE = "agent_response"
    """Triggered when the agent generates a response."""

    SESSION_START = "session_start"
    """Triggered when a session starts."""

    SESSION_END = "session_end"
    """Triggered when a session ends."""

    TOOL_APPROVAL = "tool_approval"
    """Triggered when a tool requires approval."""

    ERROR = "error"
    """Triggered when an error occurs."""


@dataclass
class HookContext:
    """Context information passed to hooks.

    This dataclass contains all the information available to a hook when it's executed,
    including the event type, event-specific data, session state, and assistant ID.

    Attributes:
        event: The event that triggered this hook.
        data: Event-specific data (e.g., tool call info, error details).
        session_state: Current session state dictionary.
        assistant_id: Optional identifier for the assistant.
    """

    event: HookEvent
    """The event that triggered this hook."""

    data: dict[str, Any]
    """Event-specific data (e.g., tool call info, error details)."""

    session_state: dict[str, Any]
    """Current session state dictionary."""

    assistant_id: str | None = None
    """Optional identifier for the assistant."""


class HookResult(TypedDict):
    """Result returned by a hook execution.

    This TypedDict defines the structure of results returned by hooks,
    allowing hooks to control execution flow and modify data.

    Attributes:
        continue_execution: Whether to continue with the normal execution flow.
        modified_data: Optional modified data to use instead of original data.
        message: Optional message to log or display.
        error: Optional error message if the hook failed.
    """

    continue_execution: bool
    """Whether to continue with the normal execution flow."""

    modified_data: NotRequired[dict[str, Any] | None]
    """Optional modified data to use instead of original data."""

    message: NotRequired[str | None]
    """Optional message to log or display."""

    error: NotRequired[str | None]
    """Optional error message if the hook failed."""


class HookProtocol(abc.ABC):
    """Protocol that all hooks must implement.

    This abstract base class defines the interface that all hooks must follow.
    Hooks are executed at specific points in the agent lifecycle and can inspect
    or modify the execution flow.
    """

    @property
    @abc.abstractmethod
    def name(self) -> str:
        """Unique name for this hook.

        Returns:
            The hook's unique identifier.
        """

    @property
    @abc.abstractmethod
    def events(self) -> list[HookEvent]:
        """List of events this hook should respond to.

        Returns:
            List of HookEvent values this hook handles.
        """

    @property
    @abc.abstractmethod
    def priority(self) -> int:
        """Priority for hook execution (lower numbers run first).

        Returns:
            Integer priority value (0-100 recommended, default 50).
        """

    @abc.abstractmethod
    async def execute(self, context: HookContext) -> HookResult:
        """Execute the hook with the given context.

        Args:
            context: The HookContext containing event and state information.

        Returns:
            HookResult indicating success, failure, and any modifications.
        """
