# Deep Agents - Project Index

> Auto-generated repository documentation for AI agents

## Overview

**Deep Agents** is a general-purpose agent harness built on LangGraph that implements common principles for long-horizon tasks including planning, computer access (shell and filesystem), and sub-agent delegation.

- **Repository**: `deepagents`
- **Python Version**: >= 3.11
- **Main Dependencies**: langchain, langchain-anthropic, langgraph

## Architecture

```
deepagents/
├── libs/
│   ├── deepagents/          # Core library (v0.3.0)
│   ├── deepagents-cli/      # CLI application (v0.0.10)
│   └── harbor/              # Harbor integration (v0.0.1)
├── docs/
│   ├── design/              # Design documents
│   └── plans/               # Implementation plans
├── CLAUDE.md                # Claude Code instructions
└── README.md                # Main readme
```

---

## Package: deepagents (Core Library)

**Version**: 0.3.0
**Path**: `libs/deepagents/deepagents/`
**Description**: General purpose 'deep agent' with sub-agent spawning, todo list capabilities, and mock file system.

### Entry Points

| File | Purpose |
|------|---------|
| `__init__.py` | Package exports: `create_deep_agent`, `MCPClient`, `MCPServerConfig`, middleware classes |
| `graph.py` | Main agent factory: `create_deep_agent()` with default model, tools, and middleware stack |

### Core Modules

#### `graph.py` - Agent Factory
- **`create_deep_agent()`**: Creates a configured deep agent with:
  - Default model: `claude-sonnet-4-5-20250929`
  - Built-in middleware: TodoList, Filesystem, SubAgent, Summarization, PromptCaching
  - Configurable: model, tools, system_prompt, middleware, subagents, backend, etc.
- **`get_default_model()`**: Returns default ChatAnthropic instance

### Middleware (`middleware/`)

| Module | Class | Purpose |
|--------|-------|---------|
| `__init__.py` | - | Exports all middleware classes |
| `filesystem.py` | `FilesystemMiddleware` | File operations: ls, read_file, write_file, edit_file, glob, grep, execute |
| `subagents.py` | `SubAgentMiddleware`, `SubAgent`, `CompiledSubAgent` | Task delegation to isolated sub-agents |
| `web.py` | `WebMiddleware` | Web search (DuckDuckGo), fetch URL, deep research with LLM |
| `plan_mode.py` | `PlanModeMiddleware` | Planning mode for complex tasks |
| `hooks.py` | `HooksMiddleware` | Hook execution middleware |
| `mcp.py` | `MCPMiddleware` | MCP server integration |
| `ultrathink.py` | `UltrathinkMiddleware`, `UltrathinkState` | Extended thinking (Claude 4+) |
| `user_interaction.py` | `UserInteractionMiddleware`, `UserQuestionRequest` | Interactive user dialogs |
| `patch_tool_calls.py` | `PatchToolCallsMiddleware` | Fixes dangling tool calls |

### Backends (`backends/`)

| Module | Class | Purpose |
|--------|-------|---------|
| `protocol.py` | `BackendProtocol`, `BackendFactory`, `SandboxBackendProtocol` | Backend interfaces |
| `state.py` | `StateBackend` | Ephemeral state storage (default) |
| `filesystem.py` | `FilesystemBackend` | Real disk operations |
| `store.py` | `StoreBackend` | Persistent storage (LangGraph Store) |
| `composite.py` | `CompositeBackend` | Route paths to different backends |
| `sandbox.py` | - | Sandbox execution support |
| `utils.py` | - | Utility functions |

### Hooks (`hooks/`)

| Module | Class/Function | Purpose |
|--------|----------------|---------|
| `types.py` | `Hook`, `HookType`, `HookResult` | Hook type definitions |
| `registry.py` | `HookRegistry` | Hook registration and management |
| `executor.py` | `HookExecutor` | Hook execution logic |

### MCP (`mcp/`)

| Module | Class | Purpose |
|--------|-------|---------|
| `client.py` | `MCPClient` | MCP client implementation |
| `protocol.py` | `MCPServerConfig` | MCP server configuration |
| `tool_adapter.py` | - | MCP tool adaptation for LangChain |
| `example.py` | - | Usage examples |

### Plan (`plan/`)

| Module | Purpose |
|--------|---------|
| `types.py` | Planning type definitions |

### Optional Dependencies

```bash
pip install deepagents[web]  # Web search (DuckDuckGo)
pip install deepagents[all]  # All optional features
```

---

## Package: deepagents-cli (CLI Application)

**Version**: 0.0.10
**Path**: `libs/deepagents-cli/deepagents_cli/`
**Description**: Interactive AI coding assistant with skills, memory, and HITL workflows.

