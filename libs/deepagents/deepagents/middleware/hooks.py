"""Middleware for integrating hooks into the agent execution flow.

This module provides the HooksMiddleware class that integrates the hooks system
with the agent's middleware pipeline, allowing hooks to intercept and modify
tool calls and other agent operations.
"""

from collections.abc import Awaitable, Callable
from typing import Any, NotRequired

from langchain.agents.middleware.types import AgentMiddleware, AgentState
from langchain.tools.tool_node import ToolCallRequest
from langchain_core.messages import ToolMessage
from langgraph.types import Command
from typing_extensions import TypedDict

from deepagents.hooks.executor import HookExecutor
from deepagents.hooks.registry import HookRegistry
from deepagents.hooks.types import HookContext, HookEvent


class HooksState(AgentState):
    """State for the hooks middleware.

    Attributes:
        hooks_data: Optional dictionary for storing hook-specific data.
    """

    hooks_data: NotRequired[dict[str, Any]]
    """Optional dictionary for storing hook-specific data."""


class HooksMiddleware(AgentMiddleware):
    """Middleware for executing hooks at various points in the agent lifecycle.

    This middleware integrates the hooks system into the agent's execution flow,
    allowing hooks to intercept and modify behavior at key points such as before
    and after tool calls.

    Args:
        registry: Optional HookRegistry instance. If not provided, a new empty
            registry is created.
        assistant_id: Optional identifier for the assistant.

    Example:
        ```python
        from deepagents.hooks import HookRegistry, HookEvent
        from deepagents.middleware.hooks import HooksMiddleware

        # Create a registry and register hooks
        registry = HookRegistry()
        registry.register(my_validation_hook)

        # Create middleware
        middleware = HooksMiddleware(registry=registry, assistant_id="my-assistant")

        # Use with agent
        agent = create_agent(middleware=[middleware])
        ```
    """

    state_schema = HooksState

    def __init__(
        self,
        *,
        registry: HookRegistry | None = None,
        assistant_id: str | None = None,
    ) -> None:
        """Initialize the hooks middleware.

        Args:
            registry: Optional HookRegistry instance. If not provided, creates empty registry.
            assistant_id: Optional identifier for the assistant.
        """
        self.registry = registry if registry is not None else HookRegistry()
        self.executor = HookExecutor(self.registry)
        self.assistant_id = assistant_id

    @property
    def state(self) -> type[HooksState]:
        """Get the state schema for this middleware.

        Returns:
            The HooksState class.
        """
        return HooksState

    async def pre_tool_call(self, request: ToolCallRequest) -> ToolMessage | Command | None:
        """Execute hooks before a tool is called.

        Args:
            request: The tool call request being processed.

        Returns:
            None to continue execution, or a ToolMessage/Command to short-circuit.
        """
        # Get session state from runtime
        session_state = dict(request.runtime.state)

        # Create hook context
        context = HookContext(
            event=HookEvent.PRE_TOOL_CALL,
            data={
                "tool_call": request.tool_call,
                "tool": request.tool,
            },
            session_state=session_state,
            assistant_id=self.assistant_id,
        )

        # Execute hooks
        result = await self.executor.execute(context)

        # Check if execution should continue
        if not result.get("continue_execution", True):
            # Return error message if hook stopped execution
            error_msg = result.get("error", "Tool call blocked by hook")
            if result.get("message"):
                error_msg = f"{error_msg}: {result['message']}"

            return ToolMessage(
                content=error_msg,
                tool_call_id=request.tool_call["id"],
            )

        # Apply modified data if provided
        if "modified_data" in result and result["modified_data"] is not None:
            modified = result["modified_data"]
            # Update tool call with modified data if present
            if "tool_call" in modified:
                request.tool_call.update(modified["tool_call"])

        return None

    async def post_tool_call(
        self,
        request: ToolCallRequest,
        result: ToolMessage | Command,
    ) -> ToolMessage | Command:
        """Execute hooks after a tool has been called.

        Args:
            request: The tool call request that was processed.
            result: The result from the tool execution.

        Returns:
            The original or modified result.
        """
        # Get session state from runtime
        session_state = dict(request.runtime.state)

        # Extract content from result
        if isinstance(result, ToolMessage):
            result_content = result.content
        elif isinstance(result, Command):
            # For Command, extract from update messages if available
            messages = result.update.get("messages", []) if result.update else []
            result_content = messages[0].content if messages else ""
        else:
            result_content = str(result)

        # Create hook context
        context = HookContext(
            event=HookEvent.POST_TOOL_CALL,
            data={
                "tool_call": request.tool_call,
                "tool": request.tool,
                "result": result_content,
            },
            session_state=session_state,
            assistant_id=self.assistant_id,
        )

        # Execute hooks
        hook_result = await self.executor.execute(context)

        # Check if execution should continue
        if not hook_result.get("continue_execution", True):
            # Return error message if hook stopped execution
            error_msg = hook_result.get("error", "Tool result blocked by hook")
            if hook_result.get("message"):
                error_msg = f"{error_msg}: {hook_result['message']}"

            return ToolMessage(
                content=error_msg,
                tool_call_id=request.tool_call["id"],
            )

        # Apply modified result if provided
        if "modified_data" in hook_result and hook_result["modified_data"] is not None:
            modified = hook_result["modified_data"]
            if "result" in modified:
                # Update the result with modified data
                if isinstance(result, ToolMessage):
                    result = ToolMessage(
                        content=modified["result"],
                        tool_call_id=result.tool_call_id,
                    )
                elif isinstance(result, Command):
                    # Update Command messages if present
                    if result.update and "messages" in result.update:
                        messages = result.update["messages"]
                        if messages:
                            messages[0] = ToolMessage(
                                content=modified["result"],
                                tool_call_id=request.tool_call["id"],
                            )

        return result

    def wrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], ToolMessage | Command],
    ) -> ToolMessage | Command:
        """Wrap tool calls with pre and post hooks (sync version).

        This method is not implemented for the synchronous version.
        Use the async version instead.

        Args:
            request: The tool call request being processed.
            handler: The handler function to call.

        Returns:
            The result from the handler.

        Raises:
            NotImplementedError: This middleware requires async execution.
        """
        msg = "HooksMiddleware requires async execution. Use awrap_tool_call instead."
        raise NotImplementedError(msg)

    async def awrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], Awaitable[ToolMessage | Command]],
    ) -> ToolMessage | Command:
        """Wrap tool calls with pre and post hooks (async version).

        Args:
            request: The tool call request being processed.
            handler: The async handler function to call.

        Returns:
            The result from the handler or modified result from hooks.
        """
        # Execute pre-tool-call hooks
        pre_result = await self.pre_tool_call(request)
        if pre_result is not None:
            # Hook stopped execution, return early
            return pre_result

        # Execute the actual tool call
        result = await handler(request)

        # Execute post-tool-call hooks
        result = await self.post_tool_call(request, result)

        return result
