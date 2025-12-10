# DeepAgents vs Claude Code: Análise Comparativa

## Sumário Executivo

O **DeepAgents** é uma implementação open-source inspirada em agentes de codificação como **Claude Code** e **Manus**. Este documento analisa as semelhanças arquiteturais, diferenças de implementação e gaps de funcionalidade entre os dois sistemas.

---

## 1. Visão Geral Arquitetural

### 1.1 Claude Code

Claude Code é o CLI oficial da Anthropic para interação com Claude em tarefas de engenharia de software. Características principais:

| Aspecto | Claude Code |
|---------|-------------|
| **Runtime** | CLI nativo em TypeScript/JavaScript |
| **Modelo** | Claude (Sonnet, Opus) via API Anthropic |
| **Contexto** | ~200K tokens com sumarização automática |
| **Persistência** | Checkpointing, memória de sessão |
| **Extensibilidade** | MCP servers, hooks, slash commands |

### 1.2 DeepAgents

DeepAgents é um harness de agentes construído sobre LangChain/LangGraph:

| Aspecto | DeepAgents |
|---------|------------|
| **Runtime** | Python, baseado em LangGraph StateGraph |
| **Modelo** | Agnóstico (default: Claude Sonnet 4) |
| **Contexto** | Sumarização em ~170K tokens |
| **Persistência** | StateBackend, StoreBackend, CompositeBackend |
| **Extensibilidade** | Middleware, MCP, hooks customizados |

---

## 2. Comparação de Ferramentas Built-in

### 2.1 Ferramentas de Filesystem

| Ferramenta | Claude Code | DeepAgents | Equivalência |
|------------|-------------|------------|--------------|
| Listar arquivos | `Glob` | `ls` | ✅ Similar |
| Busca por padrão | `Glob` | `glob` | ✅ Idêntico |
| Busca em conteúdo | `Grep` | `grep` | ✅ Idêntico |
| Ler arquivo | `Read` | `read_file` | ✅ Similar |
| Escrever arquivo | `Write` | `write_file` | ✅ Similar |
| Editar arquivo | `Edit` | `edit_file` | ✅ Similar |
| Executar comando | `Bash` | `execute` | ⚠️ Parcial |

### 2.2 Ferramentas de Planejamento

| Ferramenta | Claude Code | DeepAgents | Equivalência |
|------------|-------------|------------|--------------|
| Lista de tarefas | `TodoWrite` | `write_todos`, `read_todos` | ✅ Similar |
| Modo de planejamento | `EnterPlanMode`, `ExitPlanMode` | `PlanModeMiddleware` | ✅ Similar |
| Delegação | `Task` (subagents) | `task` (SubAgentMiddleware) | ✅ Similar |

### 2.3 Ferramentas de Web/API

| Ferramenta | Claude Code | DeepAgents | Equivalência |
|------------|-------------|------------|--------------|
| Busca web | `WebSearch` | `web_search` (DuckDuckGo) | ✅ Idêntico (sem API key) |
| Fetch URL | `WebFetch` | `web_fetch` | ✅ Similar |
| Deep Research | N/A | `deep_research` | ✅ Exclusivo DeepAgents |
| HTTP requests | Via Bash/curl | `http_request` | ✅ Similar |

---

## 3. Análise de Middleware

### 3.1 Arquitetura de Middleware

**Claude Code** usa um sistema de middleware interno não exposto diretamente ao usuário.

**DeepAgents** expõe middleware como componentes reutilizáveis:

```python
# libs/deepagents/deepagents/graph.py:112-139
deepagent_middleware = [
    TodoListMiddleware(),
    FilesystemMiddleware(backend=backend),
    SubAgentMiddleware(
        default_model=model,
        default_tools=tools,
        subagents=subagents,
        ...
    ),
    SummarizationMiddleware(
        model=model,
        trigger=("tokens", 170000),
        keep=("messages", 6),
    ),
    AnthropicPromptCachingMiddleware(...),
    PatchToolCallsMiddleware(),
]
```

### 3.2 Middleware Disponíveis

