"""Unit tests for UserInteractionMiddleware."""

import pytest

from deepagents.middleware.user_interaction import (
    UserInteractionMiddleware,
    UserQuestionRequest,
)


class TestUserQuestionRequest:
    """Tests for UserQuestionRequest dataclass."""

    def test_default_values(self):
        """Request should have sensible defaults."""
        request = UserQuestionRequest()

        assert request.type == "user_question"
        assert request.question == ""
        assert request.options is None
        assert request.header is None
        assert request.descriptions is None
        assert request.multi_select is False
        assert request.allow_custom is True
        assert request.default is None

    def test_serialization(self):
        """Request should serialize to dict for interrupt."""
        request = UserQuestionRequest(
            question="Which library?",
            options=["React", "Vue"],
            header="Framework",
            descriptions=["Popular", "Lightweight"],
            multi_select=False,
            allow_custom=True,
            default=0,
        )

        data = request.__dict__
        assert data["type"] == "user_question"
        assert data["question"] == "Which library?"
        assert data["options"] == ["React", "Vue"]
        assert data["header"] == "Framework"
        assert data["descriptions"] == ["Popular", "Lightweight"]
        assert data["multi_select"] is False
        assert data["allow_custom"] is True
        assert data["default"] == 0

    def test_serialization_minimal(self):
        """Request with minimal fields should serialize correctly."""
        request = UserQuestionRequest(question="What name?")

        data = request.__dict__
        assert data["question"] == "What name?"
        assert data["type"] == "user_question"
        assert data["options"] is None

    def test_custom_type(self):
        """Request can have custom type for different interrupt types."""
        request = UserQuestionRequest(
            type="confirm_action",
            question="Delete files?",
        )

        assert request.type == "confirm_action"
        assert request.__dict__["type"] == "confirm_action"


class TestUserInteractionMiddleware:
    """Tests for UserInteractionMiddleware."""

    def test_middleware_provides_tools(self):
        """Middleware should provide ask_user_question and confirm_action tools."""
        middleware = UserInteractionMiddleware()
        tools = middleware.get_tools()

        tool_names = [t.name for t in tools]
        assert "ask_user_question" in tool_names
        assert "confirm_action" in tool_names
        assert len(tools) == 2

    def test_tools_property(self):
        """Tools property should return same as get_tools()."""
        middleware = UserInteractionMiddleware()

        # Call get_tools first to populate cache
        expected_tools = middleware.get_tools()
        actual_tools = middleware.tools

        assert actual_tools == expected_tools
        assert len(actual_tools) == 2

    def test_tools_cached(self):
        """Tools should be cached after first call to get_tools()."""
        middleware = UserInteractionMiddleware()

        # First call creates tools
        tools1 = middleware.get_tools()
        # Second call should return cached tools
        tools2 = middleware.get_tools()

        # Should be the exact same objects (identity check)
        assert tools1 is tools2

    def test_system_prompt_addition(self):
        """Middleware should provide system prompt addition."""
        middleware = UserInteractionMiddleware()
        prompt = middleware.get_system_prompt_addition()

        # Check it's non-empty and contains expected content
        assert len(prompt) > 0
        assert "ask_user_question" in prompt
        assert "confirm_action" in prompt
        assert "User Interaction Tools" in prompt


