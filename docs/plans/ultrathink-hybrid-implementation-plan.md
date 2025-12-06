# Plano de Implementação: UltrathinkMiddleware Híbrido

## Objetivo

Evoluir o `UltrathinkMiddleware` para funcionar com **qualquer modelo LLM**, não apenas Claude. Quando o modelo suportar extended thinking nativo (Claude 4+), usar a API da Anthropic. Caso contrário, fornecer um fallback inteligente com tool de reasoning + instruções no prompt.

---

## Arquitetura Proposta

```
┌─────────────────────────────────────────────────────────────┐
│                   UltrathinkMiddleware                      │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Inicialização:                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ • budget_tokens: int (1024-128000)                  │   │
│  │ • enabled_by_default: bool                          │   │
│  │ • interleaved_thinking: bool                        │   │
│  │ • fallback_mode: "tool" | "prompt" | "both"  [NEW]  │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  Runtime:                                                   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                                                     │   │
│  │  É modelo Claude 4+?                                │   │
│  │       │                                             │   │
│  │       ├── SIM ──► Extended Thinking nativo          │   │
│  │       │           • thinking={"type": "enabled"}    │   │
│  │       │           • Tools: enable/disable           │   │
│  │       │                                             │   │
│  │       └── NÃO ──► Fallback Mode                     │   │
│  │                   • Tool: think_step_by_step        │   │
│  │                   • Prompt: instruções de reasoning │   │
│  │                   • Tools: enable/disable           │   │
│  │                                                     │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Componentes a Implementar

### 1. Nova Tool: `think_step_by_step`

**Arquivo**: `libs/deepagents/deepagents/middleware/ultrathink.py`

```python
@tool
def think_step_by_step(
    problem: str,
    reasoning_steps: list[str],
    conclusion: str,
) -> str:
    """Think through a complex problem step by step before taking action.

    Use this tool when facing:
    - Complex mathematical problems
    - Multi-step logical reasoning
    - Code analysis and debugging
    - Architecture decisions
    - Any task requiring careful thought

    Args:
        problem: Clear statement of the problem to solve
        reasoning_steps: List of reasoning steps, each building on the previous
        conclusion: Final conclusion based on the reasoning

    Returns:
        Confirmation with summary of the reasoning process
    """
    steps_summary = "\n".join(f"  {i+1}. {step}" for i, step in enumerate(reasoning_steps))
    return f"""Reasoning complete:

Problem: {problem}

Steps:
{steps_summary}

Conclusion: {conclusion}

You may now proceed with actions based on this reasoning."""
```

**Propósito**: Forçar o modelo a estruturar seu pensamento antes de agir.

### 2. System Prompt Addition

**Método**: `get_system_prompt_addition()`

```python
def get_system_prompt_addition(self) -> str:
    """Add thinking instructions for non-Claude models."""
    if self._requires_fallback():
        return """
## Extended Thinking Mode

You have access to the `think_step_by_step` tool for complex reasoning tasks.

**When to use it:**
- Mathematical problems or calculations
- Multi-step logical reasoning
- Code analysis, debugging, or architecture decisions
- Any task where careful thought leads to better results

**How to use it:**
1. State the problem clearly
2. Break down your reasoning into steps
3. Reach a conclusion
4. Then proceed with actions

This structured thinking helps ensure accurate and well-reasoned responses.
"""
    return ""
```

### 3. Detecção de Modelo

**Método**: `_requires_fallback()`

```python
def _requires_fallback(self, model: object = None) -> bool:
    """Check if fallback mode is needed for the given model."""
    if model is None:
        # Durante inicialização, assumir que pode precisar
        return True

    # Claude 4+ suporta extended thinking nativo
    if isinstance(model, ChatAnthropic):
        model_name = getattr(model, 'model_name', '') or ''
        # Modelos que suportam extended thinking
        supported = ['claude-4', 'claude-opus-4', 'claude-sonnet-4', 'claude-haiku-4']
        return not any(s in model_name.lower() for s in supported)

    # Outros modelos precisam de fallback
    return True
```

### 4. Tools Dinâmicas

**Método**: `get_tools()`

```python
def get_tools(self) -> list[BaseTool]:
    """Get tools based on model capabilities."""
    tools = []

    # Tools de controle (sempre disponíveis)
    tools.extend([self._enable_tool, self._disable_tool])

    # Tool de fallback (para modelos não-Claude)
    if self._requires_fallback():
        tools.append(self._think_step_by_step_tool)

    return tools
```

### 5. Novo Parâmetro: `fallback_mode`

```python
def __init__(
    self,
    budget_tokens: int = DEFAULT_BUDGET_TOKENS,
    enabled_by_default: bool = False,
    interleaved_thinking: bool = True,
    fallback_mode: Literal["tool", "prompt", "both"] = "both",  # NOVO
) -> None:
    """Initialize ultrathink middleware.

    Args:
        budget_tokens: Token budget for native thinking (Claude only)
        enabled_by_default: Whether thinking is enabled by default
        interleaved_thinking: Enable thinking between tool calls (Claude only)
        fallback_mode: For non-Claude models:
            - "tool": Only provide think_step_by_step tool
            - "prompt": Only add thinking instructions to prompt
            - "both": Provide both tool and prompt instructions (recommended)
    """