| Middleware | Descrição | Claude Code Equivalente |
|------------|-----------|-------------------------|
| `TodoListMiddleware` | Gestão de tarefas | TodoWrite nativo |
| `FilesystemMiddleware` | Operações de arquivo | Tools nativos |
| `SubAgentMiddleware` | Delegação a sub-agentes | Task tool |
| `SummarizationMiddleware` | Compressão de contexto | Sumarização automática |
| `MCPMiddleware` | Integração MCP | MCP servers |
| `HooksMiddleware` | Validação/logging de tools | Hooks system |
| `PlanModeMiddleware` | Fluxo de planejamento | EnterPlanMode/ExitPlanMode |
| `AnthropicPromptCachingMiddleware` | Cache de prompts | Interno (não exposto) |
| `PatchToolCallsMiddleware` | Correção de tool calls | Interno |
| `UltrathinkMiddleware` | Extended thinking para raciocínio profundo | Interno (thinking mode) |
| `UserInteractionMiddleware` | Perguntas interativas e confirmações | AskUserQuestion |
| `WebMiddleware` | Busca web e pesquisa profunda (DuckDuckGo) | WebSearch + WebFetch |

---

## 4. Sistema de Sub-Agentes

### 4.1 Claude Code

```typescript
// Task tool com subagent_type especializado
Task({
    subagent_type: "Explore" | "Plan" | "general-purpose",
    prompt: "...",
    model: "sonnet" | "opus" | "haiku"
})
```

Características:
- Sub-agentes especializados pré-definidos
- Contexto isolado por invocação
- Modelo configurável por sub-agente
- Execução paralela suportada

### 4.2 DeepAgents

```python
# libs/deepagents/deepagents/middleware/subagents.py
research_subagent = {
    "name": "research-agent",
    "description": "Used to research in-depth questions",
    "prompt": "You are an expert researcher",
    "tools": [internet_search],
    "model": "openai:gpt-4o",
}

agent = create_deep_agent(subagents=[research_subagent])
```

Características:
- Sub-agentes customizáveis
- Suporta `SubAgent` (dict) ou `CompiledSubAgent` (LangGraph)
- General-purpose agent automático
- Middleware herdado configurável

---

## 5. Sistema de Backends

### 5.1 Arquitetura de Backends (DeepAgents)

```
BackendProtocol
├── StateBackend (efêmero, em memória)
├── FilesystemBackend (disco local)
├── StoreBackend (LangGraph Store, persistente)
├── CompositeBackend (roteamento por path)
└── SandboxBackendProtocol
    └── Sandbox providers (Modal, Runloop, Daytona)
```

### 5.2 Comparação

| Aspecto | Claude Code | DeepAgents |
|---------|-------------|------------|
| Armazenamento padrão | Filesystem local | StateBackend (efêmero) |
| Persistência cross-sessão | Checkpointer | StoreBackend |
| Sandbox | Container interno | Modal/Runloop/Daytona |
| Routing por path | Não aplicável | CompositeBackend |

---

## 6. Plan Mode

### 6.1 Claude Code

O Plan Mode no Claude Code é uma funcionalidade que permite:
1. Entrada em modo de planejamento via `EnterPlanMode`
2. Exploração do codebase (apenas ferramentas de leitura)
3. Criação de plano detalhado
4. Aprovação do usuário
5. Execução via `ExitPlanMode`

### 6.2 DeepAgents

```python
# libs/deepagents/deepagents/middleware/plan_mode.py:95-587
class PlanModeMiddleware(AgentMiddleware):
    """
    1. Planning phase: Agent explores codebase and creates a detailed plan
    2. Execution phase: Agent implements the approved plan step by step
    """
```

**Ferramentas disponíveis:**
- `enter_plan_mode(goal, plan_file)` - Inicia planejamento
- `submit_plan(title, description, steps, ...)` - Submete plano
- `complete_plan_step(step_id, result)` - Marca step completo
- `exit_plan_mode()` - Sai do modo

