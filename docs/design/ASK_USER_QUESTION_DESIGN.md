# Design Doc: AskUserQuestion Tool

## Status: Draft
**Author:** Claude
**Created:** 2025-12-05
**Target Version:** deepagents v0.x.x

---

## 1. Overview

### 1.1 Problem Statement

Atualmente, o DeepAgents não possui uma forma estruturada para o agente fazer perguntas ao usuário durante a execução. Isso limita:

1. **Clarificação de requisitos** - O agente não pode pedir esclarecimentos
2. **Decisões de implementação** - Não há como apresentar opções ao usuário
3. **Validação interativa** - Impossível confirmar entendimento antes de agir
4. **UX de framework** - Desenvolvedores não podem criar agentes interativos

### 1.2 Solução Proposta

Implementar uma ferramenta `ask_user_question` que:
- Pausa a execução do agente
- Apresenta pergunta com opções estruturadas
- Coleta resposta do usuário
- Resume execução com a resposta

### 1.3 Referência: Claude Code

O Claude Code implementa `AskUserQuestion` com:
```typescript
AskUserQuestion({
    questions: [{
        question: "Which library should we use?",
        header: "Library",  // max 12 chars
        options: [
            { label: "React Query", description: "For data fetching" },
            { label: "SWR", description: "Lightweight alternative" }
        ],
        multiSelect: false
    }]
})
```

---

## 2. Design Detalhado

### 2.1 API da Ferramenta

```python
@tool
def ask_user_question(
    question: str,
    options: list[str] | None = None,
    *,
    header: str | None = None,
    descriptions: list[str] | None = None,
    multi_select: bool = False,
    allow_custom: bool = True,
    default: str | int | None = None,
    runtime: ToolRuntime = None,
) -> str | list[str]:
    """Ask the user a question and wait for their response.

    Use this tool when you need to:
    - Clarify ambiguous requirements
    - Present implementation choices
    - Confirm understanding before proceeding
    - Get user preferences or decisions

    Args:
        question: The question to ask the user. Should be clear and specific.
        options: Optional list of choices. If provided, user selects from these.
                 If None, user provides free-form text input.
        header: Short label for the question (max 12 chars). Used in compact display.
        descriptions: Optional descriptions for each option (same length as options).
        multi_select: If True, user can select multiple options. Default False.
        allow_custom: If True and options provided, user can enter custom text.
        default: Default option (index or text). Used if user presses Enter.
        runtime: Tool runtime (automatically provided).

    Returns:
        User's response. String for single-select, list[str] for multi-select.

    Examples:
        # Simple yes/no question
        answer = ask_user_question(
            question="Should I proceed with the refactoring?",
            options=["Yes", "No"],
        )

        # Multiple choice with descriptions
        choice = ask_user_question(
            question="Which authentication method?",
            header="Auth",
            options=["JWT", "Session", "OAuth2"],
            descriptions=[
                "Stateless tokens, good for APIs",
                "Server-side sessions, simpler setup",
                "Third-party providers like Google/GitHub"
            ],
        )

        # Free-form input
        name = ask_user_question(
            question="What should we name the new component?",
        )

        # Multi-select
        features = ask_user_question(
            question="Which features should we include?",
            options=["Dark mode", "Notifications", "Export", "Search"],
            multi_select=True,
        )
    """
```

### 2.2 Mecanismo de Interrupt

A ferramenta usa o mesmo mecanismo de interrupt do HITL existente:

```python
# No middleware, ao processar ask_user_question:
from langgraph.types import interrupt

def handle_ask_user_question(question: str, options: list[str] | None, ...):
    # Cria request de interrupt
    request = UserQuestionRequest(
        type="user_question",
        question=question,
        options=options,
        header=header,
        descriptions=descriptions,
        multi_select=multi_select,
        allow_custom=allow_custom,
        default=default,
    )

    # Pausa execução e aguarda resposta
    response = interrupt(request)

    # Retorna resposta do usuário para o agente
    return response
```

### 2.3 Renderização CLI

