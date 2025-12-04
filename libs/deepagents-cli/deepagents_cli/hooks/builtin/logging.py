"""Logging hook for tool calls."""

import logging

from deepagents.hooks.types import HookContext, HookEvent, HookProtocol, HookResult

logger = logging.getLogger(__name__)


class ToolLoggingHook(HookProtocol):
    """Hook that logs all tool calls for debugging and auditing.

    This hook logs information about tool calls before and after execution,
    including tool name, arguments, and results.

    Priority: 90 (runs after most other hooks)
    Events: PRE_TOOL_CALL, POST_TOOL_CALL
    """

    @property
    def name(self) -> str:
        """Get the hook name.

        Returns:
            The hook's unique identifier.
        """
        return "tool_logging"

    @property
    def events(self) -> list[HookEvent]:
        """Get the list of events this hook responds to.

        Returns:
            List containing PRE_TOOL_CALL and POST_TOOL_CALL events.
        """
        return [HookEvent.PRE_TOOL_CALL, HookEvent.POST_TOOL_CALL]

    @property
    def priority(self) -> int:
        """Get the hook priority.

        Returns:
            Priority value (90 - runs after most other hooks).
        """
        return 90

    async def execute(self, context: HookContext) -> HookResult:
        """Execute the logging hook.

        Args:
            context: The hook context containing event and tool information.

        Returns:
            HookResult allowing execution to continue.
        """
        if context.event == HookEvent.PRE_TOOL_CALL:
            tool_call = context.data.get("tool_call", {})
            tool_name = tool_call.get("name", "unknown")
            tool_args = tool_call.get("args", {})

            logger.info("Tool call: %s", tool_name)
            logger.debug("Tool arguments: %s", tool_args)

        elif context.event == HookEvent.POST_TOOL_CALL:
            tool_call = context.data.get("tool_call", {})
            tool_name = tool_call.get("name", "unknown")
            result = context.data.get("result", "")

            # Truncate result for logging if too long
            result_preview = str(result)[:200]
            if len(str(result)) > 200:
                result_preview += "..."

            logger.info("Tool call completed: %s", tool_name)
            logger.debug("Tool result: %s", result_preview)

        return HookResult(continue_execution=True)
