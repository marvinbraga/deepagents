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
│   ├── deepagents/          # Core library (v0.2.8)
│   ├── deepagents-cli/      # CLI application (v0.0.10)
│   └── harbor/              # Harbor integration (v0.0.1)
├── docs/
│   └── plans/               # Implementation plans
└── .claude/                 # Claude Code configuration
```

---

## Package: deepagents (Core Library)

**Version**: 0.2.8
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
from deepagents.middleware import UltrathinkMiddleware

agent = create_deep_agent(
    model=ChatAnthropic(model_name="claude-sonnet-4-5-20250929"),
    tools=[custom_tool],
    middleware=[UltrathinkMiddleware(budget_tokens=10000)],
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

---

## Test Structure

### deepagents tests (`libs/deepagents/tests/`)
- `unit_tests/` - Unit tests
  - `middleware/` - Middleware tests (test_ultrathink.py, etc.)
  - `backends/` - Backend tests
- `integration_tests/` - Integration tests (test_ultrathink.py, etc.)

### deepagents-cli tests (`libs/deepagents-cli/tests/`)
- Unit and integration tests for CLI

### harbor tests (`libs/harbor/tests/`)
- `unit_tests/test_imports.py` - Import verification

---

## Documentation

| Path | Description |
|------|-------------|
| `README.md` | Main documentation |
| `docs/plans/` | Implementation plans |
| `libs/deepagents/deepagents/mcp/README.md` | MCP documentation |
| `libs/harbor/README.md` | Harbor documentation |
| `libs/deepagents-cli/README.md` | CLI documentation |

---

## Configuration Files

| File | Purpose |
|------|---------|
| `libs/deepagents/pyproject.toml` | Core library config |
| `libs/deepagents-cli/pyproject.toml` | CLI config |
| `libs/harbor/pyproject.toml` | Harbor config |
| `.gitignore` | Git ignore rules |
| `LICENSE` | MIT License |

---

*Generated: 2025-12-06*