```
┌─────────────────────────────────────────────────────┐
│ ❓ Agent Question                                    │
│                                                     │
│ Which authentication method should we use?          │
│                                                     │
│ ☑ JWT         Stateless tokens, good for APIs      │
│ ☐ Session     Server-side sessions, simpler setup  │
│ ☐ OAuth2      Third-party providers                │
│ ☐ Other...    Enter custom response                │
└─────────────────────────────────────────────────────┘

Use ↑↓ to navigate, Enter to select, or type to filter
```

### 2.4 Integração com Middleware

```python
# libs/deepagents/deepagents/middleware/user_interaction.py

from dataclasses import dataclass
from langchain.agents.middleware import AgentMiddleware
from langchain_core.tools import tool, BaseTool
from langgraph.types import interrupt


@dataclass
class UserQuestionRequest:
    """Request payload for user question interrupt."""
    type: str = "user_question"
    question: str = ""
    options: list[str] | None = None
    header: str | None = None
    descriptions: list[str] | None = None
    multi_select: bool = False
    allow_custom: bool = True
    default: str | int | None = None


class UserInteractionMiddleware(AgentMiddleware):
    """Middleware for structured user interaction during agent execution.

    This middleware provides tools for the agent to ask questions,
    request confirmations, and gather user input in a structured way.

    Example:
        ```python
        from deepagents import create_deep_agent
        from deepagents.middleware.user_interaction import UserInteractionMiddleware

        agent = create_deep_agent(
            middleware=[UserInteractionMiddleware()],
        )
        ```
    """

    def __init__(self) -> None:
        self._tools: list[BaseTool] = []

    def get_tools(self) -> list[BaseTool]:
        """Get user interaction tools."""
        if self._tools:
            return self._tools

        @tool
        def ask_user_question(
            question: str,
            options: list[str] | None = None,
            header: str | None = None,
            descriptions: list[str] | None = None,
            multi_select: bool = False,
            allow_custom: bool = True,
            default: str | int | None = None,
        ) -> str | list[str]:
            """Ask the user a question and wait for their response.

            [... docstring from section 2.1 ...]
            """
            # Validate inputs
            if options and descriptions:
                if len(options) != len(descriptions):
                    raise ValueError("options and descriptions must have same length")

            if header and len(header) > 12:
                header = header[:12]

            # Create interrupt request
            request = UserQuestionRequest(
                question=question,
                options=options,
                header=header,
                descriptions=descriptions,
                multi_select=multi_select,
                allow_custom=allow_custom,
                default=default,
            )

            # Pause execution and wait for user response
            response = interrupt(request.__dict__)

            return response

        @tool
        def confirm_action(
            action: str,
            details: str | None = None,
            default: bool = True,
        ) -> bool:
            """Ask user to confirm before proceeding with an action.

            Use this for potentially destructive or significant operations
            where you want explicit user consent.

            Args:
                action: Brief description of what will happen
                details: Optional additional context
                default: Default response if user just presses Enter

            Returns:
                True if user confirms, False otherwise

            Example:
                if confirm_action(
                    action="Delete 15 test files",
                    details="Files matching *_test.py in /src/tests/"
                ):
                    # proceed with deletion
            """
            request = UserQuestionRequest(
                type="confirm_action",
                question=f"Confirm: {action}",
                options=["Yes, proceed", "No, cancel"],
                descriptions=[details, None] if details else None,
                default=0 if default else 1,
            )

            response = interrupt(request.__dict__)
            return response in ("Yes, proceed", "yes", "y", True)

        self._tools = [ask_user_question, confirm_action]
        return self._tools

    @property
    def tools(self) -> list[BaseTool]:
        return self.get_tools()
```

---

## 3. Implementação CLI

### 3.1 Handler de Interrupt