**Fases:**
- `PLANNING` - Exploração, ferramentas de escrita bloqueadas
- `AWAITING_APPROVAL` - Aguardando aprovação do usuário
- `EXECUTING` - Implementação do plano
- `COMPLETED` - Finalizado

---

## 7. MCP (Model Context Protocol)

### 7.1 Claude Code

- Configuração via `mcp.json` ou `CLAUDE.md`
- Servers conectados automaticamente
- Tools prefixados com `mcp__<server>__<tool>`
- Resources e prompts disponíveis

### 7.2 DeepAgents

```python
# libs/deepagents/deepagents/middleware/mcp.py:17-262
class MCPMiddleware(AgentMiddleware):
    """MCP middleware for Model Context Protocol integration."""

    async def initialize(self):
        """Connect to all configured MCP servers."""

    def get_tools(self) -> list[BaseTool]:
        """Get tools from all connected MCP servers."""

    def get_system_prompt_addition(self) -> str:
        """Get MCP server instructions for system prompt."""
```

**Características:**
- Auto-connect em inicialização
- Tools via `langchain-mcp-adapters`
- System prompt dinâmico com instruções de servers
- Async context manager suportado

---

## 8. Sistema de Memória

### 8.1 Claude Code

- Memória de sessão via checkpointer
- `CLAUDE.md` para instruções persistentes
- Contexto limitado com sumarização automática

### 8.2 DeepAgents

```python
# libs/deepagents-cli/deepagents_cli/agent_memory.py
class AgentMemoryMiddleware(AgentMiddleware):
    """Long-term memory middleware for persistent agent state."""
```

**Implementação via CompositeBackend:**
```python
backend = CompositeBackend(
    default=StateBackend(),  # Efêmero
    routes={"/memories/": StoreBackend(store=InMemoryStore())},  # Persistente
)
```

**Protocol de memória (default_agent_prompt.md):**
1. Check `ls /memories/` no início da sessão
2. Preferir conhecimento salvo sobre conhecimento geral
3. Salvar aprendizado em `/memories/[topic].md`

---

## 9. Gaps e Diferenças

### 9.1 Funcionalidades Exclusivas do Claude Code

| Funcionalidade | Descrição | Status no DeepAgents |
|----------------|-----------|----------------------|
| `AskUserQuestion` | Perguntas interativas estruturadas | ✅ Implementado (UserInteractionMiddleware) |
| `NotebookEdit` | Edição de Jupyter notebooks | ❌ Não implementado |
| Slash commands nativos | `/help`, `/clear`, etc. | ✅ Implementado (CustomCommands) |
| Git integration nativo | Commits, PRs via tools | ⚠️ Via Bash/execute |
| Screenshot/Image support | Leitura de imagens | ❌ Não implementado |
| PDF reading | Leitura de PDFs | ❌ Não implementado |
| `WebSearch` nativo | Busca sem API key extra | ✅ Implementado (WebMiddleware/DuckDuckGo) |
| Sequential thinking | `mcp__sequential-thinking` | ✅ Implementado (UltrathinkMiddleware) |
| Session management | Persistência de sessões | ✅ Implementado (SessionManager) |

### 9.2 Funcionalidades Exclusivas do DeepAgents

| Funcionalidade | Descrição |
|----------------|-----------|
| Model-agnostic | Suporta qualquer LLM via LangChain (Anthropic, OpenAI, Google, XAI) |
| CompositeBackend | Roteamento flexível de storage |
| Middleware extensível | API pública para customização |
| SubAgents customizados | Criar sub-agentes com lógica própria |
| LangGraph integration | Checkpointer, Store, Studio |
| Sandbox providers | Modal, Runloop, Daytona |
| UltrathinkMiddleware | Extended thinking nativo com fallback para modelos não-Claude |
| ProviderRegistry | Sistema de registro de providers de modelos |
| CustomCommands | Sistema extensível de slash commands com índices e aliases |
| SessionManager | Gerenciamento de sessões com persistência via SQLite |
| WebMiddleware | Busca web via DuckDuckGo (sem API key) + Deep Research com LLM |

---