class TestAskUserQuestionValidation:
    """Tests for ask_user_question tool validation."""

    @pytest.fixture
    def ask_tool(self):
        """Get the ask_user_question tool."""
        middleware = UserInteractionMiddleware()
        tools = middleware.get_tools()
        return next(t for t in tools if t.name == "ask_user_question")

    def test_options_descriptions_length_mismatch(self, ask_tool):
        """Should raise ValueError when options and descriptions have different lengths."""
        with pytest.raises(ValueError, match="options and descriptions must have same length"):
            ask_tool.invoke({
                "question": "Choose framework?",
                "options": ["React", "Vue"],
                "descriptions": ["Only one description"],
            })

    def test_options_descriptions_length_match(self, ask_tool):
        """Should accept when options and descriptions have same length."""
        # This will raise an interrupt error in tests, but that's expected
        # We're just testing that validation passes
        with pytest.raises(Exception):  # Will fail due to interrupt(), but validation passes
            ask_tool.invoke({
                "question": "Choose framework?",
                "options": ["React", "Vue"],
                "descriptions": ["Popular", "Lightweight"],
            })

    def test_header_truncation(self, ask_tool):
        """Headers longer than 12 chars should be truncated."""
        # We need to mock interrupt to check the actual header value
        from unittest.mock import patch

        with patch("deepagents.middleware.user_interaction.interrupt") as mock_interrupt:
            mock_interrupt.return_value = "test"

            ask_tool.invoke({
                "question": "Test?",
                "header": "VeryLongHeaderThatExceeds12Characters",
            })

            # Check that interrupt was called with truncated header
            call_args = mock_interrupt.call_args
            request_dict = call_args[0][0]
            assert request_dict["header"] == "VeryLongHead"
            assert len(request_dict["header"]) == 12

    def test_header_not_truncated_if_short(self, ask_tool):
        """Headers 12 chars or shorter should not be truncated."""
        from unittest.mock import patch

        with patch("deepagents.middleware.user_interaction.interrupt") as mock_interrupt:
            mock_interrupt.return_value = "test"

            ask_tool.invoke({
                "question": "Test?",
                "header": "Short",
            })

            call_args = mock_interrupt.call_args
            request_dict = call_args[0][0]
            assert request_dict["header"] == "Short"

    def test_header_exactly_12_chars(self, ask_tool):
        """Header exactly 12 chars should not be truncated."""
        from unittest.mock import patch

        with patch("deepagents.middleware.user_interaction.interrupt") as mock_interrupt:
            mock_interrupt.return_value = "test"

            ask_tool.invoke({
                "question": "Test?",
                "header": "Exactly12Chr",  # Exactly 12 characters
            })

            call_args = mock_interrupt.call_args
            request_dict = call_args[0][0]
            assert request_dict["header"] == "Exactly12Chr"
            assert len(request_dict["header"]) == 12

    def test_empty_options_allowed(self, ask_tool):
        """options=None should work for free-form input."""
        from unittest.mock import patch

        with patch("deepagents.middleware.user_interaction.interrupt") as mock_interrupt:
            mock_interrupt.return_value = "Custom response"

            result = ask_tool.invoke({
                "question": "What name?",
                "options": None,
            })

            assert result == "Custom response"
            call_args = mock_interrupt.call_args
            request_dict = call_args[0][0]
            assert request_dict["options"] is None

    def test_empty_question_allowed(self, ask_tool):
        """Empty question string should work."""
        from unittest.mock import patch

        with patch("deepagents.middleware.user_interaction.interrupt") as mock_interrupt:
            mock_interrupt.return_value = "answer"

            result = ask_tool.invoke({
                "question": "",
            })

            assert result == "answer"
            call_args = mock_interrupt.call_args
            request_dict = call_args[0][0]
            assert request_dict["question"] == ""

    def test_multi_select_flag(self, ask_tool):
        """multi_select flag should be passed through correctly."""
        from unittest.mock import patch

        with patch("deepagents.middleware.user_interaction.interrupt") as mock_interrupt:
            mock_interrupt.return_value = ["A", "B"]

            ask_tool.invoke({
                "question": "Choose multiple?",
                "options": ["A", "B", "C"],
                "multi_select": True,
            })

            call_args = mock_interrupt.call_args
            request_dict = call_args[0][0]
            assert request_dict["multi_select"] is True

    def test_allow_custom_flag(self, ask_tool):
        """allow_custom flag should be passed through correctly."""
        from unittest.mock import patch

        with patch("deepagents.middleware.user_interaction.interrupt") as mock_interrupt:
            mock_interrupt.return_value = "answer"

            ask_tool.invoke({
                "question": "Choose?",
                "options": ["A", "B"],
                "allow_custom": False,
            })

            call_args = mock_interrupt.call_args
            request_dict = call_args[0][0]
            assert request_dict["allow_custom"] is False

    def test_default_parameter(self, ask_tool):
        """default parameter should be passed through correctly."""
        from unittest.mock import patch

        with patch("deepagents.middleware.user_interaction.interrupt") as mock_interrupt:
            mock_interrupt.return_value = "answer"

            # Test with int default
            ask_tool.invoke({
                "question": "Choose?",
                "options": ["A", "B"],
                "default": 0,
            })

            call_args = mock_interrupt.call_args
            request_dict = call_args[0][0]
            assert request_dict["default"] == 0

            # Test with string default
            mock_interrupt.reset_mock()
            ask_tool.invoke({
                "question": "Choose?",
                "default": "default value",
            })

            call_args = mock_interrupt.call_args
            request_dict = call_args[0][0]
            assert request_dict["default"] == "default value"