```python
# libs/deepagents-cli/deepagents_cli/execution.py

def prompt_for_user_question(request: dict) -> str | list[str]:
    """Prompt user to answer a question with optional choices.

    Args:
        request: UserQuestionRequest as dict

    Returns:
        User's response (string or list for multi-select)
    """
    question = request.get("question", "")
    options = request.get("options")
    header = request.get("header")
    descriptions = request.get("descriptions")
    multi_select = request.get("multi_select", False)
    allow_custom = request.get("allow_custom", True)
    default = request.get("default")

    # Build panel content
    content_lines = [f"[bold]{question}[/bold]"]

    if header:
        title = f"❓ {header}"
    else:
        title = "❓ Agent Question"

    console.print(
        Panel(
            "\n".join(content_lines),
            title=title,
            border_style="blue",
            box=box.ROUNDED,
            padding=(0, 1),
        )
    )

    if options:
        return _select_from_options(
            options=options,
            descriptions=descriptions,
            multi_select=multi_select,
            allow_custom=allow_custom,
            default=default,
        )
    else:
        return _get_text_input(default=default)


def _select_from_options(
    options: list[str],
    descriptions: list[str] | None = None,
    multi_select: bool = False,
    allow_custom: bool = True,
    default: str | int | None = None,
) -> str | list[str]:
    """Interactive option selection with arrow keys."""

    # Add "Other..." option if custom allowed
    display_options = list(options)
    display_descriptions = list(descriptions) if descriptions else [None] * len(options)

    if allow_custom:
        display_options.append("Other...")
        display_descriptions.append("Enter custom response")

    selected = set() if multi_select else None
    cursor = 0

    # Set default cursor position
    if isinstance(default, int) and 0 <= default < len(display_options):
        cursor = default
    elif isinstance(default, str) and default in display_options:
        cursor = display_options.index(default)

    try:
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)

        try:
            tty.setraw(fd)
            sys.stdout.write("\033[?25l")  # Hide cursor
            sys.stdout.flush()

            first_render = True

            while True:
                if not first_render:
                    # Move cursor back
                    sys.stdout.write(f"\033[{len(display_options)}A\r")

                first_render = False

                # Render options
                for i, opt in enumerate(display_options):
                    sys.stdout.write("\r\033[K")  # Clear line

                    desc = display_descriptions[i] if display_descriptions else None

                    if multi_select:
                        # Multi-select: show checkbox state
                        is_selected = i in selected
                        checkbox = "☑" if is_selected else "☐"
                        highlight = i == cursor

                        if highlight:
                            style = "\033[1;34m"  # Bold blue
                        elif is_selected:
                            style = "\033[32m"  # Green
                        else:
                            style = "\033[2m"  # Dim

                        line = f"{style}{checkbox} {opt}"
                        if desc:
                            line += f"  \033[2m{desc}\033[0m"
                        else:
                            line += "\033[0m"
                    else:
                        # Single select: radio button style
                        is_cursor = i == cursor
                        radio = "●" if is_cursor else "○"

                        if is_cursor:
                            style = "\033[1;34m"  # Bold blue
                        else:
                            style = "\033[2m"  # Dim

                        line = f"{style}{radio} {opt}"
                        if desc:
                            line += f"  \033[2m{desc}\033[0m"
                        else:
                            line += "\033[0m"

                    sys.stdout.write(line + "\n")

                sys.stdout.flush()

                # Read key
                char = sys.stdin.read(1)

                if char == "\x1b":  # ESC sequence
                    next1 = sys.stdin.read(1)
                    next2 = sys.stdin.read(1)
                    if next1 == "[":
                        if next2 == "B":  # Down
                            cursor = (cursor + 1) % len(display_options)
                        elif next2 == "A":  # Up
                            cursor = (cursor - 1) % len(display_options)

                elif char == " " and multi_select:
                    # Toggle selection in multi-select mode
                    if cursor in selected:
                        selected.remove(cursor)
                    else:
                        selected.add(cursor)

                elif char in {"\r", "\n"}:  # Enter
                    sys.stdout.write("\r\n")
                    break

                elif char == "\x03":  # Ctrl+C
                    sys.stdout.write("\r\n")
                    raise KeyboardInterrupt

        finally:
            sys.stdout.write("\033[?25h")  # Show cursor
            sys.stdout.flush()
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

    except (termios.error, AttributeError):
        # Fallback for non-Unix
        return _fallback_select(display_options, multi_select, default)

    # Handle "Other..." selection
    other_index = len(options)  # Index of "Other..." if added

    if multi_select:
        if other_index in selected and allow_custom:
            selected.remove(other_index)
            custom = input("Enter custom response: ").strip()
            if custom:
                return [display_options[i] for i in selected] + [custom]
        return [display_options[i] for i in selected]
    else:
        if cursor == other_index and allow_custom:
            return input("Enter custom response: ").strip()
        return display_options[cursor]


def _get_text_input(default: str | None = None) -> str:
    """Get free-form text input from user."""
    prompt = "> "
    if default:
        prompt = f"> [{default}] "

    response = input(prompt).strip()
    return response if response else (default or "")


def _fallback_select(
    options: list[str],
    multi_select: bool,
    default: str | int | None,
) -> str | list[str]:
    """Fallback selection for non-Unix systems."""
    print("\nOptions:")
    for i, opt in enumerate(options):
        marker = f"[{i+1}]"
        print(f"  {marker} {opt}")

    if multi_select:
        print("\nEnter numbers separated by comma (e.g., 1,3):")
        response = input("> ").strip()
        indices = [int(x.strip()) - 1 for x in response.split(",") if x.strip().isdigit()]
        return [options[i] for i in indices if 0 <= i < len(options)]
    else:
        print(f"\nEnter number (default: {default or 1}):")
        response = input("> ").strip()
        if response.isdigit():
            idx = int(response) - 1
            if 0 <= idx < len(options):
                return options[idx]
        return options[default if isinstance(default, int) else 0]
```

