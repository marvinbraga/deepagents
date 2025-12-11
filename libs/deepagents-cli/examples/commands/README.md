# Custom Commands Examples

This directory contains example custom slash commands that can be used with DeepAgents CLI.

## Installation

Copy these command files to one of the following locations:

### Global Commands (available to all agents)
```bash
cp -r review ~/.deepagents/commands/
cp -r docs ~/.deepagents/commands/
```

### Agent-Specific Commands
```bash
# Replace 'myagent' with your agent name
cp -r review ~/.deepagents/myagent/commands/
cp -r docs ~/.deepagents/myagent/commands/
```

### Project Commands
```bash
# From your project root
cp -r review .deepagents/commands/
cp -r docs .deepagents/commands/
```

## Available Commands

### Code Review (`/code-review` or `/review` or `/cr`)

Performs comprehensive code review with configurable focus areas.

**Usage:**
```
/review                     # Review current directory, all aspects
/review src/main.py         # Review specific file
/review src/ security       # Review directory with security focus
```

**Arguments:**
- `target` (optional): File or directory to review. Default: `.`
- `focus` (optional): Focus area - security, performance, style, or all. Default: `all`

### Documentation (`/document` or `/doc` or `/docs`)

Generates documentation for code in various formats.

**Usage:**
```
/doc src/utils.py                    # Generate docstrings
/doc MyClass markdown                 # Generate markdown docs
/doc api/handlers.js jsdoc           # Generate JSDoc
```

**Arguments:**
- `target` (required): File, class, or function to document
- `style` (optional): Documentation style - docstring, markdown, jsdoc. Default: `docstring`

### Test Generation (`/test-gen` or `/tests` or `/gentest`)

Generates unit tests for code using specified testing framework.

**Usage:**
```
/tests src/utils.py                  # Generate pytest tests
/tests MyClass unittest              # Generate unittest tests
/tests api/handlers.js jest          # Generate Jest tests
```

**Arguments:**
- `target` (required): File or function to generate tests for
- `framework` (optional): Test framework - pytest, unittest, jest. Default: `pytest`

## Creating Your Own Commands

1. Create a markdown file with YAML frontmatter:

```markdown
---
name: my-command
description: Brief description of what the command does
aliases: [mc, myc]
args:
  - name: arg1
    description: Description of first argument
    required: true
  - name: arg2
    description: Description of second argument
    required: false
    default: "default_value"
---

Your prompt template here. Use {arg1} and {arg2} to reference arguments.

You can also use:
- {project_root} - The project root directory
- {cwd} - The current working directory
```

2. Place it in an index directory (e.g., `custom/my-command.md`)

3. The command will be available as `/my-command` or any of its aliases

## Directory Structure

Commands are organized in index directories:

```
~/.deepagents/commands/
  review/
    code-review.md
    test-gen.md
  docs/
    document.md
  custom/
    my-command.md
```

## Precedence

When the same command name exists in multiple locations:
1. **Project commands** (highest priority)
2. **Agent commands**
3. **Global commands** (lowest priority)
