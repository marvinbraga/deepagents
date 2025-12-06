"""Ultrathink middleware for extended thinking capabilities.

This module provides middleware that enables extended thinking features,
allowing the model to reason more deeply before responding. Extended thinking
is particularly useful for complex mathematical problems, multi-step reasoning,
code analysis, and architecture planning.

For Claude 4+ models, this uses the native extended thinking API.
For other models (OpenAI, xAI, Google, etc.), it provides a fallback
mechanism using a structured thinking tool and prompt instructions.

Example:
    Basic usage with always-enabled thinking::

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

    Dynamic control via agent tools::

        agent = create_deep_agent(
            middleware=[UltrathinkMiddleware(budget_tokens=10000)],
        )
        # Agent will have access to: enable_ultrathink() and disable_ultrathink()
        # For non-Claude models, also: think_step_by_step()

Note:
    Native extended thinking is only supported on Claude 4+ models
    (Opus 4.5, Sonnet 4.5, Sonnet 4, Haiku 4.5). For other models,
    a fallback mechanism with structured thinking tools is used.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Awaitable, Callable, Literal, Sequence, TypedDict

from langchain.agents.middleware.types import (
    AgentMiddleware,
    ModelRequest,
    ModelResponse,
)
from langchain.tools import ToolRuntime
from langchain_anthropic import ChatAnthropic
from langchain_core.tools import BaseTool, tool

from deepagents.middleware.ultrathink_logging import (
    log_middleware_init,
    log_model_detection,
    log_state_change,
    log_think_tool_call,
    log_thinking_enabled,
    log_tool_creation,
)

if TYPE_CHECKING:
    pass


# Constants
MIN_BUDGET_TOKENS = 1024
"""Minimum token budget for extended thinking."""

DEFAULT_BUDGET_TOKENS = 10000
"""Default token budget for extended thinking."""

MAX_BUDGET_TOKENS = 128000
"""Maximum token budget for extended thinking."""

INTERLEAVED_THINKING_BETA = "interleaved-thinking-2025-05-14"
"""Beta header for interleaved thinking support."""

# Claude 4+ model prefixes that support native extended thinking
EXTENDED_THINKING_MODELS = (
    "claude-4",
    "claude-opus-4",
    "claude-sonnet-4",
    "claude-haiku-4",
)
"""Model prefixes that support native extended thinking."""


class UltrathinkState(TypedDict, total=False):
    """State for ultrathink middleware.

    Attributes:
        ultrathink_enabled: Whether extended thinking is currently enabled.
        budget_tokens: Current token budget for thinking.
    """

    ultrathink_enabled: bool
    budget_tokens: int


class UltrathinkMiddlewareState(TypedDict, total=False):
    """Full middleware state schema for UltrathinkMiddleware.

    This is used as the state_schema for the middleware to ensure
    proper state management within the agent runtime.

    Attributes:
        ultrathink_enabled: Whether extended thinking is currently enabled.
        budget_tokens: Current token budget for thinking.
    """

    ultrathink_enabled: bool
    budget_tokens: int


class UltrathinkMiddleware(AgentMiddleware):
    """Middleware for extended thinking capabilities.

    This middleware enables extended thinking features, allowing the model
    to reason more deeply before responding. Extended thinking is
    particularly useful for:

    - Complex mathematical problems and proofs
    - Multi-step reasoning tasks
    - Code analysis and architecture planning
    - Difficult problem-solving scenarios

    For Claude 4+ models, this uses the native extended thinking API.
    For other models, it provides a fallback mechanism with:
    - A `think_step_by_step` tool for structured reasoning
    - System prompt additions with thinking instructions

    The middleware can be configured to be always enabled, or controlled
    dynamically through tools that the agent can invoke.

    Attributes:
        default_budget_tokens: Default token budget for thinking.
        enabled_by_default: Whether ultrathink is enabled by default.
        interleaved_thinking: Enable thinking between tool calls.
        fallback_mode: Mode for non-Claude models ("tool", "prompt", "both").

    Example:
        Always enabled with custom budget::

            from deepagents.middleware.ultrathink import UltrathinkMiddleware
            from deepagents import create_deep_agent

            agent = create_deep_agent(
                middleware=[
                    UltrathinkMiddleware(
                        budget_tokens=15000,
                        enabled_by_default=True,
                    ),
                ],
            )

        Dynamically controlled via tools::

            agent = create_deep_agent(
                middleware=[UltrathinkMiddleware(budget_tokens=10000)],
            )
            # Agent will have access to: enable_ultrathink() and disable_ultrathink()

        Fallback mode for non-Claude models::

            agent = create_deep_agent(
                middleware=[
                    UltrathinkMiddleware(
                        fallback_mode="both",  # tool + prompt instructions
                    ),
                ],
            )

    Note:
        Native extended thinking is only supported on Claude 4+ models.
        For other models, the fallback mechanism is automatically activated.
    """

    state_schema = UltrathinkMiddlewareState

    def __init__(
        self,
        budget_tokens: int = DEFAULT_BUDGET_TOKENS,
        enabled_by_default: bool = False,
        interleaved_thinking: bool = True,
        fallback_mode: Literal["tool", "prompt", "both"] = "both",
    ) -> None:
        """Initialize ultrathink middleware.

        Args:
            budget_tokens: Token budget for thinking. Must be between 1024
                and 128000. Values outside this range are clamped.
                Defaults to 10000. Higher values allow for more thorough
                reasoning but increase latency and cost.
            enabled_by_default: Whether ultrathink is enabled by default.
                If False, the agent can enable it via the enable_ultrathink tool.
                Defaults to False.
            interleaved_thinking: Enable thinking between tool calls.
                This allows the model to reason about tool results before
                deciding on next actions. Requires beta header. Only applies
                to Claude models.
                Defaults to True.
            fallback_mode: Fallback mode for non-Claude models:
                - "tool": Only provide think_step_by_step tool
                - "prompt": Only add thinking instructions to prompt
                - "both": Provide both tool and prompt instructions (recommended)
                Defaults to "both".
        """
        self.default_budget_tokens = max(
            MIN_BUDGET_TOKENS,
            min(budget_tokens, MAX_BUDGET_TOKENS),
        )
        self.enabled_by_default = enabled_by_default
        self.interleaved_thinking = interleaved_thinking
        self.fallback_mode = fallback_mode
        self._tools: list[BaseTool] = []
        self._fallback_tools: list[BaseTool] = []
        self._thinking_models: dict[str, ChatAnthropic] = {}
        self._current_model: object | None = None

        # Log initialization
        log_middleware_init(
            budget_tokens=self.default_budget_tokens,
            enabled_by_default=self.enabled_by_default,
            fallback_mode=self.fallback_mode,
            interleaved_thinking=self.interleaved_thinking,
        )

    def _get_thinking_model(
        self,
        base_model: ChatAnthropic,
        budget_tokens: int,
    ) -> ChatAnthropic:
        """Get or create a thinking-enabled model.

        This method caches models to avoid recreating them on every request.
        Models are cached by a combination of model name, budget tokens,
        and interleaved thinking setting.

        Args:
            base_model: The base ChatAnthropic model to enhance.
            budget_tokens: Token budget for thinking.

        Returns:
            A ChatAnthropic model configured with extended thinking.
        """
        # Normalize budget to valid range
        budget = max(MIN_BUDGET_TOKENS, min(budget_tokens, MAX_BUDGET_TOKENS))
        # ChatAnthropic uses 'model' attribute, not 'model_name'
        model_name = getattr(base_model, "model", "") or getattr(base_model, "model_name", "")
        cache_key = f"{model_name}_{budget}_{self.interleaved_thinking}"

        if cache_key not in self._thinking_models:
            model_kwargs: dict = {}

            if self.interleaved_thinking:
                model_kwargs["extra_headers"] = {
                    "anthropic-beta": INTERLEAVED_THINKING_BETA,
                }

            self._thinking_models[cache_key] = ChatAnthropic(
                model_name=model_name,
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

    def _supports_native_thinking(self, model: object) -> bool:
        """Check if the model supports native extended thinking.

        Native extended thinking is only available on Claude 4+ models.

        Args:
            model: The model to check.

        Returns:
            True if the model supports native extended thinking.
        """
        is_anthropic = self._is_anthropic_model(model)
        if not is_anthropic:
            model_name = getattr(model, "model", "") or getattr(model, "model_name", "") or str(type(model).__name__)
            log_model_detection(
                model_name=model_name,
                is_anthropic=False,
                supports_native=False,
                requires_fallback=True,
            )
            return False

        # ChatAnthropic uses 'model' attribute, not 'model_name'
        model_name = getattr(model, "model", "") or getattr(model, "model_name", "") or ""
        model_name_lower = model_name.lower()

        supports_native = any(prefix in model_name_lower for prefix in EXTENDED_THINKING_MODELS)

        log_model_detection(
            model_name=model_name,
            is_anthropic=True,
            supports_native=supports_native,
            requires_fallback=not supports_native,
        )

        return supports_native

    def _requires_fallback(self, model: object | None = None) -> bool:
        """Check if fallback mode is needed for the given model.

        Fallback mode is required for models that don't support
        native extended thinking (non-Claude or older Claude models).

        Args:
            model: The model to check. If None, returns True conservatively.

        Returns:
            True if fallback mode should be used.
        """
        if model is None:
            # During initialization, assume fallback may be needed
            return True

        return not self._supports_native_thinking(model)

    def _create_think_tool(self) -> BaseTool:
        """Create the think_step_by_step tool for fallback mode.

        Returns:
            The think_step_by_step tool.
        """

        @tool
        def think_step_by_step(
            problem: str,
            reasoning_steps: list[str],
            conclusion: str,
        ) -> str:
            """Think through a complex problem step by step before taking action.

            Use this tool when facing:
            - Complex mathematical problems or calculations
            - Multi-step logical reasoning
            - Code analysis and debugging
            - Architecture design decisions
            - Any task requiring careful thought

            This structured thinking helps ensure accurate and well-reasoned responses.

            Args:
                problem: Clear statement of the problem to solve.
                reasoning_steps: List of reasoning steps, each building on the previous.
                    Be thorough and explicit in your reasoning.
                conclusion: Final conclusion based on the reasoning.

            Returns:
                Confirmation with summary of the reasoning process.
            """
            steps_summary = "\n".join(
                f"  {i + 1}. {step}" for i, step in enumerate(reasoning_steps)
            )

            # Log the tool call for detailed tracking
            log_think_tool_call(
                problem=problem,
                num_steps=len(reasoning_steps),
                conclusion=conclusion,
            )

            # Visual indicator that ultrathink reasoning is being used
            print("\n🧠 [Ultrathink] Structured reasoning in progress...")
            print(f"   Problem: {problem[:80]}{'...' if len(problem) > 80 else ''}")
            print(f"   Steps: {len(reasoning_steps)}")
            print(f"   Conclusion: {conclusion[:60]}{'...' if len(conclusion) > 60 else ''}")

            return f"""Reasoning complete.

