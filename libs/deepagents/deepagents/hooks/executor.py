"""Hook executor for running Python and shell hooks.

This module provides the HookExecutor class that executes hooks registered
in a HookRegistry, with support for both Python hooks and external shell scripts.
"""

import asyncio
import json
import logging
import subprocess
from typing import Any

from deepagents.hooks.registry import HookRegistry
from deepagents.hooks.types import HookContext, HookEvent, HookResult

logger = logging.getLogger(__name__)


class HookExecutor:
    """Executor for running hooks with async support.

    This class executes hooks registered in a HookRegistry for specific events.
    It runs Python hooks first, then shell hooks, both sorted by priority.

    Example:
        ```python
        from deepagents.hooks import HookRegistry, HookExecutor, HookContext, HookEvent

        registry = HookRegistry()
        registry.register(my_hook)

        executor = HookExecutor(registry)

        context = HookContext(
            event=HookEvent.PRE_TOOL_CALL,
            data={"tool": "read_file", "args": {"path": "/test.txt"}},
            session_state={"user_id": "123"},
        )

        result = await executor.execute(context)
        if not result["continue_execution"]:
            print("Hook stopped execution")
        ```
    """

    def __init__(self, registry: HookRegistry) -> None:
        """Initialize the hook executor.

        Args:
            registry: The HookRegistry containing registered hooks.
        """
        self.registry = registry

    async def execute(self, context: HookContext) -> HookResult:
        """Execute all hooks for the given context.

        Runs Python hooks first, then shell hooks, all sorted by priority.
        If any hook returns continue_execution=False, execution stops immediately.

        Args:
            context: The HookContext containing event and state information.

        Returns:
            Aggregated HookResult from all executed hooks. If any hook stops
            execution, that result is returned immediately.
        """
        # Start with default result
        aggregated_result: HookResult = {
            "continue_execution": True,
        }

        # Execute Python hooks first
        python_hooks = self.registry.get_hooks(context.event)
        for hook in python_hooks:
            try:
                result = await hook.execute(context)

                # Update aggregated result
                if not result.get("continue_execution", True):
                    # Stop execution immediately if a hook says so
                    return result

                # Merge modified data if provided
                if "modified_data" in result and result["modified_data"] is not None:
                    context.data = result["modified_data"]
                    aggregated_result["modified_data"] = result["modified_data"]

                # Log messages
                if "message" in result and result["message"]:
                    logger.info("Hook '%s': %s", hook.name, result["message"])

            except Exception as e:
                logger.exception("Error executing Python hook '%s'", hook.name)
                return {
                    "continue_execution": False,
                    "error": f"Hook '{hook.name}' failed: {e}",
                }

        # Execute shell hooks
        shell_hooks = self.registry.get_shell_hooks(context.event)
        for shell_hook in shell_hooks:
            try:
                result = await self._execute_shell_hook(shell_hook.script_path, context)

                # Update aggregated result
                if not result.get("continue_execution", True):
                    # Stop execution immediately if a hook says so
                    return result

                # Merge modified data if provided
                if "modified_data" in result and result["modified_data"] is not None:
                    context.data = result["modified_data"]
                    aggregated_result["modified_data"] = result["modified_data"]

                # Log messages
                if "message" in result and result["message"]:
                    logger.info("Shell hook '%s': %s", shell_hook.name, result["message"])

            except Exception as e:
                logger.exception("Error executing shell hook '%s'", shell_hook.name)
                return {
                    "continue_execution": False,
                    "error": f"Shell hook '{shell_hook.name}' failed: {e}",
                }

        return aggregated_result

    async def _execute_shell_hook(self, script_path: str, context: HookContext) -> HookResult:
        """Execute a shell hook script.

        The hook context is passed as JSON via stdin. The script is expected to
        output a JSON object matching the HookResult structure to stdout.

        Args:
            script_path: Path to the shell script to execute.
            context: The HookContext to pass to the script.

        Returns:
            HookResult from the shell script's JSON output.

        Raises:
            subprocess.CalledProcessError: If the script exits with non-zero status.
            json.JSONDecodeError: If the script's output is not valid JSON.
            ValueError: If the script's output doesn't match HookResult structure.
        """
        # Convert context to JSON
        context_dict: dict[str, Any] = {
            "event": context.event.value,
            "data": context.data,
            "session_state": context.session_state,
            "assistant_id": context.assistant_id,
        }
        context_json = json.dumps(context_dict)

        # Execute the shell script
        process = await asyncio.create_subprocess_exec(
            script_path,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout, stderr = await process.communicate(input=context_json.encode())

        if process.returncode != 0:
            error_msg = stderr.decode().strip() if stderr else "Unknown error"
            logger.error("Shell hook at '%s' failed with code %d: %s", script_path, process.returncode, error_msg)
            return {
                "continue_execution": False,
                "error": f"Shell hook exited with code {process.returncode}: {error_msg}",
            }

        # Parse the output as JSON
        try:
            result = json.loads(stdout.decode())
        except json.JSONDecodeError as e:
            logger.error("Shell hook at '%s' returned invalid JSON: %s", script_path, e)
            return {
                "continue_execution": False,
                "error": f"Shell hook returned invalid JSON: {e}",
            }

        # Validate the result structure
        if not isinstance(result, dict) or "continue_execution" not in result:
            logger.error("Shell hook at '%s' returned invalid result structure", script_path)
            return {
                "continue_execution": False,
                "error": "Shell hook returned invalid result structure (must include 'continue_execution')",
            }

        return result  # type: ignore[return-value]