### 3.2 Integração no Loop Principal

```python
# Em execute_task(), adicionar handling para user_question:

# Dentro do loop de processamento de interrupts:
if current_stream_mode == "updates":
    if "__interrupt__" in data:
        interrupts = data["__interrupt__"]
        for interrupt_obj in interrupts:
            request = interrupt_obj.value

            # Detectar tipo de interrupt
            if request.get("type") == "user_question":
                # Pausar spinner
                if spinner_active:
                    status.stop()
                    spinner_active = False

                # Coletar resposta
                response = prompt_for_user_question(request)

                # Preparar resposta para resumir
                hitl_response[interrupt_obj.id] = {
                    "type": "user_response",
                    "response": response,
                }

                interrupt_occurred = True

            elif request.get("type") == "confirm_action":
                # Similar handling para confirmações
                ...

            else:
                # HITL padrão (tool approval)
                ...
```

---

## 4. System Prompt Addition

```python
USER_INTERACTION_SYSTEM_PROMPT = """## User Interaction Tools

You have access to tools for gathering user input during task execution:

### ask_user_question
Use this tool to ask the user questions when you need:
- Clarification on ambiguous requirements
- User preference between multiple valid approaches
- Confirmation before significant changes
- Custom input (names, values, etc.)

**When to use:**
- Before making architectural decisions
- When requirements are unclear
- When there are trade-offs the user should decide
- Before destructive operations

**When NOT to use:**
- For questions you can reasonably infer the answer to
- For trivial decisions that don't affect the outcome
- Repeatedly for the same type of question
- When the user has already expressed a clear preference

### confirm_action
Use this for explicit confirmation before:
- Deleting files or data
- Making breaking changes
- Operations that are hard to undo
- Actions affecting production systems

Example usage:
```
# Ask for preference
method = ask_user_question(
    question="Which state management approach?",
    options=["Redux", "Zustand", "Context API"],
    descriptions=["Full-featured, more boilerplate", "Minimal, hooks-based", "Built-in, simpler"],
)

# Confirm destructive action
if confirm_action("Delete 23 unused test files"):
    # proceed
```
"""
```

---

## 5. Testes

### 5.1 Unit Tests

