# Plano de Implementação: UltrathinkMiddleware

> **Documento de Planejamento Técnico**
> **Projeto:** deepagents
> **Feature:** Extended Thinking (Ultrathink)
> **Data:** 2025-12-06
> **Status:** Planejado

---

## 1. Visão Geral

### 1.1 Objetivo

Implementar um middleware que habilita a funcionalidade de **Extended Thinking** do Claude, permitindo que o modelo realize raciocínio interno mais profundo antes de responder. Esta feature é especialmente útil para:

- Problemas matemáticos complexos
- Análise de código elaborada
- Planejamento de arquitetura
- Resolução de problemas multi-etapa

### 1.2 Referências

| Recurso | Link |
|---------|------|
| Documentação Anthropic | [Extended Thinking](https://platform.claude.com/docs/en/build-with-claude/extended-thinking) |
| LangChain Anthropic | [ChatAnthropic API](https://python.langchain.com/api_reference/anthropic/chat_models/langchain_anthropic.chat_models.ChatAnthropic.html) |
| Middleware de Referência | `libs/deepagents/deepagents/middleware/plan_mode.py` |

### 1.3 Modelos Suportados

- Claude Opus 4.5 (`claude-opus-4-5-20250929`)
- Claude Sonnet 4.5 (`claude-sonnet-4-5-20250929`)
- Claude Sonnet 4 (`claude-sonnet-4-20250514`)

---

## 2. Arquitetura

### 2.1 Diagrama de Fluxo

```
┌─────────────────┐
│   User Request  │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────┐
│                    Agent Pipeline                        │
│  ┌─────────────┐  ┌──────────────────┐  ┌────────────┐  │
│  │ Other       │  │ Ultrathink       │  │ Model      │  │
│  │ Middleware  │─▶│ Middleware       │─▶│ Invocation │  │
│  └─────────────┘  └────────┬─────────┘  └────────────┘  │
│                            │                             │
│                   ┌────────▼─────────┐                  │
│                   │ Check if enabled │                  │
│                   └────────┬─────────┘                  │
│                            │                             │
│              ┌─────────────┴─────────────┐              │
│              │                           │              │
│         ┌────▼────┐                 ┌────▼────┐        │
│         │ Enabled │                 │Disabled │        │
│         └────┬────┘                 └────┬────┘        │
│              │                           │              │
│    ┌─────────▼──────────┐               │              │
│    │ Override model     │               │              │
│    │ with thinking      │               │              │
│    │ parameters         │               │              │
│    └─────────┬──────────┘               │              │
│              │                           │              │
│              └───────────┬───────────────┘              │
│                          ▼                              │
│                 ┌────────────────┐                      │
│                 │ Call Handler   │                      │
│                 └────────────────┘                      │
└─────────────────────────────────────────────────────────┘
```

### 2.2 Componentes

```
libs/deepagents/deepagents/middleware/
├── __init__.py              # Adicionar export
├── ultrathink.py            # NOVO: Middleware principal
└── ...

libs/deepagents/tests/
├── unit_tests/
│   └── middleware/
│       └── test_ultrathink.py    # NOVO: Testes unitários
└── integration_tests/
    └── test_ultrathink.py        # NOVO: Testes de integração
```

---

## 3. Especificação Técnica

### 3.1 Classes e Interfaces

#### 3.1.1 UltrathinkState (TypedDict)

```python
class UltrathinkState(TypedDict, total=False):
    """Estado do middleware ultrathink."""
    ultrathink_enabled: bool      # Se o ultrathink está ativo
    budget_tokens: int            # Budget de tokens para thinking
    thinking_history: list[str]   # Histórico de thoughts (opcional)
```

#### 3.1.2 UltrathinkMiddleware (AgentMiddleware)

| Atributo | Tipo | Descrição |
|----------|------|-----------|
| `default_budget_tokens` | `int` | Budget padrão (mín: 1024) |
| `enabled_by_default` | `bool` | Habilitar automaticamente |
| `interleaved_thinking` | `bool` | Thinking entre tool calls |
| `_thinking_models` | `dict` | Cache de modelos configurados |

| Método | Descrição |
|--------|-----------|
| `__init__()` | Configuração inicial |
| `get_tools()` | Retorna ferramentas de controle |
| `wrap_model_call()` | Intercepta e modifica requests |
| `awrap_model_call()` | Versão assíncrona |
| `_get_thinking_model()` | Factory de modelos com thinking |

### 3.2 Ferramentas Expostas

#### enable_ultrathink

```python
def enable_ultrathink(
    budget_tokens: int = 10000,
    runtime: ToolRuntime = None,
) -> str:
    """
    Habilita extended thinking para tarefas de raciocínio complexo.

    Args:
        budget_tokens: Budget de tokens (mín: 1024, padrão: 10000)
        runtime: Runtime da ferramenta (automático)

    Returns:
        Mensagem de confirmação
    """
```

#### disable_ultrathink

```python
def disable_ultrathink(
    runtime: ToolRuntime = None,
) -> str:
    """
    Desabilita extended thinking.

    Args:
        runtime: Runtime da ferramenta (automático)

    Returns:
        Mensagem de confirmação
    """
```

### 3.3 Parâmetros da API Anthropic

```python
# Configuração básica
thinking = {
    "type": "enabled",
    "budget_tokens": 10000  # 1024 - 128000
}

# Para interleaved thinking (beta)
extra_headers = {
    "anthropic-beta": "interleaved-thinking-2025-05-14"
}
```

---

## 4. Implementação

### 4.1 Fase 1: Core Middleware

**Arquivo:** `libs/deepagents/deepagents/middleware/ultrathink.py`

```python
"""Ultrathink middleware for extended thinking capabilities."""
from __future__ import annotations

from typing import TYPE_CHECKING, Awaitable, Callable, Sequence, TypedDict

from langchain.agents.middleware.types import (
    AgentMiddleware,
    ModelRequest,
    ModelResponse,
)
from langchain_anthropic import ChatAnthropic
from langchain_core.tools import BaseTool, tool

if TYPE_CHECKING:
    from langchain.agents.middleware.types import ToolRuntime


# Constantes
MIN_BUDGET_TOKENS = 1024
DEFAULT_BUDGET_TOKENS = 10000
MAX_BUDGET_TOKENS = 128000
INTERLEAVED_THINKING_BETA = "interleaved-thinking-2025-05-14"


class UltrathinkState(TypedDict, total=False):
    """State for ultrathink middleware."""

    ultrathink_enabled: bool
    budget_tokens: int


class UltrathinkMiddlewareState(TypedDict, total=False):
    """Full middleware state schema."""

    ultrathink_enabled: bool
    budget_tokens: int


class UltrathinkMiddleware(AgentMiddleware):
    """Middleware for extended thinking capabilities.

    This middleware enables Claude's extended thinking feature, allowing
    the model to reason more deeply before responding. Extended thinking
    is particularly useful for:

    - Complex mathematical problems
    - Multi-step reasoning tasks
    - Code analysis and architecture planning
    - Difficult problem-solving scenarios

    The middleware can be configured to be always enabled, or controlled
    dynamically through tools that the agent can invoke.

    Example:
        ```python
        from deepagents.middleware.ultrathink import UltrathinkMiddleware
        from deepagents import create_deep_agent

        # Option 1: Always enabled
        agent = create_deep_agent(
            middleware=[UltrathinkMiddleware(
                budget_tokens=15000,
                enabled_by_default=True,
            )],
        )

        # Option 2: Dynamically controlled via tools
        agent = create_deep_agent(
            middleware=[UltrathinkMiddleware(budget_tokens=10000)],
        )
        # Agent will have access to: enable_ultrathink() and disable_ultrathink()
        ```

    Attributes:
        default_budget_tokens: Default token budget for thinking.
        enabled_by_default: Whether ultrathink is enabled by default.
        interleaved_thinking: Enable thinking between tool calls.

    Note:
        Extended thinking is only supported on Claude 4+ models.
        Using it with unsupported models will have no effect.
    """

    state_schema = UltrathinkMiddlewareState

    def __init__(
        self,
        budget_tokens: int = DEFAULT_BUDGET_TOKENS,
        enabled_by_default: bool = False,
        interleaved_thinking: bool = True,
    ) -> None:
        """Initialize ultrathink middleware.

        Args:
            budget_tokens: Token budget for thinking. Must be between 1024
                and 128000. Defaults to 10000.
            enabled_by_default: Whether ultrathink is enabled by default.
                If False, the agent can enable it via the enable_ultrathink tool.
            interleaved_thinking: Enable thinking between tool calls.
                This allows the model to reason about tool results before
                deciding on next actions. Requires beta header.
        """
        self.default_budget_tokens = max(
            MIN_BUDGET_TOKENS,
            min(budget_tokens, MAX_BUDGET_TOKENS),
        )
        self.enabled_by_default = enabled_by_default
        self.interleaved_thinking = interleaved_thinking
        self._tools: list[BaseTool] = []
        self._thinking_models: dict[str, ChatAnthropic] = {}

    def _get_thinking_model(
        self,
        base_model: ChatAnthropic,
        budget_tokens: int,
    ) -> ChatAnthropic:
        """Get or create a thinking-enabled model.

        This method caches models to avoid recreating them on every request.

        Args:
            base_model: The base ChatAnthropic model to enhance.
            budget_tokens: Token budget for thinking.

        Returns:
            A ChatAnthropic model configured with extended thinking.
        """
        # Normalize budget
        budget = max(MIN_BUDGET_TOKENS, min(budget_tokens, MAX_BUDGET_TOKENS))
        cache_key = f"{base_model.model_name}_{budget}_{self.interleaved_thinking}"

        if cache_key not in self._thinking_models:
            model_kwargs = {}

            if self.interleaved_thinking:
                model_kwargs["extra_headers"] = {
                    "anthropic-beta": INTERLEAVED_THINKING_BETA,
                }

            self._thinking_models[cache_key] = ChatAnthropic(
                model_name=base_model.model_name,
                max_tokens=base_model.max_tokens,
                thinking={"type": "enabled", "budget_tokens": budget},
                model_kwargs=model_kwargs if model_kwargs else None,
            )

        return self._thinking_models[cache_key]

    def _is_anthropic_model(self, model: object) -> bool:
        """Check if the model is an Anthropic model.

        Args:
            model: The model to check.

        Returns:
            True if the model is a ChatAnthropic instance.
        """
        return isinstance(model, ChatAnthropic)

    def get_tools(self) -> list[BaseTool]:
        """Get ultrathink control tools.

        Returns:
            List of tools for controlling ultrathink.
        """
        if self._tools:
            return self._tools

        @tool
        def enable_ultrathink(
            budget_tokens: int = DEFAULT_BUDGET_TOKENS,
            runtime: ToolRuntime[None, UltrathinkMiddlewareState] = None,
        ) -> str:
            """Enable extended thinking for complex reasoning tasks.

            Use this when you need to solve complex problems that require
            deep reasoning, such as:
            - Mathematical proofs or calculations
            - Complex code analysis
            - Multi-step logical reasoning
            - Architecture design decisions

            Args:
                budget_tokens: Token budget for thinking (1024-128000).
                    Higher values allow for more thorough reasoning but
                    increase latency and cost. Default: 10000.
                runtime: Tool runtime (automatically provided).

            Returns:
                Confirmation message with the configured budget.
            """
            budget = max(
                MIN_BUDGET_TOKENS,
                min(budget_tokens, MAX_BUDGET_TOKENS),
            )

            if runtime:
                runtime.state["ultrathink_enabled"] = True
                runtime.state["budget_tokens"] = budget

            return (
                f"Ultrathink enabled with {budget:,} token budget. "
                "I will now think more deeply before responding."
            )

        @tool
        def disable_ultrathink(
            runtime: ToolRuntime[None, UltrathinkMiddlewareState] = None,
        ) -> str:
            """Disable extended thinking.

            Use this when the task no longer requires deep reasoning,
            to improve response latency.

            Args:
                runtime: Tool runtime (automatically provided).

            Returns:
                Confirmation message.
            """
            if runtime:
                runtime.state["ultrathink_enabled"] = False

            return "Ultrathink disabled. Returning to normal response mode."

        self._tools = [enable_ultrathink, disable_ultrathink]
        return self._tools

    def wrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], ModelResponse],
    ) -> ModelResponse:
        """Enable extended thinking if active.

        This method intercepts model calls and, if ultrathink is enabled,
        replaces the model with a thinking-enabled version.

        Args:
            request: The model request being processed.
            handler: The handler function to call with the modified request.

        Returns:
            The model response from the handler.
        """
        runtime = request.runtime

        # Determine if ultrathink should be enabled
        is_enabled = self.enabled_by_default
        budget_tokens = self.default_budget_tokens

        if runtime and hasattr(runtime, "state"):
            is_enabled = runtime.state.get("ultrathink_enabled", is_enabled)
            budget_tokens = runtime.state.get("budget_tokens", budget_tokens)

        if is_enabled:
            current_model = request.model

            # Only apply to Anthropic models
            if self._is_anthropic_model(current_model):
                thinking_model = self._get_thinking_model(
                    current_model,
                    budget_tokens,
                )
                request = request.override(model=thinking_model)

        return handler(request)

    async def awrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], Awaitable[ModelResponse]],
    ) -> ModelResponse:
        """(async) Enable extended thinking if active.

        Async version of wrap_model_call.

        Args:
            request: The model request being processed.
            handler: The async handler function to call with the modified request.

        Returns:
            The model response from the handler.
        """
        runtime = request.runtime

        is_enabled = self.enabled_by_default
        budget_tokens = self.default_budget_tokens

        if runtime and hasattr(runtime, "state"):
            is_enabled = runtime.state.get("ultrathink_enabled", is_enabled)
            budget_tokens = runtime.state.get("budget_tokens", budget_tokens)

        if is_enabled:
            current_model = request.model

            if self._is_anthropic_model(current_model):
                thinking_model = self._get_thinking_model(
                    current_model,
                    budget_tokens,
                )
                request = request.override(model=thinking_model)

        return await handler(request)

    @property
    def tools(self) -> Sequence[BaseTool]:
        """Get middleware tools.

        Returns:
            Sequence of tools provided by this middleware.
        """
        return self.get_tools()
```

### 4.2 Fase 2: Exportar no __init__.py

**Arquivo:** `libs/deepagents/deepagents/middleware/__init__.py`

Adicionar ao arquivo existente:

```python
from deepagents.middleware.ultrathink import (
    UltrathinkMiddleware,
    UltrathinkState,
)

__all__ = [
    # ... exports existentes ...
    "UltrathinkMiddleware",
    "UltrathinkState",
]
```

### 4.3 Fase 3: Testes Unitários

**Arquivo:** `libs/deepagents/tests/unit_tests/middleware/test_ultrathink.py`

```python
"""Unit tests for UltrathinkMiddleware."""
from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from deepagents.middleware.ultrathink import (
    DEFAULT_BUDGET_TOKENS,
    MAX_BUDGET_TOKENS,
    MIN_BUDGET_TOKENS,
    UltrathinkMiddleware,
)


class TestUltrathinkMiddlewareInit:
    """Tests for UltrathinkMiddleware initialization."""

    def test_default_initialization(self):
        """Test middleware initializes with default values."""
        middleware = UltrathinkMiddleware()

        assert middleware.default_budget_tokens == DEFAULT_BUDGET_TOKENS
        assert middleware.enabled_by_default is False
        assert middleware.interleaved_thinking is True

    def test_custom_budget_tokens(self):
        """Test middleware accepts custom budget tokens."""
        middleware = UltrathinkMiddleware(budget_tokens=20000)

        assert middleware.default_budget_tokens == 20000

    def test_budget_tokens_minimum_enforced(self):
        """Test that budget tokens cannot be below minimum."""
        middleware = UltrathinkMiddleware(budget_tokens=500)

        assert middleware.default_budget_tokens == MIN_BUDGET_TOKENS

    def test_budget_tokens_maximum_enforced(self):
        """Test that budget tokens cannot exceed maximum."""
        middleware = UltrathinkMiddleware(budget_tokens=500000)

        assert middleware.default_budget_tokens == MAX_BUDGET_TOKENS

    def test_enabled_by_default(self):
        """Test middleware can be enabled by default."""
        middleware = UltrathinkMiddleware(enabled_by_default=True)

        assert middleware.enabled_by_default is True

    def test_interleaved_thinking_disabled(self):
        """Test interleaved thinking can be disabled."""
        middleware = UltrathinkMiddleware(interleaved_thinking=False)

        assert middleware.interleaved_thinking is False


class TestUltrathinkMiddlewareTools:
    """Tests for UltrathinkMiddleware tools."""

    def test_get_tools_returns_two_tools(self):
        """Test that get_tools returns enable and disable tools."""
        middleware = UltrathinkMiddleware()
        tools = middleware.get_tools()

        assert len(tools) == 2
        tool_names = [t.name for t in tools]
        assert "enable_ultrathink" in tool_names
        assert "disable_ultrathink" in tool_names

    def test_tools_are_cached(self):
        """Test that tools are cached after first call."""
        middleware = UltrathinkMiddleware()

        tools1 = middleware.get_tools()
        tools2 = middleware.get_tools()

        assert tools1 is tools2

    def test_tools_property(self):
        """Test tools property returns same as get_tools."""
        middleware = UltrathinkMiddleware()

        assert list(middleware.tools) == middleware.get_tools()


class TestUltrathinkMiddlewareEnableTool:
    """Tests for the enable_ultrathink tool."""

    def test_enable_sets_state(self):
        """Test enable_ultrathink sets correct state."""
        middleware = UltrathinkMiddleware()
        tools = middleware.get_tools()
        enable_tool = next(t for t in tools if t.name == "enable_ultrathink")

        # Create mock runtime
        runtime = MagicMock()
        runtime.state = {}

        result = enable_tool.invoke({"budget_tokens": 15000, "runtime": runtime})

        assert runtime.state["ultrathink_enabled"] is True
        assert runtime.state["budget_tokens"] == 15000
        assert "15,000" in result

    def test_enable_enforces_minimum_budget(self):
        """Test enable_ultrathink enforces minimum budget."""
        middleware = UltrathinkMiddleware()
        tools = middleware.get_tools()
        enable_tool = next(t for t in tools if t.name == "enable_ultrathink")

        runtime = MagicMock()
        runtime.state = {}

        enable_tool.invoke({"budget_tokens": 100, "runtime": runtime})

        assert runtime.state["budget_tokens"] == MIN_BUDGET_TOKENS


class TestUltrathinkMiddlewareDisableTool:
    """Tests for the disable_ultrathink tool."""

    def test_disable_sets_state(self):
        """Test disable_ultrathink sets correct state."""
        middleware = UltrathinkMiddleware()
        tools = middleware.get_tools()
        disable_tool = next(t for t in tools if t.name == "disable_ultrathink")

        runtime = MagicMock()
        runtime.state = {"ultrathink_enabled": True}

        result = disable_tool.invoke({"runtime": runtime})

        assert runtime.state["ultrathink_enabled"] is False
        assert "disabled" in result.lower()


class TestUltrathinkMiddlewareWrapModelCall:
    """Tests for wrap_model_call functionality."""

    @patch("deepagents.middleware.ultrathink.ChatAnthropic")
    def test_wrap_model_call_when_disabled(self, mock_anthropic):
        """Test wrap_model_call passes through when disabled."""
        middleware = UltrathinkMiddleware(enabled_by_default=False)

        request = MagicMock()
        request.runtime = MagicMock()
        request.runtime.state = {"ultrathink_enabled": False}
        handler = MagicMock()

        middleware.wrap_model_call(request, handler)

        # Handler should be called with original request
        handler.assert_called_once_with(request)
        request.override.assert_not_called()

    @patch("deepagents.middleware.ultrathink.ChatAnthropic")
    def test_wrap_model_call_when_enabled(self, mock_anthropic_class):
        """Test wrap_model_call modifies model when enabled."""
        from langchain_anthropic import ChatAnthropic

        middleware = UltrathinkMiddleware(enabled_by_default=False)

        # Create a real-ish mock model
        mock_model = MagicMock(spec=ChatAnthropic)
        mock_model.model_name = "claude-sonnet-4-5-20250929"
        mock_model.max_tokens = 16000

        request = MagicMock()
        request.runtime = MagicMock()
        request.runtime.state = {"ultrathink_enabled": True, "budget_tokens": 10000}
        request.model = mock_model

        modified_request = MagicMock()
        request.override.return_value = modified_request

        handler = MagicMock()

        with patch.object(middleware, "_is_anthropic_model", return_value=True):
            middleware.wrap_model_call(request, handler)

        # Handler should be called with modified request
        request.override.assert_called_once()
        handler.assert_called_once_with(modified_request)


class TestUltrathinkMiddlewareModelCache:
    """Tests for thinking model caching."""

    def test_models_are_cached(self):
        """Test that thinking models are cached."""
        middleware = UltrathinkMiddleware()

        mock_model = MagicMock()
        mock_model.model_name = "claude-sonnet-4-5-20250929"
        mock_model.max_tokens = 16000

        with patch("deepagents.middleware.ultrathink.ChatAnthropic") as mock_class:
            mock_class.return_value = MagicMock()

            model1 = middleware._get_thinking_model(mock_model, 10000)
            model2 = middleware._get_thinking_model(mock_model, 10000)

            # Should only create once
            assert mock_class.call_count == 1
            assert model1 is model2

    def test_different_budgets_different_models(self):
        """Test that different budgets create different cached models."""
        middleware = UltrathinkMiddleware()

        mock_model = MagicMock()
        mock_model.model_name = "claude-sonnet-4-5-20250929"
        mock_model.max_tokens = 16000

        with patch("deepagents.middleware.ultrathink.ChatAnthropic") as mock_class:
            mock_class.return_value = MagicMock()

            middleware._get_thinking_model(mock_model, 10000)
            middleware._get_thinking_model(mock_model, 20000)

            # Should create two different models
            assert mock_class.call_count == 2
```

### 4.4 Fase 4: Testes de Integração

**Arquivo:** `libs/deepagents/tests/integration_tests/test_ultrathink.py`

```python
"""Integration tests for UltrathinkMiddleware."""
from __future__ import annotations

import pytest
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage

from deepagents import create_deep_agent
from deepagents.middleware.ultrathink import UltrathinkMiddleware


@pytest.mark.requires("langchain_anthropic")
class TestUltrathinkMiddlewareIntegration:
    """Integration tests for UltrathinkMiddleware with real agents."""

    def test_agent_with_ultrathink_enabled_by_default(self):
        """Test agent with ultrathink always enabled."""
        agent = create_deep_agent(
            model=ChatAnthropic(model="claude-sonnet-4-20250514"),
            middleware=[
                UltrathinkMiddleware(
                    budget_tokens=5000,
                    enabled_by_default=True,
                ),
            ],
        )

        result = agent.invoke(
            {"messages": [HumanMessage(content="What is 17 * 23?")]}
        )

        # Should get a response
        assert result["messages"]
        last_message = result["messages"][-1]
        assert "391" in last_message.content

    def test_agent_can_enable_ultrathink_via_tool(self):
        """Test agent can enable ultrathink dynamically."""
        agent = create_deep_agent(
            model=ChatAnthropic(model="claude-sonnet-4-20250514"),
            middleware=[UltrathinkMiddleware(budget_tokens=5000)],
        )

        # First, enable ultrathink
        result = agent.invoke(
            {
                "messages": [
                    HumanMessage(
                        content="Enable ultrathink mode, then solve: What is the cube root of 27?"
                    )
                ]
            }
        )

        assert result["messages"]
        # Should have enabled and answered
        content = " ".join(m.content for m in result["messages"] if hasattr(m, "content"))
        assert "3" in content

    def test_agent_tools_include_ultrathink_controls(self):
        """Test agent has ultrathink control tools available."""
        middleware = UltrathinkMiddleware()
        tools = middleware.get_tools()

        tool_names = [t.name for t in tools]
        assert "enable_ultrathink" in tool_names
        assert "disable_ultrathink" in tool_names
```

---

## 5. Checklist de Implementação

### 5.1 Arquivos a Criar

- [ ] `libs/deepagents/deepagents/middleware/ultrathink.py`
- [ ] `libs/deepagents/tests/unit_tests/middleware/test_ultrathink.py`
- [ ] `libs/deepagents/tests/integration_tests/test_ultrathink.py`

### 5.2 Arquivos a Modificar

- [ ] `libs/deepagents/deepagents/middleware/__init__.py` - Adicionar exports
- [ ] `libs/deepagents/README.md` - Documentar nova feature (opcional)

### 5.3 Validação

- [ ] Testes unitários passando
- [ ] Testes de integração passando
- [ ] Linting sem erros (`make lint`)
- [ ] Type checking sem erros

---

## 6. Exemplos de Uso

### 6.1 Uso Básico - Sempre Habilitado

```python
from deepagents import create_deep_agent
from deepagents.middleware.ultrathink import UltrathinkMiddleware

agent = create_deep_agent(
    middleware=[
        UltrathinkMiddleware(
            budget_tokens=15000,
            enabled_by_default=True,
        ),
    ],
)

result = agent.invoke({
    "messages": [{"role": "user", "content": "Prove that there are infinitely many primes."}]
})
```

### 6.2 Uso Dinâmico - Controlado pelo Agente

```python
from deepagents import create_deep_agent
from deepagents.middleware.ultrathink import UltrathinkMiddleware

agent = create_deep_agent(
    middleware=[UltrathinkMiddleware(budget_tokens=10000)],
)

# O agente decide quando precisa de raciocínio profundo
result = agent.invoke({
    "messages": [{
        "role": "user",
        "content": "Analyze this complex algorithm and suggest optimizations..."
    }]
})
```

### 6.3 Configuração Avançada

```python
from deepagents import create_deep_agent
from deepagents.middleware.ultrathink import UltrathinkMiddleware
from deepagents.middleware.plan_mode import PlanModeMiddleware

# Combinando com outros middlewares
agent = create_deep_agent(
    middleware=[
        UltrathinkMiddleware(
            budget_tokens=20000,
            enabled_by_default=False,
            interleaved_thinking=True,  # Pensar entre tool calls
        ),
        PlanModeMiddleware(),
    ],
)
```

---

## 7. Considerações

### 7.1 Performance

| Budget Tokens | Latência Estimada | Uso Recomendado |
|---------------|-------------------|-----------------|
| 1,024 - 5,000 | +1-3s | Problemas simples |
| 5,000 - 15,000 | +3-10s | Análise moderada |
| 15,000 - 50,000 | +10-30s | Raciocínio complexo |
| 50,000+ | +30s+ | Problemas muito difíceis |

### 7.2 Custos

- Extended thinking consome tokens adicionais
- Os tokens de thinking são cobrados como tokens de output
- Recomenda-se habilitar apenas quando necessário

### 7.3 Limitações

- Apenas modelos Claude 4+ suportam extended thinking
- O thinking não é visível na resposta (apenas summary)
- Interleaved thinking é uma feature beta

---

## 8. Timeline Sugerido

| Fase | Descrição | Dependências |
|------|-----------|--------------|
| 1 | Implementar `ultrathink.py` | Nenhuma |
| 2 | Atualizar `__init__.py` | Fase 1 |
| 3 | Escrever testes unitários | Fase 1 |
| 4 | Escrever testes de integração | Fase 1 |
| 5 | Documentação no README | Fase 1-4 |

---

## 9. Aprovação

| Papel | Nome | Data | Status |
|-------|------|------|--------|
| Autor | Claude | 2025-12-06 | Pendente |
| Revisor | - | - | Pendente |
| Aprovador | - | - | Pendente |
