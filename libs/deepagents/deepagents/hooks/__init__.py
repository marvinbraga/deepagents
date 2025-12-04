"""Hooks system for DeepAgents.

This module provides a flexible hooks system that allows intercepting and
modifying agent behavior at various lifecycle points.
"""

from deepagents.hooks.executor import HookExecutor
from deepagents.hooks.registry import HookRegistry, ShellHook
from deepagents.hooks.types import HookContext, HookEvent, HookProtocol, HookResult

__all__ = [
    "HookContext",
    "HookEvent",
    "HookExecutor",
    "HookProtocol",
    "HookRegistry",
    "HookResult",
    "ShellHook",
]