```python
# libs/deepagents/tests/middleware/test_user_interaction.py

import pytest
from deepagents.middleware.user_interaction import (
    UserInteractionMiddleware,
    UserQuestionRequest,
)


class TestUserInteractionMiddleware:
    """Tests for UserInteractionMiddleware."""

    def test_middleware_provides_tools(self):
        """Middleware should provide ask_user_question and confirm_action tools."""
        middleware = UserInteractionMiddleware()
        tools = middleware.get_tools()

        tool_names = [t.name for t in tools]
        assert "ask_user_question" in tool_names
        assert "confirm_action" in tool_names

    def test_ask_user_question_validates_options_descriptions(self):
        """Should raise error if options and descriptions length mismatch."""
        middleware = UserInteractionMiddleware()
        ask_tool = next(t for t in middleware.get_tools() if t.name == "ask_user_question")

        with pytest.raises(ValueError, match="same length"):
            ask_tool.invoke({
                "question": "Test?",
                "options": ["A", "B"],
                "descriptions": ["Only one"],
            })

    def test_header_truncation(self):
        """Header should be truncated to 12 characters."""
        # Implementation detail - verify in integration test
        pass


class TestUserQuestionRequest:
    """Tests for UserQuestionRequest dataclass."""

    def test_default_values(self):
        """Request should have sensible defaults."""
        request = UserQuestionRequest()

        assert request.type == "user_question"
        assert request.multi_select is False
        assert request.allow_custom is True

    def test_serialization(self):
        """Request should serialize to dict for interrupt."""
        request = UserQuestionRequest(
            question="Test?",
            options=["A", "B"],
        )

        data = request.__dict__
        assert data["question"] == "Test?"
        assert data["options"] == ["A", "B"]
```

### 5.2 Integration Tests

```python
# libs/deepagents-cli/tests/integration_tests/test_user_interaction.py

import pytest
from unittest.mock import patch, MagicMock
from deepagents_cli.execution import prompt_for_user_question


class TestPromptForUserQuestion:
    """Integration tests for user question prompting."""

    def test_single_select_basic(self):
        """Test basic single-select question."""
        request = {
            "type": "user_question",
            "question": "Which option?",
            "options": ["A", "B", "C"],
        }

        # Mock terminal input to select first option
        with patch("sys.stdin") as mock_stdin:
            mock_stdin.read.side_effect = ["\r"]  # Just press Enter
            mock_stdin.fileno.return_value = 0

            with patch("termios.tcgetattr"), patch("termios.tcsetattr"), patch("tty.setraw"):
                result = prompt_for_user_question(request)

        assert result == "A"

    def test_multi_select(self):
        """Test multi-select question."""
        request = {
            "type": "user_question",
            "question": "Which options?",
            "options": ["A", "B", "C"],
            "multi_select": True,
        }

        # Mock selecting A and C
        with patch("sys.stdin") as mock_stdin:
            mock_stdin.read.side_effect = [
                " ",           # Toggle A
                "\x1b", "[", "B",  # Down arrow
                "\x1b", "[", "B",  # Down arrow
                " ",           # Toggle C
                "\r",          # Enter
            ]
            mock_stdin.fileno.return_value = 0

            with patch("termios.tcgetattr"), patch("termios.tcsetattr"), patch("tty.setraw"):
                result = prompt_for_user_question(request)

        assert set(result) == {"A", "C"}

    def test_free_form_input(self):
        """Test free-form text input without options."""
        request = {
            "type": "user_question",
            "question": "What name?",
        }

        with patch("builtins.input", return_value="MyComponent"):
            result = prompt_for_user_question(request)

        assert result == "MyComponent"

    def test_custom_option(self):
        """Test selecting 'Other...' and entering custom text."""
        request = {
            "type": "user_question",
            "question": "Which option?",
            "options": ["A", "B"],
            "allow_custom": True,
        }

        # Navigate to "Other..." and select
        with patch("sys.stdin") as mock_stdin:
            mock_stdin.read.side_effect = [
                "\x1b", "[", "B",  # Down to B
                "\x1b", "[", "B",  # Down to Other...
                "\r",             # Enter
            ]
            mock_stdin.fileno.return_value = 0

            with patch("termios.tcgetattr"), patch("termios.tcsetattr"), patch("tty.setraw"):
                with patch("builtins.input", return_value="Custom"):
                    result = prompt_for_user_question(request)

        assert result == "Custom"
```

---

## 6. Migração e Compatibilidade

### 6.1 Backward Compatibility

- Middleware é **opt-in** - não afeta agentes existentes
- Não há breaking changes na API existente
- Ferramentas existentes continuam funcionando

### 6.2 Ativação