### Entry Points

| File | Purpose |
|------|---------|
| `__init__.py` | Exports `cli_main` |
| `main.py` | CLI entry point |
| `__main__.py` | Python -m support |

### Core Modules

| Module | Purpose |
|--------|---------|
| `agent.py` | Agent configuration and creation |
| `config.py` | CLI configuration management |
| `commands.py` | CLI command handlers |
| `execution.py` | Agent execution loop |
| `input.py` | User input handling |
| `ui.py` | Terminal UI components |
| `tools.py` | CLI-specific tools |
| `shell.py` | Shell command execution |
| `file_ops.py` | File operation utilities |
| `project_utils.py` | Project detection utilities |
| `token_utils.py` | Token counting utilities |
| `agent_memory.py` | Agent memory management |
| `user_interaction.py` | Interactive user dialogs |

### Models (`models/`)

| Module | Purpose |
|--------|---------|
| `base.py` | Base model interface |
| `factory.py` | Model factory |
| `registry.py` | Model registry |
| `providers/anthropic.py` | Anthropic provider |
| `providers/openai.py` | OpenAI provider |
| `providers/google.py` | Google provider |
| `providers/xai.py` | xAI (Grok) provider |

### Integrations (`integrations/`)

| Module | Purpose |
|--------|---------|
| `sandbox_factory.py` | Sandbox creation factory |
| `daytona.py` | Daytona cloud integration |
| `modal.py` | Modal cloud integration |
| `runloop.py` | Runloop integration |
| `error_codes.py` | Error code definitions |

### Hooks (`hooks/`)

| Module | Purpose |
|--------|---------|
| `loader.py` | Hook loader |
| `builtin/security.py` | Security hooks |
| `builtin/logging.py` | Logging hooks |

### Skills (`skills/`)

| Module | Purpose |
|--------|---------|
| `load.py` | Skill loading |
| `commands.py` | Skill commands |
| `middleware.py` | Skill middleware |

### Sessions (`sessions/`)

| Module | Purpose |
|--------|---------|
| `manager.py` | Session management |
| `picker.py` | Session picker UI |

### Custom Commands (`custom_commands/`)

| Module | Purpose |
|--------|---------|
| `load.py` | Command loading |
| `registry.py` | Command registry |
| `tool.py` | Command tools |
| `handler.py` | Command handlers |
| `cli_commands.py` | CLI command definitions |

### Plan (`plan/`)

| Module | Purpose |
|--------|---------|
| `ui.py` | Planning UI |
| `commands.py` | Planning commands |

### MCP (`mcp/`)

| Module | Purpose |
|--------|---------|
| `loader.py` | MCP server loader |

---

## Package: deepagents-harbor (Harbor Integration)

**Version**: 0.0.1
**Path**: `libs/harbor/deepagents_harbor/`
**Description**: Harbor integration with LangChain DeepAgents and LangSmith tracing.

### Modules

| Module | Purpose |
|--------|---------|
| `__init__.py` | Package exports |
| `backend.py` | Harbor backend implementation |
| `tracing.py` | LangSmith tracing integration |
| `deepagents_wrapper.py` | DeepAgents wrapper for Harbor |

### Scripts

| Script | Purpose |
|--------|---------|
| `scripts/analyze.py` | Analysis utilities |
| `scripts/harbor_langsmith.py` | LangSmith integration script |

---

## Built-in Tools (via Middleware)

| Tool | Description | Middleware |
|------|-------------|------------|
| `write_todos` | Create/manage task lists | TodoListMiddleware |
| `read_todos` | Read current todo state | TodoListMiddleware |
| `ls` | List directory contents | FilesystemMiddleware |
| `read_file` | Read file with pagination | FilesystemMiddleware |
| `write_file` | Create/overwrite file | FilesystemMiddleware |
| `edit_file` | String replacements | FilesystemMiddleware |
| `glob` | Find files by pattern | FilesystemMiddleware |
| `grep` | Search text patterns | FilesystemMiddleware |
| `execute`* | Run shell commands | FilesystemMiddleware |
| `task` | Delegate to sub-agents | SubAgentMiddleware |
| `web_search` | Search web via DuckDuckGo (no API key) | WebMiddleware |
| `web_fetch` | Fetch URL content | WebMiddleware |
| `deep_research` | Deep research with LLM synthesis | WebMiddleware |
| `ask_user_question` | Interactive questions | UserInteractionMiddleware |
| `confirm_action` | Request confirmations | UserInteractionMiddleware |
| `enable_ultrathink` | Enable extended thinking | UltrathinkMiddleware |
| `disable_ultrathink` | Disable extended thinking | UltrathinkMiddleware |

