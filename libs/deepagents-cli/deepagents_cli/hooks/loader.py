"""Loader for hooks configuration."""

import logging
from typing import TYPE_CHECKING

from deepagents.hooks.registry import HookRegistry

if TYPE_CHECKING:
    from deepagents_cli.config import Settings

logger = logging.getLogger(__name__)


def load_hooks_config(settings: "Settings") -> HookRegistry:
    """Load hooks configuration from settings.

    This function creates a HookRegistry and registers built-in hooks
    based on the current settings and configuration.

    Args:
        settings: The Settings instance containing configuration

    Returns:
        HookRegistry with registered hooks

    Example:
        ```python
        from deepagents_cli.config import settings
        from deepagents_cli.hooks import load_hooks_config

        registry = load_hooks_config(settings)
        ```
    """
    registry = HookRegistry()

    # Register built-in hooks
    _register_builtin_hooks(registry, settings)

    # TODO: Load user-defined hooks from config file
    # project_hooks = Path(".deepagents/hooks.json")
    # user_hooks = Path.home() / ".deepagents" / "hooks.json"

    logger.info("Loaded hooks registry with %d hooks", len(registry._python_hooks) + len(registry._shell_hooks))
    return registry


def _register_builtin_hooks(registry: HookRegistry, settings: "Settings") -> None:
    """Register built-in hooks.

    Args:
        registry: The HookRegistry to register hooks into
        settings: The Settings instance
    """
    # Import built-in hooks
    from deepagents_cli.hooks.builtin.logging import ToolLoggingHook
    from deepagents_cli.hooks.builtin.security import DangerousCommandHook, PathTraversalHook

    # Register logging hook (lower priority to run last)
    logging_hook = ToolLoggingHook()
    registry.register(logging_hook)
    logger.debug("Registered ToolLoggingHook")

    # Register security hooks (higher priority to run first)
    path_traversal_hook = PathTraversalHook()
    registry.register(path_traversal_hook)
    logger.debug("Registered PathTraversalHook")

    dangerous_command_hook = DangerousCommandHook()
    registry.register(dangerous_command_hook)
    logger.debug("Registered DangerousCommandHook")