```python
# Opção 1: Adicionar ao create_deep_agent (recomendado para v1.0)
agent = create_deep_agent(
    enable_user_interaction=True,  # Nova flag
)

# Opção 2: Middleware explícito
from deepagents.middleware.user_interaction import UserInteractionMiddleware

agent = create_deep_agent(
    middleware=[UserInteractionMiddleware()],
)

# Opção 3: Incluir por padrão no create_agent_with_all_features
agent = await create_agent_with_all_features(
    ...,
    enable_user_interaction=True,  # Default True
)
```

---

## 7. Cronograma de Implementação

| Fase | Tarefas | Estimativa |
|------|---------|------------|
| 1 | Criar `UserInteractionMiddleware` base | 2-3h |
| 2 | Implementar `ask_user_question` tool | 2-3h |
| 3 | Implementar handler CLI (`prompt_for_user_question`) | 3-4h |
| 4 | Integrar no loop de execução | 2-3h |
| 5 | Adicionar `confirm_action` | 1-2h |
| 6 | Testes unitários e integração | 3-4h |
| 7 | Documentação e exemplos | 2-3h |
| **Total** | | **15-22h** |

---

## 8. Decisões de Design

### 8.1 Por que usar Interrupt vs Callback?

**Escolha:** Interrupt (LangGraph)

**Justificativa:**
- Consistente com HITL existente
- Suporta checkpointing automático
- Funciona com streaming
- Não requer mudanças no grafo

### 8.2 Por que Middleware vs Tool Direta?

**Escolha:** Middleware

**Justificativa:**
- Pode injetar system prompt
- Pode filtrar/modificar ferramentas por contexto
- Extensível para futuros tipos de interação
- Padrão estabelecido no DeepAgents

### 8.3 Por que não usar prompt_toolkit?

**Escolha:** ANSI direto + fallback

**Justificativa:**
- Já usado no tool approval existente
- Menor overhead
- Consistência visual com resto da CLI
- prompt_toolkit pode ser adicionado depois

---

## 9. Riscos e Mitigações

| Risco | Probabilidade | Impacto | Mitigação |
|-------|---------------|---------|-----------|
| Agente usa excessivamente | Média | Médio | Documentar boas práticas no prompt |
| Loops infinitos de perguntas | Baixa | Alto | Limitar perguntas por turno |
| Incompatibilidade de terminal | Baixa | Médio | Fallback para input básico |
| Conflito com auto-approve | Média | Baixo | Sempre pausar para perguntas |

---

## 10. Métricas de Sucesso

- [ ] Tool funciona end-to-end em teste manual
- [ ] 100% cobertura de testes unitários
- [ ] Documentação no README atualizada
- [ ] Exemplo no quickstarts repo
- [ ] Nenhuma regressão em testes existentes

---

## Appendix A: Exemplos de Uso

### A.1 Agente de Refactoring

```python
# O agente pode perguntar antes de grandes mudanças
answer = ask_user_question(
    question="Found 15 files with deprecated API usage. How should I proceed?",
    options=[
        "Update all files automatically",
        "Show me each change for approval",
        "Create a migration plan first",
        "Skip for now"
    ],
    descriptions=[
        "Fast but may need review after",
        "Slower but more control",
        "Document changes before making them",
        "I'll handle this manually later"
    ],
)
```

### A.2 Agente de Setup de Projeto

```python
# Coletar preferências de setup
db = ask_user_question(
    question="Which database?",
    header="Database",
    options=["PostgreSQL", "MySQL", "SQLite", "MongoDB"],
)

auth = ask_user_question(
    question="Authentication method?",
    header="Auth",
    options=["JWT", "Session", "OAuth2", "None"],
)

features = ask_user_question(
    question="Which features to include?",
    options=["API docs", "Testing", "Docker", "CI/CD"],
    multi_select=True,
)
```

### A.3 Agente de Code Review

```python
# Confirmar antes de aplicar fixes
if confirm_action(
    action="Apply 8 auto-fixes for linting errors",
    details="3 import sorting, 2 unused imports, 3 formatting issues"
):
    # aplicar fixes
else:
    # mostrar diff e perguntar individualmente
```