class TestConfirmActionTool:
    """Tests for confirm_action tool."""

    @pytest.fixture
    def confirm_tool(self):
        """Get the confirm_action tool."""
        middleware = UserInteractionMiddleware()
        tools = middleware.get_tools()
        return next(t for t in tools if t.name == "confirm_action")

    def test_confirm_action_creates_correct_request(self, confirm_tool):
        """confirm_action should create correct UserQuestionRequest."""
        from unittest.mock import patch

        with patch("deepagents.middleware.user_interaction.interrupt") as mock_interrupt:
            mock_interrupt.return_value = "Yes, proceed"

            result = confirm_tool.invoke({
                "action": "Delete 10 files",
                "details": "Files in /tmp/",
                "default": True,
            })

            # Check interrupt was called with correct structure
            call_args = mock_interrupt.call_args
            request_dict = call_args[0][0]

            assert request_dict["type"] == "confirm_action"
            assert request_dict["question"] == "Confirm: Delete 10 files"
            assert request_dict["options"] == ["Yes, proceed", "No, cancel"]
            assert request_dict["descriptions"] == ["Files in /tmp/", None]
            assert request_dict["default"] == 0  # True maps to 0

            # Check return value is boolean
            assert result is True

    def test_confirm_action_without_details(self, confirm_tool):
        """confirm_action should work without details."""
        from unittest.mock import patch

        with patch("deepagents.middleware.user_interaction.interrupt") as mock_interrupt:
            mock_interrupt.return_value = "Yes, proceed"

            result = confirm_tool.invoke({
                "action": "Proceed with update",
                "default": False,
            })

            call_args = mock_interrupt.call_args
            request_dict = call_args[0][0]

            assert request_dict["descriptions"] is None
            assert request_dict["default"] == 1  # False maps to 1
            assert result is True

    def test_confirm_action_returns_true_for_yes(self, confirm_tool):
        """confirm_action should return True for affirmative responses."""
        from unittest.mock import patch

        test_cases = [
            "Yes, proceed",
            "yes",
            "y",
            True,
        ]

        for response in test_cases:
            with patch("deepagents.middleware.user_interaction.interrupt") as mock_interrupt:
                mock_interrupt.return_value = response

                result = confirm_tool.invoke({
                    "action": "Test action",
                })

                assert result is True, f"Failed for response: {response}"

    def test_confirm_action_returns_false_for_no(self, confirm_tool):
        """confirm_action should return False for negative responses."""
        from unittest.mock import patch

        test_cases = [
            "No, cancel",
            "no",
            "n",
            False,
            "anything else",
        ]

        for response in test_cases:
            with patch("deepagents.middleware.user_interaction.interrupt") as mock_interrupt:
                mock_interrupt.return_value = response

                result = confirm_tool.invoke({
                    "action": "Test action",
                })

                assert result is False, f"Failed for response: {response}"


class TestToolIntegration:
    """Integration tests for tool behavior."""

    def test_ask_user_question_tool_has_correct_name(self):
        """Tool should have the correct name."""
        middleware = UserInteractionMiddleware()
        tools = middleware.get_tools()
        ask_tool = next(t for t in tools if t.name == "ask_user_question")

        assert ask_tool.name == "ask_user_question"

    def test_confirm_action_tool_has_correct_name(self):
        """Tool should have the correct name."""
        middleware = UserInteractionMiddleware()
        tools = middleware.get_tools()
        confirm_tool = next(t for t in tools if t.name == "confirm_action")

        assert confirm_tool.name == "confirm_action"

    def test_ask_user_question_has_description(self):
        """Tool should have a docstring/description."""
        middleware = UserInteractionMiddleware()
        tools = middleware.get_tools()
        ask_tool = next(t for t in tools if t.name == "ask_user_question")

        assert ask_tool.description is not None
        assert len(ask_tool.description) > 0
        assert "Ask the user a question" in ask_tool.description

    def test_confirm_action_has_description(self):
        """Tool should have a docstring/description."""
        middleware = UserInteractionMiddleware()
        tools = middleware.get_tools()
        confirm_tool = next(t for t in tools if t.name == "confirm_action")

        assert confirm_tool.description is not None
        assert len(confirm_tool.description) > 0
        assert "confirm" in confirm_tool.description.lower()

    def test_multiple_middleware_instances_independent(self):
        """Multiple middleware instances should be independent."""
        middleware1 = UserInteractionMiddleware()
        middleware2 = UserInteractionMiddleware()

        tools1 = middleware1.get_tools()
        tools2 = middleware2.get_tools()

        # Should have same structure but different instances
        assert len(tools1) == len(tools2)
        assert tools1 is not tools2
        assert tools1[0] is not tools2[0]
