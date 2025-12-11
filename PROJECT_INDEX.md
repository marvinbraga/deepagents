# Deep Agents - Project Documentation Index

> **Version:** 0.3.0 (deepagents) / 0.0.10 (deepagents-cli)
> **Last Updated:** 2025-12-10
> **Repository:** LangGraph-based agent framework for long-horizon AI tasks

---

## Quick Navigation

| Section | Description |
|---------|-------------|
| [Overview](#overview) | Project introduction and key concepts |
| [Architecture](#architecture) | System design and component relationships |
| [Package Reference](#package-reference) | Detailed package documentation |
| [API Reference](#api-reference) | Key functions and classes |
| [Development Guide](#development-guide) | Setup, testing, and contribution |
| [Configuration](#configuration) | Settings and customization |

---

## Overview

**Deep Agents** is a LangGraph-based agent framework implementing three core patterns for long-horizon AI tasks:

1. **Planning** - Structured task decomposition before execution
2. **Computer Access** - File system, shell, and web capabilities
3. **Sub-agent Delegation** - Isolated context windows for parallel/complex work

### Key Features

- **Model Agnostic** - Works with Claude, GPT-4, Gemini, Grok via LangChain
- **Middleware Architecture** - Extensible plugin system for tools and behaviors
- **Pluggable Backends** - State, Filesystem, Store, Composite, Sandbox
- **Progressive Disclosure** - Skills system loads capabilities on demand
- **Human-in-the-Loop** - Configurable approval workflows
- **Web Search** - DuckDuckGo integration (no API key required)
- **Extended Thinking** - Ultrathink support for Claude 4+ with fallback

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         User Input                               │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│            create_deep_agent() / create_cli_agent()              │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Middleware Stack                             │
│  ┌─────────────┬─────────────┬──────────────┬────────────────┐  │
│  │ TodoList    │ Filesystem  │ SubAgents    │ Summarization  │  │
│  ├─────────────┼─────────────┼──────────────┼────────────────┤  │
│  │ PlanMode    │ MCP         │ Hooks        │ Ultrathink     │  │
│  ├─────────────┼─────────────┼──────────────┼────────────────┤  │
│  │ Web         │ UserInteract│ Skills       │ PromptCache    │  │
│  └─────────────┴─────────────┴──────────────┴────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                   LangGraph StateGraph                           │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│         LLM (via ProviderRegistry)                               │
│  ┌──────────┬──────────┬──────────┬──────────┐                  │
│  │ Anthropic│ OpenAI   │ Google   │ XAI      │                  │
│  │ (Claude) │ (GPT-4)  │ (Gemini) │ (Grok)   │                  │
│  └──────────┴──────────┴──────────┴──────────┘                  │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Backend Layer                                 │
│  ┌──────────┬──────────┬──────────┬──────────┐                  │
│  │ State    │ Filesystem│ Store   │ Sandbox  │                  │
│  │ (memory) │ (disk)   │ (persist)│ (Modal/..)│                 │
│  └──────────┴──────────┴──────────┴──────────┘                  │
└─────────────────────────────────────────────────────────────────┘
```

### Directory Structure

```
deepagents/
├── libs/
│   ├── deepagents/              # Core library (v0.3.0)
│   │   └── deepagents/
│   │       ├── graph.py         # create_deep_agent()
│   │       ├── middleware/      # Tool providers
│   │       │   ├── filesystem.py
│   │       │   ├── subagents.py
│   │       │   ├── plan_mode.py
│   │       │   ├── mcp.py
│   │       │   ├── hooks.py
│   │       │   ├── ultrathink.py
│   │       │   ├── user_interaction.py
│   │       │   └── web.py
│   │       ├── backends/        # Storage providers
│   │       │   ├── state.py
│   │       │   ├── filesystem.py
│   │       │   ├── store.py
│   │       │   ├── composite.py
│   │       │   └── sandbox.py
│   │       ├── hooks/           # Event hooks
│   │       └── mcp/             # MCP integration
│   │
│   ├── deepagents-cli/          # CLI application (v0.0.10)
│   │   └── deepagents_cli/
│   │       ├── main.py          # Entry point
│   │       ├── agent.py         # Agent creation
│   │       ├── tools.py         # CLI tools
│   │       ├── skills/          # Progressive disclosure
│   │       ├── sessions/        # Session management
│   │       ├── custom_commands/ # Slash commands
│   │       ├── models/          # Provider registry
│   │       │   └── providers/   # Anthropic, OpenAI, Google, XAI
│   │       └── integrations/    # Sandbox providers
│   │
│   └── harbor/                  # Benchmarking (v0.0.1)
│       └── deepagents_harbor/
│
├── docs/
│   └── DEEPAGENTS_VS_CLAUDE_CODE.md  # Feature comparison
├── CLAUDE.md                    # Claude Code integration
└── README.md                    # Main documentation
```

---

## Package Reference

### deepagents (Core Library)

**Location:** `libs/deepagents/`
**Version:** 0.3.0
**Python:** >=3.11

#### Entry Point

```python
from deepagents import create_deep_agent

agent = create_deep_agent(
    model="anthropic:claude-sonnet-4-20250514",
    tools=[my_custom_tool],
    system_prompt="Your task-specific instructions",
    middleware=[MyMiddleware()],
    subagents=[research_agent, analysis_agent],
    backend=FilesystemBackend(root_dir="/project"),
    interrupt_on={"execute": True},
)

result = agent.invoke({"messages": [{"role": "user", "content": "..."}]})
```

#### Middleware Reference

| Middleware | Purpose | Tools Provided |
|------------|---------|----------------|
| `TodoListMiddleware` | Task tracking | `write_todos`, `read_todos` |
| `FilesystemMiddleware` | File operations | `ls`, `read_file`, `write_file`, `edit_file`, `glob`, `grep`, `execute` |
| `SubAgentMiddleware` | Task delegation | `task` |
| `PlanModeMiddleware` | Planning workflow | `enter_plan_mode`, `submit_plan`, `complete_plan_step`, `exit_plan_mode` |
| `MCPMiddleware` | MCP protocol | Server-defined tools |
| `HooksMiddleware` | Event hooks | - |
| `UltrathinkMiddleware` | Extended thinking | `enable_ultrathink`, `disable_ultrathink` |
| `UserInteractionMiddleware` | User dialogs | `ask_user_question`, `confirm_action` |
| `WebMiddleware` | Web access | `web_search`, `web_fetch`, `deep_research` |
| `SummarizationMiddleware` | Context management | - |
| `AnthropicPromptCachingMiddleware` | Cost optimization | - |
| `PatchToolCallsMiddleware` | Tool call fixes | - |

#### Backend Reference

| Backend | Description | Use Case |
|---------|-------------|----------|
| `StateBackend` | In-memory ephemeral | Default, single-session |
| `FilesystemBackend` | Real disk operations | Local development |
| `StoreBackend` | LangGraph Store | Cross-session persistence |
| `CompositeBackend` | Path-based routing | Hybrid storage |
| `SandboxBackendProtocol` | Sandboxed execution | Modal, Runloop, Daytona |

#### Optional Dependencies

```bash
pip install deepagents[web]   # DuckDuckGo search
pip install deepagents[mcp]   # MCP protocol
pip install deepagents[all]   # All optional features
```

---

### deepagents-cli (CLI Application)

**Location:** `libs/deepagents-cli/`
**Version:** 0.0.10
**Python:** >=3.11

#### Running the CLI

```bash
# Install
pip install deepagents-cli

# Run
deepagents                      # Start interactive session
deepagents --agent myagent      # Use specific agent
deepagents --resume             # Resume last session
deepagents --new                # Force new session
```

#### Module Reference

| Module | Purpose |
|--------|---------|
| `main.py` | CLI entry point |
| `agent.py` | `create_cli_agent()`, `create_agent_with_all_features()` |
| `tools.py` | Web search, HTTP requests, fetch URL |
| `config.py` | Configuration management |
| `execution.py` | Agent execution loop |
| `ui.py` | Terminal UI components |
| `shell.py` | Shell command execution |
| `user_interaction.py` | Interactive dialogs |
| `agent_memory.py` | Memory management |
| `token_utils.py` | Token counting |

#### Configuration Hierarchy

```
~/.deepagents/                  # Global config
    ├── agent.md                # Default agent prompt
    ├── skills/                 # Global skills
    └── commands/               # Global slash commands

~/.deepagents/<agent>/          # Agent-specific
    ├── agent.md
    ├── skills/
    └── commands/

.deepagents/                    # Project-specific (in project root)
    ├── agent.md
    ├── skills/
    └── commands/
```

#### Model Providers

```python
from deepagents_cli.models import create_model

# Supported providers
model = create_model("anthropic:claude-sonnet-4-20250514")
model = create_model("openai:gpt-4o")
model = create_model("google:gemini-2.0-flash")
model = create_model("xai:grok-3")
```

#### Sessions

| Module | Purpose |
|--------|---------|
| `sessions/manager.py` | Session CRUD (SQLite) |
| `sessions/picker.py` | Interactive session picker |

Sessions are linked to project path and git branch, with automatic cleanup.

---

### harbor (Benchmarking)

**Location:** `libs/harbor/`
**Version:** 0.0.1
**Purpose:** Benchmark integration for agent evaluation

```bash
make run-terminal-bench-modal   # Run on Modal
make run-terminal-bench-docker  # Run locally
```

| Module | Purpose |
|--------|---------|
| `backend.py` | Harbor backend |
| `tracing.py` | LangSmith integration |
| `deepagents_wrapper.py` | DeepAgents wrapper |

---

## API Reference

### Core Functions

#### `create_deep_agent()`

```python
def create_deep_agent(
    model: str | BaseChatModel | None = None,
    tools: Sequence[BaseTool | Callable | dict] | None = None,
    *,
    system_prompt: str | None = None,
    middleware: Sequence[AgentMiddleware] = (),
    subagents: list[SubAgent | CompiledSubAgent] | None = None,
    response_format: ResponseFormat | None = None,
    context_schema: type[Any] | None = None,
    checkpointer: Checkpointer | None = None,
    store: BaseStore | None = None,
    backend: BackendProtocol | BackendFactory | None = None,
    interrupt_on: dict[str, bool | InterruptOnConfig] | None = None,
    debug: bool = False,
    name: str | None = None,
    cache: BaseCache | None = None,
) -> CompiledStateGraph
```

**Default middleware stack:**
- `TodoListMiddleware`
- `FilesystemMiddleware`
- `SubAgentMiddleware`
- `SummarizationMiddleware` (170k tokens trigger)
- `AnthropicPromptCachingMiddleware`
- `PatchToolCallsMiddleware`

### Built-in Tools

| Tool | Parameters | Description |
|------|------------|-------------|
| `write_todos` | `todos: list[TodoItem]` | Create/update task list |
| `read_todos` | - | Read current task list |
| `ls` | `path: str` | List directory contents |
| `read_file` | `path: str, offset?: int, limit?: int` | Read file with pagination |
| `write_file` | `path: str, content: str` | Create/overwrite file |
| `edit_file` | `path: str, old: str, new: str` | String replacement |
| `glob` | `pattern: str` | Find files by pattern |
| `grep` | `pattern: str, path?: str` | Search file contents |
| `execute`* | `command: str` | Run shell command |
| `task` | `agent: str, prompt: str` | Delegate to sub-agent |
| `ask_user_question` | `question: str, options?: list` | Interactive question |
| `confirm_action` | `action: str, severity: str` | Request confirmation |
| `web_search` | `query: str, max_results?: int` | DuckDuckGo search |
| `web_fetch` | `url: str` | Fetch URL content |
| `deep_research` | `topic: str` | Multi-step LLM research |
| `enable_ultrathink` | `budget_tokens?: int` | Enable extended thinking |
| `disable_ultrathink` | - | Disable extended thinking |

*Requires `SandboxBackendProtocol` implementation

---

## Development Guide

### Prerequisites

- Python 3.11+
- `uv` package manager

### Setup

```bash
# Clone repository
git clone https://github.com/langchain-ai/deepagents.git
cd deepagents

# Install deepagents core
cd libs/deepagents
uv sync --all-groups

# Install CLI
cd ../deepagents-cli
uv sync --all-groups
```

### Commands

#### deepagents (core)

```bash
make test              # Unit tests with coverage
make integration_test  # Integration tests
make lint              # Ruff + mypy
make format            # Auto-format
```

#### deepagents-cli

```bash
make test              # Unit tests (socket-disabled)
make test_integration  # Integration tests
make lint              # Lint check
make format            # Auto-format
uv run deepagents      # Run CLI
```

#### harbor

```bash
make test                       # Unit tests
make run-terminal-bench-modal   # Modal benchmarks
make run-terminal-bench-docker  # Docker benchmarks
```

### Running Single Tests

```bash
uv run pytest tests/unit_tests/test_file.py::test_function
make test TEST_FILE=tests/unit_tests/test_specific.py
```

### Code Style

| Setting | Value |
|---------|-------|
| Formatter | Ruff |
| Line length | 150 (core), 100 (CLI) |
| Docstrings | Google style |
| Type hints | Required (mypy strict) |
| Async tests | pytest-asyncio |

---

## Configuration

### Environment Variables

| Variable | Description |
|----------|-------------|
| `ANTHROPIC_API_KEY` | Anthropic API key |
| `OPENAI_API_KEY` | OpenAI API key |
| `GOOGLE_API_KEY` | Google AI API key |
| `XAI_API_KEY` | xAI API key |
| `TAVILY_API_KEY` | Tavily search (optional) |

### Agent Configuration (`agent.md`)

```markdown
# Agent Name

Instructions for your agent...

## Skills
- skill1: Description
- skill2: Description

## Memory Protocol
1. Check `/memories/` at session start
2. Save learnings to `/memories/[topic].md`
```

### Slash Commands

```yaml
---
name: review
description: Code review command
aliases: [cr, check]
args:
  - name: target
    description: Target file or directory
    required: false
    default: "."
---
Review the code in {target}...
```

---

## Usage Examples

### Basic Agent

```python
from deepagents import create_deep_agent

agent = create_deep_agent(
    system_prompt="You are a helpful coding assistant.",
)
result = agent.invoke({"messages": [{"role": "user", "content": "Hello!"}]})
```

### With Custom Tools

```python
from deepagents import create_deep_agent

def weather(city: str) -> str:
    """Get weather for a city."""
    return f"Weather in {city}: Sunny"

agent = create_deep_agent(tools=[weather])
```

### With Web Search

```python
from deepagents import create_deep_agent
from deepagents.middleware import WebMiddleware
from langchain_anthropic import ChatAnthropic

llm = ChatAnthropic(model="claude-sonnet-4-20250514")
agent = create_deep_agent(
    middleware=[WebMiddleware(model=llm)],
)
```

### With Extended Thinking

```python
from deepagents import create_deep_agent
from deepagents.middleware import UltrathinkMiddleware

agent = create_deep_agent(
    middleware=[UltrathinkMiddleware(budget_tokens=10000)],
)
```

### With Filesystem Backend

```python
from deepagents import create_deep_agent
from deepagents.backends import FilesystemBackend

agent = create_deep_agent(
    backend=FilesystemBackend(root_dir="/path/to/project"),
)
```

### With Memory Persistence

```python
from deepagents import create_deep_agent
from deepagents.backends import CompositeBackend, StateBackend, StoreBackend
from langgraph.store.memory import InMemoryStore

agent = create_deep_agent(
    backend=CompositeBackend(
        default=StateBackend(),
        routes={"/memories/": StoreBackend(store=InMemoryStore())},
    ),
)
```

### With Sub-agents

```python
from deepagents import create_deep_agent

research_agent = {
    "name": "researcher",
    "description": "Researches topics in depth",
    "prompt": "You are an expert researcher.",
    "model": "openai:gpt-4o",
}

agent = create_deep_agent(subagents=[research_agent])
```

---

## Cross-References

### Internal Documentation

| Document | Description |
|----------|-------------|
| [README.md](README.md) | Project introduction |
| [CLAUDE.md](CLAUDE.md) | Claude Code integration |
| [docs/DEEPAGENTS_VS_CLAUDE_CODE.md](docs/DEEPAGENTS_VS_CLAUDE_CODE.md) | Feature comparison |
| [libs/deepagents/README.md](libs/deepagents/README.md) | Core library docs |
| [libs/deepagents-cli/README.md](libs/deepagents-cli/README.md) | CLI docs |
| [libs/harbor/README.md](libs/harbor/README.md) | Benchmarking docs |

### External Resources

| Resource | URL |
|----------|-----|
| Documentation | https://docs.langchain.com/oss/python/deepagents/overview |
| API Reference | https://reference.langchain.com/python/deepagents/ |
| Quickstarts | https://github.com/langchain-ai/deepagents-quickstarts |
| LangGraph | https://docs.langchain.com/oss/python/langgraph/overview |

---

## Feature Comparison with Claude Code

| Category | DeepAgents | Claude Code |
|----------|------------|-------------|
| Filesystem tools | 95% | Native |
| Task management | 90% | Native |
| Sub-agents | 85% (more flexible) | Native |
| Plan mode | 80% | Native |
| MCP integration | 90% | Native |
| Memory/Persistence | 85% | Native |
| Web tools | 95% | Native |
| User interaction | 95% | Native |
| Extended thinking | 95% | Native |
| Slash commands | 95% | Native |
| Model providers | 95% (multi-vendor) | Anthropic only |
| Multimodal | 20% | Native |

See [docs/DEEPAGENTS_VS_CLAUDE_CODE.md](docs/DEEPAGENTS_VS_CLAUDE_CODE.md) for detailed comparison.

---

*Generated with /sc:index command | 2025-12-10*
