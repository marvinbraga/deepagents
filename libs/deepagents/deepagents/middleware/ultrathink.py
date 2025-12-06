"""Ultrathink middleware for extended thinking capabilities.

This module provides middleware that enables Claude's extended thinking feature,
allowing the model to reason more deeply before responding. Extended thinking
is particularly useful for complex mathematical problems, multi-step reasoning,
code analysis, and architecture planning.

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

Note:
    Extended thinking is only supported on Claude 4+ models (Opus 4.5, Sonnet 4.5,
    Sonnet 4, Haiku 4.5). Using it with unsupported models will have no effect.
"""

from __future__ import annotations

from typing import Awaitable, Callable, Sequence, TypedDict

from langchain.agents.middleware.types import (
    AgentMiddleware,
    ModelRequest,
    ModelResponse,
)
from langchain.tools import ToolRuntime
from langchain_anthropic import ChatAnthropic
from langchain_core.tools import BaseTool, tool


# Constants
MIN_BUDGET_TOKENS = 1024
"""Minimum token budget for extended thinking."""

DEFAULT_BUDGET_TOKENS = 10000
"""Default token budget for extended thinking."""

MAX_BUDGET_TOKENS = 128000
"""Maximum token budget for extended thinking."""

INTERLEAVED_THINKING_BETA = "interleaved-thinking-2025-05-14"
"""Beta header for interleaved thinking support."""


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

    This middleware enables Claude's extended thinking feature, allowing
    the model to reason more deeply before responding. Extended thinking
    is particularly useful for:

    - Complex mathematical problems and proofs
    - Multi-step reasoning tasks
    - Code analysis and architecture planning
    - Difficult problem-solving scenarios

    The middleware can be configured to be always enabled, or controlled
    dynamically through tools that the agent can invoke.

    Attributes:
        default_budget_tokens: Default token budget for thinking.
        enabled_by_default: Whether ultrathink is enabled by default.
        interleaved_thinking: Enable thinking between tool calls.

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
                and 128000. Values outside this range are clamped.
                Defaults to 10000. Higher values allow for more thorough
                reasoning but increase latency and cost.
            enabled_by_default: Whether ultrathink is enabled by default.
                If False, the agent can enable it via the enable_ultrathink tool.
                Defaults to False.
            interleaved_thinking: Enable thinking between tool calls.
                This allows the model to reason about tool results before
                deciding on next actions. Requires beta header.
                Defaults to True.
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
        cache_key = f"{base_model.model_name}_{budget}_{self.interleaved_thinking}"

        if cache_key not in self._thinking_models:
            model_kwargs: dict = {}

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

        Returns a list of tools that allow the agent to dynamically
        enable or disable extended thinking during a conversation.

        Returns:
            List of tools: enable_ultrathink and disable_ultrathink.
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
            to improve response latency and reduce costs.

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

        Async version of wrap_model_call. This method intercepts model calls
        and, if ultrathink is enabled, replaces the model with a
        thinking-enabled version.

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
