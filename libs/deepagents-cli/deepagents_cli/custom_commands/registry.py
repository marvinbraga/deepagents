"""Command registry for managing and routing slash commands.

This module provides a centralized registry for both built-in and custom
slash commands. It handles command discovery, alias resolution, and
provides the interface for command completion.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Callable

from deepagents_cli.custom_commands.load import CommandMetadata, list_commands

if TYPE_CHECKING:
    from deepagents_cli.config import Settings


class CommandRegistry:
    """Central registry for all slash commands.

    Manages both built-in commands (hardcoded handlers) and custom commands
    (loaded from markdown files). Provides lookup by name or alias.

    Attributes:
        settings: Settings instance for path resolution.
        agent_name: Current agent identifier.
    """

    def __init__(self, settings: "Settings", agent_name: str) -> None:
        """Initialize the command registry.

        Args:
            settings: Settings instance for path resolution.
            agent_name: Current agent identifier.
        """
        self.settings = settings
        self.agent_name = agent_name
        self._builtin_commands: dict[str, tuple[Callable[..., bool], str]] = {}
        self._custom_commands: dict[str, CommandMetadata] = {}
        self._alias_map: dict[str, str] = {}

    def register_builtin(
        self,
        name: str,
        handler: Callable[..., bool],
        description: str,
    ) -> None:
        """Register a built-in command.

        Args:
            name: Command name (without leading slash).
            handler: Function to handle the command.
            description: Human-readable description for help/completion.
        """
        self._builtin_commands[name] = (handler, description)

    def load_custom_commands(self) -> None:
        """Load custom commands from all configured directories.

        Loads commands from three levels with precedence:
        1. Project commands (highest)
        2. Agent commands
        3. Global commands (lowest)
        """
        # Clear existing custom commands
        self._custom_commands.clear()
        self._alias_map.clear()

        # Get directory paths
        global_dir = self.settings.get_global_commands_dir()
        agent_dir = self.settings.get_user_commands_dir(self.agent_name)
        project_dir = self.settings.get_project_commands_dir()

        # Load commands with proper precedence
        commands = list_commands(
            global_commands_dir=global_dir,
            agent_commands_dir=agent_dir,
            project_commands_dir=project_dir,
        )

        # Index by name and aliases
        # Use format {index}:{name} when index is present (like Claude Code)
        for cmd in commands:
            index = cmd.get("index", "")
            cmd_name = cmd["name"]

            # Full name with index prefix (e.g., "review:code-review")
            if index:
                full_name = f"{index}:{cmd_name}"
            else:
                full_name = cmd_name

            self._custom_commands[full_name] = cmd

            # Also register aliases with index prefix
            for alias in cmd.get("aliases", []):
                if index:
                    alias_full = f"{index}:{alias}"
                else:
                    alias_full = alias
                self._alias_map[alias_full] = full_name

            # Also register without prefix for backwards compatibility
            # (only if there's no conflict)
            if index and cmd_name not in self._custom_commands:
                self._alias_map[cmd_name] = full_name

    def get_command(self, name: str) -> tuple[str, CommandMetadata | None]:
        """Look up a command by name or alias.

        Args:
            name: Command name or alias to look up.

        Returns:
            Tuple of (resolved_name, metadata).
            - If found as custom command: (name, CommandMetadata)
            - If not found: (name, None)
        """
        # Resolve alias to command name
        resolved_name = self._alias_map.get(name, name)

        # Check custom commands
        if resolved_name in self._custom_commands:
            return resolved_name, self._custom_commands[resolved_name]

        return name, None

    def is_builtin_command(self, name: str) -> bool:
        """Check if a command is a built-in command.

        Args:
            name: Command name to check.

        Returns:
            True if it's a built-in command.
        """
        return name in self._builtin_commands

    def is_custom_command(self, name: str) -> bool:
        """Check if a command is a custom command.

        Args:
            name: Command name or alias to check.

        Returns:
            True if it's a custom command.
        """
        resolved_name = self._alias_map.get(name, name)
        return resolved_name in self._custom_commands

    def get_custom_command(self, name: str) -> CommandMetadata | None:
        """Get custom command metadata by name or alias.

        Args:
            name: Command name or alias.

        Returns:
            CommandMetadata if found, None otherwise.
        """
        _, metadata = self.get_command(name)
        return metadata

    def get_all_commands(self) -> dict[str, str]:
        """Get all commands with descriptions for completion.

        Returns:
            Dictionary mapping command names to descriptions.
            Includes both built-in and custom commands.
            Custom commands use format {index}:{name} when index is present.
        """
        commands: dict[str, str] = {}

        # Add built-in commands
        for name, (_, description) in self._builtin_commands.items():
            commands[name] = description

        # Add custom commands with their full names (index:name format)
        for full_name, metadata in self._custom_commands.items():
            source_label = f"({metadata['source']})"
            commands[full_name] = f"{metadata['description']} {source_label}"

            # Also add aliases with index prefix
            index = metadata.get("index", "")
            for alias in metadata.get("aliases", []):
                if index:
                    alias_full = f"{index}:{alias}"
                else:
                    alias_full = alias
                if alias_full not in commands:
                    commands[alias_full] = f"Alias for /{full_name}"

        return commands

    def get_custom_commands_list(self) -> list[CommandMetadata]:
        """Get list of all custom commands.

        Returns:
            List of CommandMetadata for all loaded custom commands.
        """
        return list(self._custom_commands.values())

    def reload(self) -> None:
        """Reload custom commands from disk.

        Useful when commands may have been added/modified during a session.
        """
        self.load_custom_commands()


def create_command_registry(settings: "Settings", agent_name: str) -> CommandRegistry:
    """Create and initialize a command registry.

    Args:
        settings: Settings instance for path resolution.
        agent_name: Current agent identifier.

    Returns:
        Initialized CommandRegistry with custom commands loaded.
    """
    registry = CommandRegistry(settings, agent_name)
    registry.load_custom_commands()
    return registry