*Requires SandboxBackendProtocol implementation

---

## Key Patterns

### Middleware Pattern
```python
from langchain.agents.middleware.types import AgentMiddleware, ModelRequest, ModelResponse

class CustomMiddleware(AgentMiddleware):
    state_schema = MyStateSchema  # Optional TypedDict for state
    tools = [my_tool]  # Tools provided by middleware

    def wrap_model_call(self, request: ModelRequest, handler) -> ModelResponse:
        # Modify request, call handler, process response
        return handler(request)
```

### Agent Creation
```python
from deepagents import create_deep_agent
from deepagents.middleware import UltrathinkMiddleware, WebMiddleware

agent = create_deep_agent(
    model=ChatAnthropic(model_name="claude-sonnet-4-5-20250929"),
    tools=[custom_tool],
    middleware=[
        UltrathinkMiddleware(budget_tokens=10000),
        WebMiddleware(model=llm),  # Web search, fetch, research
    ],
    system_prompt="Your custom instructions",
)
```

### Backend Configuration
```python
from deepagents.backends import FilesystemBackend, CompositeBackend, StoreBackend

agent = create_deep_agent(
    backend=CompositeBackend(
        default=FilesystemBackend(root_dir="/project"),
        routes={"/memories/": StoreBackend(store=InMemoryStore())},
    ),
)
```

### Web Search (DuckDuckGo - No API Key)
```python
from deepagents.middleware.web import web_search_sync, web_fetch_sync, deep_research_sync

# Simple search
results = web_search_sync("Python 3.13 features", max_results=5)

# Fetch URL content
content = web_fetch_sync("https://docs.python.org/3/")

# Deep research with LLM synthesis
from langchain_anthropic import ChatAnthropic
llm = ChatAnthropic(model="claude-sonnet-4-20250514")
report = deep_research_sync("Python async best practices", model=llm)
```

---

## Test Structure

### deepagents tests (`libs/deepagents/tests/`)
- `unit_tests/` - Unit tests (17 files)
  - `middleware/` - Middleware tests (test_ultrathink.py, test_web.py, etc.)
  - `backends/` - Backend tests (8 files)
- `integration_tests/` - Integration tests (5 files)

### deepagents-cli tests (`libs/deepagents-cli/tests/`)
- Unit and integration tests for CLI (~20 files)

### harbor tests (`libs/harbor/tests/`)
- `unit_tests/test_imports.py` - Import verification

**Total test files**: ~51

---

## Development Commands

```bash
# libs/deepagents/
uv sync --all-groups       # Install dependencies
make test                  # Unit tests with coverage
make integration_test      # Integration tests
make lint                  # Ruff + mypy
make format                # Auto-format

# libs/deepagents-cli/
uv sync --all-groups       # Install dependencies
make test                  # Unit tests (socket-disabled)
make test_integration      # Integration tests
make lint                  # Lint check
make format                # Auto-format
uv run deepagents          # Run CLI

# libs/harbor/
uv sync                    # Install dependencies
make test                  # Unit tests
make run-terminal-bench-modal  # Modal benchmarks
make run-terminal-bench-docker # Docker benchmarks

# Run single test
uv run pytest tests/unit_tests/test_file.py::test_function_name
```

---

## Documentation

| Path | Description |
|------|-------------|
| `README.md` | Main documentation |
| `CLAUDE.md` | Claude Code instructions |
| `docs/plans/` | Implementation plans |
| `docs/design/` | Design documents |
| `docs/DEEPAGENTS_VS_CLAUDE_CODE.md` | Feature comparison |
| `libs/deepagents/README.md` | Core library docs |
| `libs/deepagents/deepagents/mcp/README.md` | MCP documentation |
| `libs/deepagents-cli/README.md` | CLI documentation |
| `libs/harbor/README.md` | Harbor documentation |

---

## Configuration Files

| File | Purpose |
|------|---------|
| `libs/deepagents/pyproject.toml` | Core library config |
| `libs/deepagents-cli/pyproject.toml` | CLI config |
| `libs/harbor/pyproject.toml` | Harbor config |
| `.serena/project.yml` | Serena MCP config |
| `.gitignore` | Git ignore rules |
| `LICENSE` | MIT License |

---

## Code Style

| Setting | Value |
|---------|-------|
| Formatter | ruff |
| Line length | 150 (deepagents), 100 (CLI) |
| Docstrings | Google-style |
| Type hints | Required (mypy strict) |
| Tests | pytest + pytest-asyncio |

---

*Generated: 2025-12-10*