```

---

## Mudanças nos Arquivos

### Arquivo 1: `ultrathink.py`

| Seção | Mudança |
|-------|---------|
| Imports | Adicionar `Literal` do typing |
| `__init__` | Novo parâmetro `fallback_mode` |
| `_requires_fallback()` | Novo método para detectar necessidade de fallback |
| `_create_think_tool()` | Novo método privado para criar a tool |
| `get_tools()` | Retornar tools condicionalmente |
| `get_system_prompt_addition()` | Novo método para instruções de prompt |
| Docstrings | Atualizar documentação |

### Arquivo 2: `__init__.py` (middleware)

Nenhuma mudança necessária - exports já existem.

### Arquivo 3: Testes unitários

| Teste | Descrição |
|-------|-----------|
| `test_fallback_detection_anthropic` | Verifica que Claude 4+ não usa fallback |
| `test_fallback_detection_other_models` | Verifica que outros modelos usam fallback |
| `test_think_tool_available_for_fallback` | Tool think disponível para não-Claude |
| `test_think_tool_not_available_for_claude` | Tool think não disponível para Claude |
| `test_system_prompt_addition_fallback` | Prompt adicionado para fallback |
| `test_system_prompt_addition_claude` | Sem prompt extra para Claude |
| `test_fallback_mode_tool_only` | Modo "tool" só adiciona tool |
| `test_fallback_mode_prompt_only` | Modo "prompt" só adiciona prompt |
| `test_fallback_mode_both` | Modo "both" adiciona ambos |

### Arquivo 4: Testes de integração

| Teste | Descrição |
|-------|-----------|
| `test_middleware_with_openai_model` | Funciona com GPT-4 |
| `test_middleware_with_xai_model` | Funciona com Grok |
| `test_think_tool_execution` | Tool executa corretamente |

---

## Fluxo de Execução

### Cenário 1: Claude 4+ com `--ultrathink`

```
1. CLI passa --ultrathink
2. UltrathinkMiddleware criado com enabled_by_default=True
3. _requires_fallback() retorna False (é Claude)
4. get_tools() retorna [enable_ultrathink, disable_ultrathink]
5. wrap_model_call() aplica thinking={"type": "enabled"}
6. Modelo usa extended thinking nativo
```

### Cenário 2: GPT-4/Grok com `--ultrathink`

```
1. CLI passa --ultrathink
2. UltrathinkMiddleware criado com enabled_by_default=True
3. _requires_fallback() retorna True (não é Claude)
4. get_tools() retorna [enable_ultrathink, disable_ultrathink, think_step_by_step]
5. get_system_prompt_addition() retorna instruções de thinking
6. wrap_model_call() não modifica o modelo (não suporta)
7. Modelo usa tool think_step_by_step quando necessário
```

---

## Interface de Uso

### CLI (sem mudanças)

```bash
# Funciona igual para qualquer modelo
deepagents --ultrathink --ultrathink-budget 15000
```

### Código Python

```python
from deepagents.middleware import UltrathinkMiddleware

# Modo padrão (recomendado)
middleware = UltrathinkMiddleware(
    budget_tokens=15000,
    enabled_by_default=True,
)

# Só tool (sem modificar prompt)
middleware = UltrathinkMiddleware(
    fallback_mode="tool",
)

# Só prompt (sem tool extra)
middleware = UltrathinkMiddleware(
    fallback_mode="prompt",
)
```

---

## Compatibilidade

| Aspecto | Status |
|---------|--------|
| API existente | ✅ Mantida (retrocompatível) |
| Testes existentes | ✅ Continuam passando |
| CLI flags | ✅ Sem mudanças |
| Comportamento Claude | ✅ Idêntico ao atual |

---

## Estimativa de Implementação

| Tarefa | Complexidade |
|--------|--------------|
| Implementar `_requires_fallback()` | Baixa |
| Criar tool `think_step_by_step` | Baixa |
| Implementar `get_system_prompt_addition()` | Baixa |
| Modificar `get_tools()` | Baixa |
| Adicionar parâmetro `fallback_mode` | Baixa |
| Testes unitários (9 novos) | Média |
| Testes de integração (3 novos) | Média |
| Documentação | Baixa |

**Total estimado**: ~12 novos testes, ~100 linhas de código novo

---

## Riscos e Mitigações

| Risco | Mitigação |
|-------|-----------|
| Tool não usada pelo modelo | Instruções claras no prompt |
| Overhead de tokens no prompt | Modo "tool" disponível |
| Detecção incorreta de modelo | Fallback conservador (assume não-Claude) |

---

## Próximos Passos (após aprovação)

1. Implementar mudanças em `ultrathink.py`
2. Adicionar testes unitários
3. Adicionar testes de integração
4. Testar com modelo xAI/Grok disponível
5. Atualizar documentação

---

*Plano criado em: 2025-12-06*
