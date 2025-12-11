"""Custom slash commands module for DeepAgents CLI.

This module provides support for user-defined slash commands similar to
Claude Code's .claude/commands/ feature. Commands are loaded from markdown
files with YAML frontmatter and can be invoked via /command-name in the CLI.

Directory hierarchy (precedence: project > agent > global):
- Global: ~/.deepagents/commands/{index_name}/{command_name}.md
- Agent: ~/.deepagents/{agent}/commands/{index_name}/{command_name}.md
- Project: {project}/.deepagents/commands/{index_name}/{command_name}.md

Example command file structure:
```markdown
---
name: review-code
description: Review code for quality and best practices
aliases: [review, cr]
---

Review the code for:
1. Quality and best practices
2. Potential bugs
3. Performance concerns
```
"""

from deepagents_cli.custom_commands.handler import (
    get_command_help,
    handle_custom_command,
    parse_command_line,
)
from deepagents_cli.custom_commands.load import (
    CommandMetadata,
    expand_command_template,
    get_command_content,
    list_commands,
)
from deepagents_cli.custom_commands.registry import (
    CommandRegistry,
    create_command_registry,
)
from deepagents_cli.custom_commands.tool import (
    SlashCommandInput,
    SlashCommandTool,
    create_slash_command_tool,
)

__all__ = [
    # Load
    "CommandMetadata",
    "list_commands",
    "get_command_content",
    "expand_command_template",
    # Registry
    "CommandRegistry",
    "create_command_registry",
    # Handler
    "handle_custom_command",
    "parse_command_line",
    "get_command_help",
    # Tool
    "SlashCommandTool",
    "SlashCommandInput",
    "create_slash_command_tool",
]
