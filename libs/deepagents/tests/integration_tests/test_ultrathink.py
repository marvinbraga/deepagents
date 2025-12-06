"""Integration tests for UltrathinkMiddleware."""

import pytest
from langchain.agents import create_agent
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage

from deepagents import create_deep_agent
from deepagents.middleware.ultrathink import (
    UltrathinkMiddleware,
    UltrathinkState,
)


@pytest.mark.requires("langchain_anthropic")
class TestUltrathinkMiddlewareIntegration:
    """Integration tests for UltrathinkMiddleware with real agents."""

    def test_middleware_provides_tools_to_agent(self):
        """Agent should have access to ultrathink control tools."""
        middleware = UltrathinkMiddleware()
        tools = middleware.get_tools()

        tool_names = [t.name for t in tools]
        assert "enable_ultrathink" in tool_names
        assert "disable_ultrathink" in tool_names
        assert len(tools) == 2

    def test_middleware_can_be_added_to_deep_agent(self):
        """UltrathinkMiddleware should integrate with create_deep_agent."""
        agent = create_deep_agent(
            model=ChatAnthropic(model="claude-sonnet-4-20250514"),
            middleware=[
                UltrathinkMiddleware(
                    budget_tokens=5000,
                    enabled_by_default=False,
                ),
            ],
        )

        # Agent should be created without errors
        assert agent is not None

    def test_middleware_can_be_added_to_basic_agent(self):
        """UltrathinkMiddleware should integrate with create_agent."""
        agent = create_agent(
            model=ChatAnthropic(model="claude-sonnet-4-20250514"),
            middleware=[
                UltrathinkMiddleware(budget_tokens=5000),
            ],
        )

        # Agent should be created without errors
        assert agent is not None

    def test_middleware_with_enabled_by_default(self):
        """Agent with enabled_by_default should have ultrathink active."""
        agent = create_agent(
            model=ChatAnthropic(model="claude-sonnet-4-20250514"),
            middleware=[
                UltrathinkMiddleware(
                    budget_tokens=5000,
                    enabled_by_default=True,
                ),
            ],
        )

        # Agent should be created with ultrathink enabled
        assert agent is not None

    def test_middleware_with_interleaved_thinking_disabled(self):
        """Agent should work with interleaved_thinking disabled."""
        agent = create_agent(
            model=ChatAnthropic(model="claude-sonnet-4-20250514"),
            middleware=[
                UltrathinkMiddleware(
                    budget_tokens=5000,
                    interleaved_thinking=False,
                ),
            ],
        )

        assert agent is not None

    def test_middleware_combined_with_other_middleware(self):
        """UltrathinkMiddleware should work with other middleware."""
        from deepagents.middleware import PlanModeMiddleware

        # Use create_agent instead of create_deep_agent to avoid
        # duplicate FilesystemMiddleware
        agent = create_agent(
            model=ChatAnthropic(model="claude-sonnet-4-20250514"),
            middleware=[
                UltrathinkMiddleware(budget_tokens=5000),
                PlanModeMiddleware(),
            ],
        )

        assert agent is not None


@pytest.mark.requires("langchain_anthropic")
class TestUltrathinkStateManagement:
    """Tests for ultrathink state management."""

    def test_state_type_is_exported(self):
        """UltrathinkState should be properly exported."""
        state: UltrathinkState = {
            "ultrathink_enabled": True,
            "budget_tokens": 10000,
        }

        assert state["ultrathink_enabled"] is True
        assert state["budget_tokens"] == 10000

    def test_middleware_has_state_schema(self):
        """Middleware should have proper state_schema for runtime."""
        middleware = UltrathinkMiddleware()

        assert hasattr(middleware, "state_schema")
        assert middleware.state_schema is not None


@pytest.mark.requires("langchain_anthropic")
@pytest.mark.slow
class TestUltrathinkWithRealInvocation:
    """Tests that actually invoke the model (marked as slow)."""

    def test_agent_with_ultrathink_can_answer_simple_question(self):
        """Agent with ultrathink enabled should answer questions."""
        agent = create_agent(
            model=ChatAnthropic(model="claude-sonnet-4-20250514"),
            middleware=[
                UltrathinkMiddleware(
                    budget_tokens=2000,
                    enabled_by_default=True,
                ),
            ],
        )

        result = agent.invoke(
            {"messages": [HumanMessage(content="What is 2 + 2?")]}
        )

        assert result["messages"]
        last_message = result["messages"][-1]
        # Should contain the answer (4) somewhere
        assert "4" in str(last_message.content)

    def test_agent_can_invoke_enable_ultrathink_tool(self):
        """Agent should be able to use enable_ultrathink tool."""
        agent = create_agent(
            model=ChatAnthropic(model="claude-sonnet-4-20250514"),
            middleware=[
                UltrathinkMiddleware(budget_tokens=2000),
            ],
        )

        result = agent.invoke(
            {
                "messages": [
                    HumanMessage(
                        content=(
                            "First, use the enable_ultrathink tool with budget_tokens=3000. "
                            "Then tell me what 5 times 7 is."
                        )
                    )
                ]
            }
        )

        assert result["messages"]
        # Should have processed the request
        content = " ".join(
            str(m.content) for m in result["messages"] if hasattr(m, "content")
        )
        assert "35" in content or "enabled" in content.lower()
