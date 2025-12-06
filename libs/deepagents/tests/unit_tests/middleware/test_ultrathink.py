"""Unit tests for UltrathinkMiddleware."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from deepagents.middleware.ultrathink import (
    DEFAULT_BUDGET_TOKENS,
    INTERLEAVED_THINKING_BETA,
    MAX_BUDGET_TOKENS,
    MIN_BUDGET_TOKENS,
    UltrathinkMiddleware,
    UltrathinkMiddlewareState,
    UltrathinkState,
)


class TestUltrathinkState:
    """Tests for UltrathinkState TypedDict."""

    def test_state_accepts_valid_fields(self):
        """State should accept valid fields."""
        state: UltrathinkState = {
            "ultrathink_enabled": True,
            "budget_tokens": 10000,
        }

        assert state["ultrathink_enabled"] is True
        assert state["budget_tokens"] == 10000

    def test_state_partial_fields(self):
        """State should work with partial fields (total=False)."""
        state: UltrathinkState = {"ultrathink_enabled": False}

        assert state["ultrathink_enabled"] is False
        assert "budget_tokens" not in state


class TestUltrathinkMiddlewareInit:
    """Tests for UltrathinkMiddleware initialization."""

    def test_default_initialization(self):
        """Middleware should initialize with default values."""
        middleware = UltrathinkMiddleware()

        assert middleware.default_budget_tokens == DEFAULT_BUDGET_TOKENS
        assert middleware.enabled_by_default is False
        assert middleware.interleaved_thinking is True
        assert middleware._tools == []
        assert middleware._thinking_models == {}

    def test_custom_budget_tokens(self):
        """Middleware should accept custom budget tokens."""
        middleware = UltrathinkMiddleware(budget_tokens=20000)

        assert middleware.default_budget_tokens == 20000

    def test_budget_tokens_minimum_enforced(self):
        """Budget tokens should be clamped to minimum."""
        middleware = UltrathinkMiddleware(budget_tokens=500)

        assert middleware.default_budget_tokens == MIN_BUDGET_TOKENS

    def test_budget_tokens_maximum_enforced(self):
        """Budget tokens should be clamped to maximum."""
        middleware = UltrathinkMiddleware(budget_tokens=500000)

        assert middleware.default_budget_tokens == MAX_BUDGET_TOKENS

    def test_enabled_by_default_true(self):
        """Middleware can be enabled by default."""
        middleware = UltrathinkMiddleware(enabled_by_default=True)

        assert middleware.enabled_by_default is True

    def test_interleaved_thinking_disabled(self):
        """Interleaved thinking can be disabled."""
        middleware = UltrathinkMiddleware(interleaved_thinking=False)

        assert middleware.interleaved_thinking is False

    def test_all_parameters_combined(self):
        """All parameters should work together."""
        middleware = UltrathinkMiddleware(
            budget_tokens=25000,
            enabled_by_default=True,
            interleaved_thinking=False,
        )

        assert middleware.default_budget_tokens == 25000
        assert middleware.enabled_by_default is True
        assert middleware.interleaved_thinking is False


class TestUltrathinkMiddlewareTools:
    """Tests for UltrathinkMiddleware tools."""

    def test_get_tools_returns_two_tools(self):
        """get_tools should return enable and disable tools."""
        middleware = UltrathinkMiddleware()
        tools = middleware.get_tools()

        assert len(tools) == 2
        tool_names = [t.name for t in tools]
        assert "enable_ultrathink" in tool_names
        assert "disable_ultrathink" in tool_names

    def test_tools_are_cached(self):
        """Tools should be cached after first call."""
        middleware = UltrathinkMiddleware()

        tools1 = middleware.get_tools()
        tools2 = middleware.get_tools()

        assert tools1 is tools2

    def test_tools_property(self):
        """tools property should return same as get_tools."""
        middleware = UltrathinkMiddleware()

        assert list(middleware.tools) == middleware.get_tools()

    def test_enable_tool_has_correct_description(self):
        """enable_ultrathink tool should have descriptive docstring."""
        middleware = UltrathinkMiddleware()
        tools = middleware.get_tools()
        enable_tool = next(t for t in tools if t.name == "enable_ultrathink")

        assert "extended thinking" in enable_tool.description.lower()
        assert "complex" in enable_tool.description.lower()

    def test_disable_tool_has_correct_description(self):
        """disable_ultrathink tool should have descriptive docstring."""
        middleware = UltrathinkMiddleware()
        tools = middleware.get_tools()
        disable_tool = next(t for t in tools if t.name == "disable_ultrathink")

        assert "disable" in disable_tool.description.lower()


class TestEnableUltrathinkTool:
    """Tests for the enable_ultrathink tool."""

    def test_enable_returns_confirmation_message(self):
        """enable_ultrathink should return confirmation with budget."""
        middleware = UltrathinkMiddleware()
        tools = middleware.get_tools()
        enable_tool = next(t for t in tools if t.name == "enable_ultrathink")

        # When called without runtime (as in unit tests), it still works
        result = enable_tool.invoke({"budget_tokens": 15000})

        assert "15,000" in result
        assert "enabled" in result.lower()

    def test_enable_returns_message_with_default_budget(self):
        """enable_ultrathink should use default budget if not specified."""
        middleware = UltrathinkMiddleware()
        tools = middleware.get_tools()
        enable_tool = next(t for t in tools if t.name == "enable_ultrathink")

        result = enable_tool.invoke({})

        assert "10,000" in result  # DEFAULT_BUDGET_TOKENS
        assert "enabled" in result.lower()

    def test_enable_enforces_minimum_budget_in_message(self):
        """enable_ultrathink message should show clamped minimum budget."""
        middleware = UltrathinkMiddleware()
        tools = middleware.get_tools()
        enable_tool = next(t for t in tools if t.name == "enable_ultrathink")

        result = enable_tool.invoke({"budget_tokens": 100})

        # Should show MIN_BUDGET_TOKENS (1024) instead of 100
        assert "1,024" in result
        assert "enabled" in result.lower()

    def test_enable_enforces_maximum_budget_in_message(self):
        """enable_ultrathink message should show clamped maximum budget."""
        middleware = UltrathinkMiddleware()
        tools = middleware.get_tools()
        enable_tool = next(t for t in tools if t.name == "enable_ultrathink")

        result = enable_tool.invoke({"budget_tokens": 500000})

        # Should show MAX_BUDGET_TOKENS (128000) instead of 500000
        assert "128,000" in result
        assert "enabled" in result.lower()


class TestDisableUltrathinkTool:
    """Tests for the disable_ultrathink tool."""

    def test_disable_returns_confirmation_message(self):
        """disable_ultrathink should return confirmation message."""
        middleware = UltrathinkMiddleware()
        tools = middleware.get_tools()
        disable_tool = next(t for t in tools if t.name == "disable_ultrathink")

        result = disable_tool.invoke({})

        assert "disabled" in result.lower()


class TestIsAnthropicModel:
    """Tests for _is_anthropic_model method."""

    def test_returns_true_for_chat_anthropic(self):
        """Should return True for ChatAnthropic instances."""
        from langchain_anthropic import ChatAnthropic

        middleware = UltrathinkMiddleware()

        # Create a real ChatAnthropic instance (will not make API calls)
        model = ChatAnthropic(model_name="claude-sonnet-4-5-20250929")
        assert middleware._is_anthropic_model(model) is True

    def test_returns_false_for_other_models(self):
        """Should return False for non-Anthropic models."""
        middleware = UltrathinkMiddleware()

        mock_model = MagicMock()  # Generic mock, not ChatAnthropic

        assert middleware._is_anthropic_model(mock_model) is False

    def test_returns_false_for_none(self):
        """Should return False for None."""
        middleware = UltrathinkMiddleware()

        assert middleware._is_anthropic_model(None) is False

    def test_returns_false_for_string(self):
        """Should return False for string."""
        middleware = UltrathinkMiddleware()

        assert middleware._is_anthropic_model("claude-sonnet-4") is False


class TestGetThinkingModel:
    """Tests for _get_thinking_model method."""

    def test_creates_model_with_thinking_enabled(self):
        """Should create model with thinking parameter."""
        middleware = UltrathinkMiddleware()

        mock_base_model = MagicMock()
        mock_base_model.model_name = "claude-sonnet-4-5-20250929"
        mock_base_model.max_tokens = 16000

        with patch(
            "deepagents.middleware.ultrathink.ChatAnthropic"
        ) as MockChatAnthropic:
            MockChatAnthropic.return_value = MagicMock()

            middleware._get_thinking_model(mock_base_model, 10000)

            MockChatAnthropic.assert_called_once()
            call_kwargs = MockChatAnthropic.call_args[1]

            assert call_kwargs["model_name"] == "claude-sonnet-4-5-20250929"
            assert call_kwargs["max_tokens"] == 16000
            assert call_kwargs["thinking"] == {"type": "enabled", "budget_tokens": 10000}

    def test_includes_interleaved_thinking_header(self):
        """Should include beta header when interleaved_thinking is True."""
        middleware = UltrathinkMiddleware(interleaved_thinking=True)

        mock_base_model = MagicMock()
        mock_base_model.model_name = "claude-sonnet-4-5-20250929"
        mock_base_model.max_tokens = 16000

        with patch(
            "deepagents.middleware.ultrathink.ChatAnthropic"
        ) as MockChatAnthropic:
            MockChatAnthropic.return_value = MagicMock()

            middleware._get_thinking_model(mock_base_model, 10000)

            call_kwargs = MockChatAnthropic.call_args[1]
            assert call_kwargs["model_kwargs"]["extra_headers"]["anthropic-beta"] == (
                INTERLEAVED_THINKING_BETA
            )

    def test_no_header_when_interleaved_thinking_disabled(self):
        """Should not include beta header when interleaved_thinking is False."""
        middleware = UltrathinkMiddleware(interleaved_thinking=False)

        mock_base_model = MagicMock()
        mock_base_model.model_name = "claude-sonnet-4-5-20250929"
        mock_base_model.max_tokens = 16000

        with patch(
            "deepagents.middleware.ultrathink.ChatAnthropic"
        ) as MockChatAnthropic:
            MockChatAnthropic.return_value = MagicMock()

            middleware._get_thinking_model(mock_base_model, 10000)

            call_kwargs = MockChatAnthropic.call_args[1]
            assert call_kwargs["model_kwargs"] is None

    def test_models_are_cached(self):
        """Same configuration should return cached model."""
        middleware = UltrathinkMiddleware()

        mock_base_model = MagicMock()
        mock_base_model.model_name = "claude-sonnet-4-5-20250929"
        mock_base_model.max_tokens = 16000

        with patch(
            "deepagents.middleware.ultrathink.ChatAnthropic"
        ) as MockChatAnthropic:
            mock_thinking_model = MagicMock()
            MockChatAnthropic.return_value = mock_thinking_model

            model1 = middleware._get_thinking_model(mock_base_model, 10000)
            model2 = middleware._get_thinking_model(mock_base_model, 10000)

            assert MockChatAnthropic.call_count == 1
            assert model1 is model2

    def test_different_budgets_create_different_models(self):
        """Different budgets should create separate cached models."""
        middleware = UltrathinkMiddleware()

        mock_base_model = MagicMock()
        mock_base_model.model_name = "claude-sonnet-4-5-20250929"
        mock_base_model.max_tokens = 16000

        with patch(
            "deepagents.middleware.ultrathink.ChatAnthropic"
        ) as MockChatAnthropic:
            MockChatAnthropic.return_value = MagicMock()

            middleware._get_thinking_model(mock_base_model, 10000)
            middleware._get_thinking_model(mock_base_model, 20000)

            assert MockChatAnthropic.call_count == 2

    def test_normalizes_budget_to_valid_range(self):
        """Should clamp budget to valid range."""
        middleware = UltrathinkMiddleware()

        mock_base_model = MagicMock()
        mock_base_model.model_name = "claude-sonnet-4-5-20250929"
        mock_base_model.max_tokens = 16000

        with patch(
            "deepagents.middleware.ultrathink.ChatAnthropic"
        ) as MockChatAnthropic:
            MockChatAnthropic.return_value = MagicMock()

            # Test minimum
            middleware._get_thinking_model(mock_base_model, 100)
            call_kwargs = MockChatAnthropic.call_args[1]
            assert call_kwargs["thinking"]["budget_tokens"] == MIN_BUDGET_TOKENS


class TestWrapModelCall:
    """Tests for wrap_model_call method."""

    def test_passes_through_when_disabled(self):
        """Should pass through without modification when disabled."""
        middleware = UltrathinkMiddleware(enabled_by_default=False)

        request = MagicMock()
        request.runtime = MagicMock()
        request.runtime.state = {"ultrathink_enabled": False}

        handler = MagicMock(return_value="response")

        result = middleware.wrap_model_call(request, handler)

        handler.assert_called_once_with(request)
        request.override.assert_not_called()
        assert result == "response"

    def test_passes_through_when_no_runtime(self):
        """Should pass through when runtime is not available."""
        middleware = UltrathinkMiddleware(enabled_by_default=False)

        request = MagicMock()
        request.runtime = None

        handler = MagicMock(return_value="response")

        result = middleware.wrap_model_call(request, handler)

        handler.assert_called_once_with(request)
        assert result == "response"

    def test_passes_through_for_non_anthropic_model(self):
        """Should pass through for non-Anthropic models."""
        middleware = UltrathinkMiddleware(enabled_by_default=True)

        request = MagicMock()
        request.runtime = MagicMock()
        request.runtime.state = {}
        request.model = MagicMock()  # Not a ChatAnthropic

        handler = MagicMock(return_value="response")

        result = middleware.wrap_model_call(request, handler)

        handler.assert_called_once_with(request)
        request.override.assert_not_called()
        assert result == "response"

    def test_overrides_model_when_enabled(self):
        """Should override model with thinking model when enabled."""
        middleware = UltrathinkMiddleware(enabled_by_default=False)

        from langchain_anthropic import ChatAnthropic

        mock_model = MagicMock(spec=ChatAnthropic)
        mock_model.model_name = "claude-sonnet-4-5-20250929"
        mock_model.max_tokens = 16000

        request = MagicMock()
        request.runtime = MagicMock()
        request.runtime.state = {"ultrathink_enabled": True, "budget_tokens": 10000}
        request.model = mock_model

        modified_request = MagicMock()
        request.override.return_value = modified_request

        handler = MagicMock(return_value="response")

        with patch.object(middleware, "_is_anthropic_model", return_value=True):
            with patch.object(
                middleware, "_get_thinking_model", return_value=MagicMock()
            ) as mock_get:
                result = middleware.wrap_model_call(request, handler)

                mock_get.assert_called_once_with(mock_model, 10000)
                request.override.assert_called_once()
                handler.assert_called_once_with(modified_request)

    def test_uses_default_values_when_state_empty(self):
        """Should use default values when state doesn't have values."""
        middleware = UltrathinkMiddleware(
            enabled_by_default=True, budget_tokens=15000
        )

        from langchain_anthropic import ChatAnthropic

        mock_model = MagicMock(spec=ChatAnthropic)
        mock_model.model_name = "claude-sonnet-4-5-20250929"
        mock_model.max_tokens = 16000

        request = MagicMock()
        request.runtime = MagicMock()
        request.runtime.state = {}  # Empty state
        request.model = mock_model

        handler = MagicMock(return_value="response")

        with patch.object(middleware, "_is_anthropic_model", return_value=True):
            with patch.object(
                middleware, "_get_thinking_model", return_value=MagicMock()
            ) as mock_get:
                middleware.wrap_model_call(request, handler)

                # Should use default budget from middleware
                mock_get.assert_called_once_with(mock_model, 15000)


