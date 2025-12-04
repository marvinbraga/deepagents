"""Hook registry for managing Python and shell hooks.

This module provides the HookRegistry class that manages the registration
and retrieval of hooks, supporting both Python hooks (implementing HookProtocol)
and shell script hooks.
"""

from collections.abc import Sequence
from dataclasses import dataclass

from deepagents.hooks.types import HookEvent, HookProtocol


@dataclass
class ShellHook:
    """Configuration for a shell script hook.

    Attributes:
        name: Unique name for this shell hook.
        script_path: Path to the shell script to execute.
        events: List of events this hook should respond to.
        priority: Priority for hook execution (lower numbers run first).
    """

    name: str
    """Unique name for this shell hook."""

    script_path: str
    """Path to the shell script to execute."""

    events: list[HookEvent]
    """List of events this hook should respond to."""

    priority: int = 50
    """Priority for hook execution (lower numbers run first)."""


class HookRegistry:
    """Registry for managing Python and shell hooks.

    This class provides a centralized registry for managing hooks that can be
    executed at various points in the agent lifecycle. It supports both Python
    hooks (implementing HookProtocol) and shell script hooks.

    Example:
        ```python
        from deepagents.hooks import HookRegistry, HookEvent

        registry = HookRegistry()

        # Register a Python hook
        registry.register(my_hook_instance)

        # Register a shell hook
        registry.register_shell(
            name="validation_hook",
            script_path="/path/to/validate.sh",
            events=[HookEvent.PRE_TOOL_CALL],
            priority=10
        )

        # Get hooks for a specific event
        hooks = registry.get_hooks(HookEvent.PRE_TOOL_CALL)
        ```
    """

    def __init__(self) -> None:
        """Initialize an empty hook registry."""
        self._python_hooks: dict[str, HookProtocol] = {}
        self._shell_hooks: dict[str, ShellHook] = {}

    def register(self, hook: HookProtocol) -> None:
        """Register a Python hook.

        Args:
            hook: The hook instance to register (must implement HookProtocol).

        Raises:
            ValueError: If a hook with the same name is already registered.
        """
        if hook.name in self._python_hooks:
            msg = f"Hook with name '{hook.name}' is already registered"
            raise ValueError(msg)

        self._python_hooks[hook.name] = hook

    def register_shell(
        self,
        name: str,
        script_path: str,
        events: list[HookEvent] | Sequence[HookEvent],
        priority: int = 50,
    ) -> None:
        """Register a shell script hook.

        Shell hooks are executed as external processes and receive the hook
        context as JSON via stdin.

        Args:
            name: Unique name for this shell hook.
            script_path: Path to the shell script to execute.
            events: List of events this hook should respond to.
            priority: Priority for hook execution (lower numbers run first). Default: 50.

        Raises:
            ValueError: If a shell hook with the same name is already registered.
        """
        if name in self._shell_hooks:
            msg = f"Shell hook with name '{name}' is already registered"
            raise ValueError(msg)

        self._shell_hooks[name] = ShellHook(
            name=name,
            script_path=script_path,
            events=list(events),
            priority=priority,
        )

    def unregister(self, name: str) -> None:
        """Unregister a hook by name.

        Removes both Python and shell hooks with the given name.

        Args:
            name: Name of the hook to unregister.

        Raises:
            ValueError: If no hook with the given name is found.
        """
        if name in self._python_hooks:
            del self._python_hooks[name]
        elif name in self._shell_hooks:
            del self._shell_hooks[name]
        else:
            msg = f"No hook with name '{name}' found"
            raise ValueError(msg)

    def get_hooks(self, event: HookEvent) -> list[HookProtocol]:
        """Get all Python hooks registered for a specific event.

        Returns hooks sorted by priority (lower priority values first).

        Args:
            event: The event to get hooks for.

        Returns:
            List of HookProtocol instances sorted by priority.
        """
        hooks = [hook for hook in self._python_hooks.values() if event in hook.events]
        return sorted(hooks, key=lambda h: h.priority)

    def get_shell_hooks(self, event: HookEvent) -> list[ShellHook]:
        """Get all shell hooks registered for a specific event.

        Returns hooks sorted by priority (lower priority values first).

        Args:
            event: The event to get shell hooks for.

        Returns:
            List of ShellHook instances sorted by priority.
        """
        hooks = [hook for hook in self._shell_hooks.values() if event in hook.events]
        return sorted(hooks, key=lambda h: h.priority)
