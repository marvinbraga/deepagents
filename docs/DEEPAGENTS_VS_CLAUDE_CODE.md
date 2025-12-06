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
| Busca web | `WebSearch` | `web_search` (Tavily) | ✅ Similar |
| Fetch URL | `WebFetch` | `fetch_url` | ✅ Similar |
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
| Slash commands nativos | `/help`, `/clear`, etc. | ⚠️ Parcial (skills) |
| Git integration nativo | Commits, PRs via tools | ⚠️ Via Bash/execute |
| Screenshot/Image support | Leitura de imagens | ❌ Não implementado |
| PDF reading | Leitura de PDFs | ❌ Não implementado |
| `WebSearch` nativo | Busca sem API key extra | ⚠️ Requer Tavily |
| Sequential thinking | `mcp__sequential-thinking` | ⚠️ Via MCP externo |

### 9.2 Funcionalidades Exclusivas do DeepAgents

| Funcionalidade | Descrição |
|----------------|-----------|
| Model-agnostic | Suporta qualquer LLM via LangChain |
| CompositeBackend | Roteamento flexível de storage |
| Middleware extensível | API pública para customização |
| SubAgents customizados | Criar sub-agentes com lógica própria |
| LangGraph integration | Checkpointer, Store, Studio |
| Sandbox providers | Modal, Runloop, Daytona |

---

## 10. Tabela Resumo de Paridade

| Categoria | Paridade | Observação |
|-----------|----------|------------|
| Filesystem tools | 95% | Praticamente idêntico |
| Task management | 90% | Muito similar |
| Sub-agents | 85% | DeepAgents mais flexível |
| Plan mode | 80% | Conceito similar, API diferente |
| MCP integration | 90% | DeepAgents usa langchain-mcp-adapters |
| Memory/Persistence | 75% | DeepAgents mais configurável |
| Web tools | 70% | Requer API keys extras |
| User interaction | 90% | AskUserQuestion implementado |
| Multimodal | 20% | Sem suporte a imagens/PDFs |

---

## 11. Arquitetura de Código

### 11.1 Estrutura do DeepAgents

```
libs/
├── deepagents/              # Core library
│   └── deepagents/
│       ├── graph.py         # create_deep_agent()
│       ├── middleware/      # TodoList, Filesystem, SubAgent, MCP, Hooks, PlanMode
│       ├── backends/        # State, Filesystem, Store, Composite, Sandbox
│       ├── hooks/           # Hook system
│       ├── mcp/             # MCP utilities
│       └── plan/            # Plan mode utilities
├── deepagents-cli/          # CLI application
│   └── deepagents_cli/
│       ├── main.py          # CLI entry point
│       ├── agent.py         # create_agent_with_all_features()
│       ├── tools.py         # web_search, http_request, fetch_url
│       ├── skills/          # Skills middleware
│       ├── mcp/             # MCP config loading
│       └── hooks/           # Hooks config loading
└── harbor/                  # Sandbox management
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
    ├── SummarizationMiddleware
    └── AnthropicPromptCachingMiddleware
    ↓
LangGraph StateGraph
    ↓
LLM (Claude/GPT/etc)
    ↓
Tool Execution (via Backend)
    ↓
Response
```

---

## 12. Conclusão

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
- Documentação de migração Claude Code → DeepAgents

**Recomendação:**
Para usuários que precisam de flexibilidade de modelo ou integração com ecossistema LangChain, DeepAgents é uma excelente alternativa. Para usuários que precisam de funcionalidades avançadas como multimodal ou máxima integração com Claude, o Claude Code oficial continua sendo a escolha mais completa.

---

*Documento gerado em: 2025-12-05*
*Versão do DeepAgents analisada: commit ad6e116*