class TestAwrapModelCall:
    """Tests for awrap_model_call async method."""

    @pytest.mark.asyncio
    async def test_passes_through_when_disabled(self):
        """Should pass through without modification when disabled."""
        middleware = UltrathinkMiddleware(enabled_by_default=False)

        request = MagicMock()
        request.runtime = MagicMock()
        request.runtime.state = {"ultrathink_enabled": False}

        async def async_handler(req):
            return "response"

        result = await middleware.awrap_model_call(request, async_handler)

        request.override.assert_not_called()
        assert result == "response"

    @pytest.mark.asyncio
    async def test_overrides_model_when_enabled(self):
        """Should override model with thinking model when enabled."""
        middleware = UltrathinkMiddleware(enabled_by_default=False)

        from langchain_anthropic import ChatAnthropic

        mock_model = MagicMock(spec=ChatAnthropic)
        mock_model.model_name = "claude-sonnet-4-5-20250929"
        mock_model.max_tokens = 16000

        request = MagicMock()
        request.runtime = MagicMock()
        request.runtime.state = {"ultrathink_enabled": True, "budget_tokens": 10000}
        request.model = mock_model

        modified_request = MagicMock()
        request.override.return_value = modified_request

        async def async_handler(req):
            return "response"

        with patch.object(middleware, "_is_anthropic_model", return_value=True):
            with patch.object(
                middleware, "_get_thinking_model", return_value=MagicMock()
            ):
                result = await middleware.awrap_model_call(request, async_handler)

                request.override.assert_called_once()
                assert result == "response"


class TestStateSchema:
    """Tests for state_schema class attribute."""

    def test_has_state_schema(self):
        """Middleware should have state_schema attribute."""
        assert hasattr(UltrathinkMiddleware, "state_schema")
        assert UltrathinkMiddleware.state_schema is UltrathinkMiddlewareState
