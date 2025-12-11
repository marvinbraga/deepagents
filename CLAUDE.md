# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Deep Agents is a LangGraph-based agent framework implementing planning, computer access, and sub-agent delegation patterns. The repository is a monorepo containing three packages under `libs/`:

- **deepagents** - Core agent library with `create_deep_agent()` factory
- **deepagents-cli** - Interactive terminal interface (similar to Claude Code)
- **deepagents-harbor** - Harbor integration for benchmarking

## Development Commands

All packages use `uv` for dependency management. Run commands from within each package directory.

### deepagents (libs/deepagents)
```bash
uv sync --all-groups          # Install dependencies
make test                      # Unit tests with coverage
make integration_test          # Integration tests
make lint                      # Ruff format check, ruff check, mypy
make format                    # Auto-format code
```

### deepagents-cli (libs/deepagents-cli)
```bash
uv sync --all-groups          # Install dependencies
make test                      # Unit tests (socket-disabled)
make test_integration          # Integration tests
make lint                      # Lint check
make format                    # Auto-format code
uv run deepagents              # Run CLI during development
```

### deepagents-harbor (libs/harbor)
```bash
uv sync                       # Install dependencies
make test                      # Unit tests
make run-terminal-bench-modal  # Run benchmarks on Modal
make run-terminal-bench-docker # Run benchmarks locally
```

### Running a Single Test
```bash
# From package directory
uv run pytest tests/unit_tests/test_file.py::test_function_name
# Or using make with TEST_FILE variable
make test TEST_FILE=tests/unit_tests/test_specific.py
```

## Architecture

### Core Library (deepagents)

Entry point: `deepagents.create_deep_agent()` - creates a compiled LangGraph StateGraph.

**Middleware System** - Tools and behaviors are provided via middleware pattern:
- `FilesystemMiddleware` - File operations (ls, read_file, write_file, edit_file, glob, grep, execute)
- `SubAgentMiddleware` - Task delegation to isolated sub-agents
- `UserInteractionMiddleware` - ask_user_question, confirm_action tools
- TodoListMiddleware (from langchain) - Task tracking (write_todos, read_todos)

**Backends** - Pluggable storage for file operations:
- `StateBackend` (default) - Ephemeral in agent state
- `FilesystemBackend` - Real disk operations
- `StoreBackend` - LangGraph Store persistence
- `CompositeBackend` - Route different paths to different backends

**Subagents** - Can be defined as dicts or `CompiledSubAgent` for custom graphs.

### CLI (deepagents-cli)

Main modules:
- `cli.py` / `main.py` - Entry point and CLI loop
- `agent.py` - Agent configuration
- `execution.py` - Execution flow
- `tools.py` - Tool definitions
- `skills/` - Progressive disclosure skill system
- `sessions/` - Session management
- `user_interaction.py` - HITL prompts

**Configuration hierarchy:**
- Global: `~/.deepagents/<agent_name>/agent.md` + skills/
- Project: `.deepagents/agent.md` + skills/
- Project root detection via `.git`

## Code Style

- Uses `ruff` for linting and formatting (line-length: 150 for deepagents, 100 for CLI)
- Google-style docstrings (`convention = "google"`)
- Type hints required (`mypy strict = true`)
- Tests use `pytest` with `pytest-asyncio` for async tests

## Key Concepts

**Middleware adds tools and prompt modifications** - Don't duplicate tool descriptions already covered by middleware defaults.

**Subagent delegation** - Use `task` tool to spawn isolated agents for parallel/complex work.

**Progressive disclosure for skills** - Skills show only name+description until activated, then full instructions loaded.

**HITL (Human-in-the-Loop)** - Configure `interrupt_on` parameter for tool approval workflows.