## 10. Tabela Resumo de Paridade

| Categoria | Paridade | Observação |
|-----------|----------|------------|
| Filesystem tools | 95% | Praticamente idêntico |
| Task management | 90% | Muito similar |
| Sub-agents | 85% | DeepAgents mais flexível |
| Plan mode | 80% | Conceito similar, API diferente |
| MCP integration | 90% | DeepAgents usa langchain-mcp-adapters |
| Memory/Persistence | 85% | SessionManager e CompositeBackend |
| Web tools | 95% | WebMiddleware com DuckDuckGo (sem API key) |
| User interaction | 95% | UserInteractionMiddleware completo |
| Multimodal | 20% | Sem suporte a imagens/PDFs |
| Extended thinking | 95% | UltrathinkMiddleware com fallback |
| Slash commands | 95% | CustomCommands com índices e aliases |
| Model providers | 95% | Registry com Anthropic, OpenAI, Google, XAI |

---

## 11. Arquitetura de Código

### 11.1 Estrutura do DeepAgents

```
libs/
├── deepagents/              # Core library
│   └── deepagents/
│       ├── graph.py         # create_deep_agent()
│       ├── middleware/      # TodoList, Filesystem, SubAgent, MCP, Hooks, PlanMode, Ultrathink
│       ├── backends/        # State, Filesystem, Store, Composite, Sandbox
│       ├── hooks/           # Hook system (registry, executor, types)
│       ├── mcp/             # MCP utilities (client, protocol, tool_adapter)
│       └── plan/            # Plan mode utilities
├── deepagents-cli/          # CLI application
│   └── deepagents_cli/
│       ├── main.py          # CLI entry point
│       ├── agent.py         # create_agent_with_all_features()
│       ├── tools.py         # web_search, http_request, fetch_url
│       ├── skills/          # Skills middleware
│       ├── mcp/             # MCP config loading
│       ├── hooks/           # Hooks config loading (builtin: security, logging)
│       ├── models/          # Model providers (Anthropic, OpenAI, Google, XAI)
│       ├── custom_commands/ # Slash commands system
│       ├── sessions/        # Session management (SessionManager, picker)
│       └── integrations/    # Sandbox providers (Modal, Runloop, Daytona)
└── harbor/                  # Benchmark management
```

### 11.2 Fluxo de Execução

```
User Input
    ↓
create_deep_agent() / create_agent_with_all_features()
    ↓
Middleware Stack (compose)
    ├── AgentMemoryMiddleware
    ├── SkillsMiddleware
    ├── ShellMiddleware
    ├── HooksMiddleware
    ├── PlanModeMiddleware
    ├── MCPMiddleware
    ├── TodoListMiddleware
    ├── FilesystemMiddleware
    ├── SubAgentMiddleware
    ├── WebMiddleware
    ├── SummarizationMiddleware
    ├── UltrathinkMiddleware
    ├── UserInteractionMiddleware
    └── AnthropicPromptCachingMiddleware
    ↓
LangGraph StateGraph
    ↓
LLM (via ProviderRegistry: Claude/GPT/Gemini/Grok)
    ↓
Tool Execution (via Backend)
    ↓
Response (persisted via SessionManager)
```

---

## 12. Ultrathink (Extended Thinking)

### 12.1 Claude Code

O Claude Code usa extended thinking internamente através da API da Anthropic, permitindo que o modelo raciocine mais profundamente antes de responder.

### 12.2 DeepAgents

O DeepAgents implementa o `UltrathinkMiddleware` com suporte nativo para Claude 4+ e fallback para outros modelos:

```python
# libs/deepagents/deepagents/middleware/ultrathink.py
class UltrathinkMiddleware(AgentMiddleware):
    """Middleware for extended thinking capabilities."""

    def __init__(
        self,
        budget_tokens: int = 10000,      # Token budget (1024-128000)
        enabled_by_default: bool = False,
        interleaved_thinking: bool = True,
        fallback_mode: Literal["tool", "prompt", "both"] = "both",
    ):
```

