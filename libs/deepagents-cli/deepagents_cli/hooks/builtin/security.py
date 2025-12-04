"""Security hooks for validating tool calls."""

import logging
import os
import re
from pathlib import Path

from deepagents.hooks.types import HookContext, HookEvent, HookProtocol, HookResult

logger = logging.getLogger(__name__)


class PathTraversalHook(HookProtocol):
    """Hook that prevents path traversal attacks in file operations.

    This hook validates file paths in tool calls to ensure they don't
    attempt to access files outside the working directory using path
    traversal techniques (e.g., ../../../etc/passwd).

    Priority: 10 (runs early for security)
    Events: PRE_TOOL_CALL
    """

    @property
    def name(self) -> str:
        """Get the hook name.

        Returns:
            The hook's unique identifier.
        """
        return "path_traversal_prevention"

    @property
    def events(self) -> list[HookEvent]:
        """Get the list of events this hook responds to.

        Returns:
            List containing PRE_TOOL_CALL event.
        """
        return [HookEvent.PRE_TOOL_CALL]

    @property
    def priority(self) -> int:
        """Get the hook priority.

        Returns:
            Priority value (10 - runs early for security).
        """
        return 10

    async def execute(self, context: HookContext) -> HookResult:
        """Execute the path traversal prevention hook.

        Args:
            context: The hook context containing tool call information.

        Returns:
            HookResult blocking execution if path traversal detected.
        """
        tool_call = context.data.get("tool_call", {})
        tool_name = tool_call.get("name", "")
        tool_args = tool_call.get("args", {})

        # Check file operation tools
        file_tools = {"read_file", "write_file", "edit_file", "ls", "glob", "grep"}
        if tool_name not in file_tools:
            return HookResult(continue_execution=True)

        # Get the file path argument
        file_path_arg = tool_args.get("file_path") or tool_args.get("path") or tool_args.get("directory")

        if not file_path_arg:
            return HookResult(continue_execution=True)

        # Validate the path
        try:
            # Resolve the path to its absolute form
            resolved_path = Path(file_path_arg).resolve()
            working_dir = Path.cwd().resolve()

            # Check if the resolved path is within the working directory
            # This prevents ../../../etc/passwd style attacks
            if not str(resolved_path).startswith(str(working_dir)):
                logger.warning(
                    "Blocked path traversal attempt in %s: %s (resolved to %s, outside %s)",
                    tool_name,
                    file_path_arg,
                    resolved_path,
                    working_dir,
                )
                return HookResult(
                    continue_execution=False,
                    error="Path traversal blocked",
                    message=f"Access denied: Path {file_path_arg} is outside the working directory",
                )

        except Exception as e:
            logger.warning("Error validating path %s: %s", file_path_arg, e)
            # Allow execution if we can't validate (to avoid false positives)
            return HookResult(continue_execution=True)

        return HookResult(continue_execution=True)


class DangerousCommandHook(HookProtocol):
    """Hook that blocks potentially dangerous shell commands.

    This hook inspects shell commands for dangerous patterns like:
    - rm -rf / (recursive deletion)
    - dd commands (disk operations)
    - mkfs (filesystem formatting)
    - chmod 777 (overly permissive permissions)
    - curl/wget piped to bash

    Priority: 10 (runs early for security)
    Events: PRE_TOOL_CALL
    """

    # Dangerous command patterns
    DANGEROUS_PATTERNS = [
        r"rm\s+(-[rf]+\s+)?/\s*$",  # rm -rf /
        r"rm\s+-rf\s+/",  # rm -rf / anywhere
        r":\(\)\s*\{.*\}\s*;",  # Fork bomb
        r"dd\s+if=/dev/(zero|random)",  # Disk fill
        r"mkfs\.",  # Format filesystem
        r">\s*/dev/sd[a-z]",  # Write directly to disk
        r"chmod\s+(-R\s+)?777",  # Overly permissive
        r"curl.*\|\s*(ba)?sh",  # Pipe to shell
        r"wget.*\|\s*(ba)?sh",  # Pipe to shell
    ]

    @property
    def name(self) -> str:
        """Get the hook name.

        Returns:
            The hook's unique identifier.
        """
        return "dangerous_command_prevention"

    @property
    def events(self) -> list[HookEvent]:
        """Get the list of events this hook responds to.

        Returns:
            List containing PRE_TOOL_CALL event.
        """
        return [HookEvent.PRE_TOOL_CALL]

    @property
    def priority(self) -> int:
        """Get the hook priority.

        Returns:
            Priority value (10 - runs early for security).
        """
        return 10

    async def execute(self, context: HookContext) -> HookResult:
        """Execute the dangerous command prevention hook.

        Args:
            context: The hook context containing tool call information.

        Returns:
            HookResult blocking execution if dangerous command detected.
        """
        tool_call = context.data.get("tool_call", {})
        tool_name = tool_call.get("name", "")
        tool_args = tool_call.get("args", {})

        # Check shell/execute tools
        shell_tools = {"shell", "execute"}
        if tool_name not in shell_tools:
            return HookResult(continue_execution=True)

        # Get the command
        command = tool_args.get("command", "")
        if not command:
            return HookResult(continue_execution=True)

        # Check against dangerous patterns
        for pattern in self.DANGEROUS_PATTERNS:
            if re.search(pattern, command, re.IGNORECASE):
                logger.warning(
                    "Blocked dangerous command in %s: %s (matched pattern: %s)",
                    tool_name,
                    command,
                    pattern,
                )
                return HookResult(
                    continue_execution=False,
                    error="Dangerous command blocked",
                    message=f"Potentially dangerous command blocked: {command[:100]}",
                )

        return HookResult(continue_execution=True)