Problem: {problem}

Steps:
{steps_summary}

Conclusion: {conclusion}

You may now proceed with actions based on this reasoning."""

        return think_step_by_step

    def get_tools(self) -> list[BaseTool]:
        """Get ultrathink control tools.

        Returns a list of tools that allow the agent to dynamically
        enable or disable extended thinking during a conversation.

        For non-Claude models, also includes the think_step_by_step tool
        if fallback_mode includes "tool".

        Returns:
            List of tools based on model capabilities and fallback_mode.
        """
        if self._tools:
            # Return cached tools, but check if we need fallback tools
            if self._requires_fallback(self._current_model):
                if self.fallback_mode in ("tool", "both") and self._fallback_tools:
                    return self._tools + self._fallback_tools
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
                old_enabled = runtime.state.get("ultrathink_enabled", False)
                old_budget = runtime.state.get("budget_tokens", 0)
                runtime.state["ultrathink_enabled"] = True
                runtime.state["budget_tokens"] = budget
                log_state_change("ultrathink_enabled", old_enabled, True)
                log_state_change("budget_tokens", old_budget, budget)

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
            to improve response latency and reduce costs.

            Args:
                runtime: Tool runtime (automatically provided).

            Returns:
                Confirmation message.
            """
            if runtime:
                old_enabled = runtime.state.get("ultrathink_enabled", True)
                runtime.state["ultrathink_enabled"] = False
                log_state_change("ultrathink_enabled", old_enabled, False)

            return "Ultrathink disabled. Returning to normal response mode."

        self._tools = [enable_ultrathink, disable_ultrathink]

        # Create fallback tool
        if self.fallback_mode in ("tool", "both"):
            self._fallback_tools = [self._create_think_tool()]

        # Return with fallback if needed
        requires_fallback = self._requires_fallback(self._current_model)
        if requires_fallback:
            if self.fallback_mode in ("tool", "both"):
                all_tools = self._tools + self._fallback_tools
                log_tool_creation(
                    tools=[t.name for t in all_tools],
                    for_fallback=True,
                )
                return all_tools

        log_tool_creation(
            tools=[t.name for t in self._tools],
            for_fallback=False,
        )
        return self._tools

    def get_system_prompt_addition(self) -> str:
        """Get additional system prompt instructions for thinking mode.

        For non-Claude models, returns instructions on how to use
        the think_step_by_step tool for structured reasoning.

        Returns:
            System prompt addition, or empty string if not needed.
        """
        if not self._requires_fallback(self._current_model):
            return ""

        if self.fallback_mode not in ("prompt", "both"):
            return ""

        return """
## Extended Thinking Mode (ENABLED)

You MUST use the `think_step_by_step` tool BEFORE starting any complex task.

**ALWAYS use it for:**
- Software architecture and design decisions
- Planning multi-file implementations
- Choosing between design patterns
- Complex algorithms or data structures
- Debugging complex issues
- Any task requiring multiple steps

**How to use it:**
1. FIRST: Call `think_step_by_step` with:
   - problem: Clear statement of what you're solving
   - reasoning_steps: Your step-by-step reasoning (at least 3 steps)
   - conclusion: Your decision/plan based on the reasoning
2. THEN: Proceed with implementation

**Example:** Before implementing a game, think through:
- What classes/modules are needed?
- What design patterns to apply?
- What's the order of implementation?

This structured thinking leads to better code quality and fewer errors.
IMPORTANT: Use this tool at the START of complex tasks, not after.
"""

    def wrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], ModelResponse],
    ) -> ModelResponse:
        """Enable extended thinking if active.

        This method intercepts model calls and, if ultrathink is enabled,
        replaces the model with a thinking-enabled version (for Claude models).
        For non-Claude models, the thinking tool is available as a fallback.

        Args:
            request: The model request being processed.
            handler: The handler function to call with the modified request.

        Returns:
            The model response from the handler.
        """
        runtime = request.runtime

        # Track current model for tool generation
        self._current_model = request.model

        # Determine if ultrathink should be enabled
        is_enabled = self.enabled_by_default
        budget_tokens = self.default_budget_tokens

        if runtime and hasattr(runtime, "state"):
            is_enabled = runtime.state.get("ultrathink_enabled", is_enabled)
            budget_tokens = runtime.state.get("budget_tokens", budget_tokens)

        if is_enabled:
            current_model = request.model

            # Only apply native thinking to supported Anthropic models
            if self._supports_native_thinking(current_model):
                thinking_model = self._get_thinking_model(
                    current_model,
                    budget_tokens,
                )
                request = request.override(model=thinking_model)
                log_thinking_enabled(budget_tokens=budget_tokens, is_native=True)
            else:
                # For non-Claude models, the think_step_by_step tool is available
                log_thinking_enabled(budget_tokens=budget_tokens, is_native=False)

        return handler(request)

    async def awrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], Awaitable[ModelResponse]],
    ) -> ModelResponse:
        """(async) Enable extended thinking if active.

        Async version of wrap_model_call. This method intercepts model calls
        and, if ultrathink is enabled, replaces the model with a
        thinking-enabled version (for Claude models).

        Args:
            request: The model request being processed.
            handler: The async handler function to call with the modified request.

        Returns:
            The model response from the handler.
        """
        runtime = request.runtime

        # Track current model for tool generation
        self._current_model = request.model

        is_enabled = self.enabled_by_default
        budget_tokens = self.default_budget_tokens

        if runtime and hasattr(runtime, "state"):
            is_enabled = runtime.state.get("ultrathink_enabled", is_enabled)
            budget_tokens = runtime.state.get("budget_tokens", budget_tokens)

        if is_enabled:
            current_model = request.model

            if self._supports_native_thinking(current_model):
                thinking_model = self._get_thinking_model(
                    current_model,
                    budget_tokens,
                )
                request = request.override(model=thinking_model)
                log_thinking_enabled(budget_tokens=budget_tokens, is_native=True)
            else:
                log_thinking_enabled(budget_tokens=budget_tokens, is_native=False)

        return await handler(request)

    @property
    def tools(self) -> Sequence[BaseTool]:
        """Get middleware tools.

        Returns:
            Sequence of tools provided by this middleware.
        """
        return self.get_tools()