**Características:**
- Para Claude 4+: usa API nativa de extended thinking
- Para outros modelos: fallback via `think_step_by_step` tool
- Budget de tokens configurável (1024-128000)
- Interleaved thinking entre tool calls
- Ferramentas: `enable_ultrathink()`, `disable_ultrathink()`

---

## 13. Sistema de Slash Commands

### 13.1 Claude Code

Usa slash commands nativos (`/help`, `/clear`) e slash commands customizados via `.claude/commands/`.

### 13.2 DeepAgents

O `CustomCommands` implementa um sistema completo de slash commands:

```python
# libs/deepagents-cli/deepagents_cli/custom_commands/cli_commands.py
# deepagents commands list --agent <agent> [--project] [--global]
# deepagents commands create <name> [--index <index>] [--project] [--global]
# deepagents commands info <name>
```

**Hierarquia de comandos:**
```
~/.deepagents/commands/           # Global commands
~/.deepagents/<agent>/commands/   # Agent-specific commands
.deepagents/commands/             # Project commands
```

**Formato de comando (YAML frontmatter):**
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
# Template with variables: {target}, {project_root}, {cwd}
```

---

## 14. Sistema de Providers de Modelo

### 14.1 DeepAgents ProviderRegistry

O DeepAgents implementa um sistema de registro de providers para suportar múltiplos LLMs:

```python
# libs/deepagents-cli/deepagents_cli/models/providers/
├── anthropic.py   # AnthropicProvider (Claude)
├── openai.py      # OpenAIProvider (GPT-4, o1, etc)
├── google.py      # GoogleProvider (Gemini)
└── xai.py         # XAIProvider (Grok)
```

**Registry pattern:**
```python
from deepagents_cli.models import create_model, get_registry

# Criar modelo por string
model = create_model("anthropic:claude-sonnet-4-20250514")
model = create_model("openai:gpt-4o")
model = create_model("google:gemini-2.0-flash")
model = create_model("xai:grok-3")

# Listar providers disponíveis
registry = get_registry()
available = registry.get_available()  # providers com API key configurada
```

---

## 15. Gerenciamento de Sessões

### 15.1 Claude Code

Persistência de sessão via checkpointer interno.

### 15.2 DeepAgents SessionManager

O DeepAgents implementa gerenciamento de sessões com persistência em SQLite:

```python
# libs/deepagents-cli/deepagents_cli/sessions/manager.py
@dataclass
class SessionInfo:
    session_id: str
    created_at: datetime
    updated_at: datetime
    project_path: str
    git_branch: str | None
    description: str | None

class SessionManager:
    def create_session(self, description: str | None = None) -> SessionInfo
    def list_sessions(self, limit: int = 10) -> list[SessionInfo]
    def get_most_recent_session(self) -> SessionInfo | None
    def update_session(self, session_id: str, ...) -> None
    def delete_session(self, session_id: str) -> None
```

**Características:**
- Sessões vinculadas a projeto e branch git
- Picker interativo para retomar sessões
- Histórico de conversas persistente
- Cleanup automático de sessões antigas

---

## 16. Conclusão

O **DeepAgents** é uma reimplementação bem-sucedida dos conceitos fundamentais do Claude Code:

**Pontos Fortes:**
- Arquitetura modular e extensível
- Model-agnostic (não preso a um provedor)
- Sistema de backends flexível
- Integração nativa com LangGraph ecosystem
- Middleware como componentes reutilizáveis

**Áreas de Melhoria:**
- Suporte multimodal (imagens, PDFs)
- Integração Git mais profunda

**Recomendação:**
Para usuários que precisam de flexibilidade de modelo ou integração com ecossistema LangChain, DeepAgents é uma excelente alternativa. Para usuários que precisam de funcionalidades avançadas como multimodal ou máxima integração com Claude, o Claude Code oficial continua sendo a escolha mais completa.

---

*Documento atualizado em: 2025-12-10*
*Versão do DeepAgents analisada: commit 96a1b47 (develop)*
*Versão anterior: 2025-12-05 (commit ad6e116)*
