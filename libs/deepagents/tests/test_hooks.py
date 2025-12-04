"""Unit tests for the hooks system."""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from deepagents.hooks.executor import HookExecutor
from deepagents.hooks.registry import HookRegistry, ShellHook
from deepagents.hooks.types import HookContext, HookEvent, HookProtocol, HookResult
from deepagents.middleware.hooks import HooksMiddleware


class TestHookEvent:
    """Test HookEvent enum values."""

    def test_hook_event_values(self):
        """Test that all expected hook events exist."""
        assert HookEvent.PRE_TOOL_CALL.value == "pre_tool_call"
        assert HookEvent.POST_TOOL_CALL.value == "post_tool_call"
        assert HookEvent.USER_PROMPT_SUBMIT.value == "user_prompt_submit"
        assert HookEvent.AGENT_RESPONSE.value == "agent_response"
        assert HookEvent.SESSION_START.value == "session_start"
        assert HookEvent.SESSION_END.value == "session_end"
        assert HookEvent.TOOL_APPROVAL.value == "tool_approval"
        assert HookEvent.ERROR.value == "error"

    def test_hook_event_is_string_enum(self):
        """Test that HookEvent is a string enum."""
        assert isinstance(HookEvent.PRE_TOOL_CALL, str)
        assert isinstance(HookEvent.POST_TOOL_CALL, HookEvent)


class TestHookContext:
    """Test HookContext creation and serialization."""

    def test_hook_context_creation(self):
        """Test creating a HookContext."""
        context = HookContext(
            event=HookEvent.PRE_TOOL_CALL,
            data={"tool": "read_file", "args": {"path": "/test.txt"}},
            session_state={"user_id": "123"},
            assistant_id="test-assistant",
        )

        assert context.event == HookEvent.PRE_TOOL_CALL
        assert context.data == {"tool": "read_file", "args": {"path": "/test.txt"}}
        assert context.session_state == {"user_id": "123"}
        assert context.assistant_id == "test-assistant"

    def test_hook_context_without_assistant_id(self):
        """Test creating a HookContext without assistant_id."""
        context = HookContext(
            event=HookEvent.SESSION_START,
            data={},
            session_state={},
        )

        assert context.event == HookEvent.SESSION_START
        assert context.assistant_id is None

    def test_hook_context_serialization(self):
        """Test that HookContext can be serialized to dict."""
        context = HookContext(
            event=HookEvent.PRE_TOOL_CALL,
            data={"test": "value"},
            session_state={"state": "data"},
            assistant_id="assistant-1",
        )

        # Manual serialization for JSON
        context_dict = {
            "event": context.event.value,
            "data": context.data,
            "session_state": context.session_state,
            "assistant_id": context.assistant_id,
        }

        assert json.dumps(context_dict)  # Should not raise


class TestHookRegistry:
    """Test HookRegistry registration and retrieval."""

    def test_registry_initialization(self):
        """Test creating an empty registry."""
        registry = HookRegistry()
        assert registry._python_hooks == {}
        assert registry._shell_hooks == {}

    def test_register_python_hook(self):
        """Test registering a Python hook."""
        registry = HookRegistry()

        # Create a mock hook
        mock_hook = Mock(spec=HookProtocol)
        mock_hook.name = "test_hook"
        mock_hook.events = [HookEvent.PRE_TOOL_CALL]
        mock_hook.priority = 50

        registry.register(mock_hook)

        assert "test_hook" in registry._python_hooks
        assert registry._python_hooks["test_hook"] == mock_hook

    def test_register_duplicate_python_hook_raises(self):
        """Test that registering duplicate hook raises ValueError."""
        registry = HookRegistry()

        mock_hook = Mock(spec=HookProtocol)
        mock_hook.name = "test_hook"

        registry.register(mock_hook)

        with pytest.raises(ValueError, match="already registered"):
            registry.register(mock_hook)

    def test_register_shell_hook(self):
        """Test registering a shell hook."""
        registry = HookRegistry()

        registry.register_shell(
            name="validation_hook",
            script_path="/path/to/validate.sh",
            events=[HookEvent.PRE_TOOL_CALL, HookEvent.POST_TOOL_CALL],
            priority=10,
        )

        assert "validation_hook" in registry._shell_hooks
        shell_hook = registry._shell_hooks["validation_hook"]
        assert isinstance(shell_hook, ShellHook)
        assert shell_hook.name == "validation_hook"
        assert shell_hook.script_path == "/path/to/validate.sh"
        assert shell_hook.events == [HookEvent.PRE_TOOL_CALL, HookEvent.POST_TOOL_CALL]
        assert shell_hook.priority == 10

    def test_register_duplicate_shell_hook_raises(self):
        """Test that registering duplicate shell hook raises ValueError."""
        registry = HookRegistry()

        registry.register_shell(
            name="test_hook",
            script_path="/test.sh",
            events=[HookEvent.PRE_TOOL_CALL],
        )

        with pytest.raises(ValueError, match="already registered"):
            registry.register_shell(
                name="test_hook",
                script_path="/other.sh",
                events=[HookEvent.POST_TOOL_CALL],
            )

    def test_unregister_python_hook(self):
        """Test unregistering a Python hook."""
        registry = HookRegistry()

        mock_hook = Mock(spec=HookProtocol)
        mock_hook.name = "test_hook"
        registry.register(mock_hook)

        registry.unregister("test_hook")
        assert "test_hook" not in registry._python_hooks

    def test_unregister_shell_hook(self):
        """Test unregistering a shell hook."""
        registry = HookRegistry()

        registry.register_shell(
            name="test_hook",
            script_path="/test.sh",
            events=[HookEvent.PRE_TOOL_CALL],
        )

        registry.unregister("test_hook")
        assert "test_hook" not in registry._shell_hooks

    def test_unregister_nonexistent_hook_raises(self):
        """Test that unregistering nonexistent hook raises ValueError."""
        registry = HookRegistry()

        with pytest.raises(ValueError, match="No hook with name"):
            registry.unregister("nonexistent")

    def test_get_hooks_for_event(self):
        """Test getting hooks for a specific event."""
        registry = HookRegistry()

        mock_hook1 = Mock(spec=HookProtocol)
        mock_hook1.name = "hook1"
        mock_hook1.events = [HookEvent.PRE_TOOL_CALL]
        mock_hook1.priority = 50

        mock_hook2 = Mock(spec=HookProtocol)
        mock_hook2.name = "hook2"
        mock_hook2.events = [HookEvent.PRE_TOOL_CALL, HookEvent.POST_TOOL_CALL]
        mock_hook2.priority = 10

        mock_hook3 = Mock(spec=HookProtocol)
        mock_hook3.name = "hook3"
        mock_hook3.events = [HookEvent.SESSION_START]
        mock_hook3.priority = 30

        registry.register(mock_hook1)
        registry.register(mock_hook2)
        registry.register(mock_hook3)

        hooks = registry.get_hooks(HookEvent.PRE_TOOL_CALL)

        assert len(hooks) == 2
        # Should be sorted by priority (lower first)
        assert hooks[0] == mock_hook2  # priority 10
        assert hooks[1] == mock_hook1  # priority 50

    def test_get_shell_hooks_for_event(self):
        """Test getting shell hooks for a specific event."""
        registry = HookRegistry()

        registry.register_shell(
            name="hook1",
            script_path="/hook1.sh",
            events=[HookEvent.PRE_TOOL_CALL],
            priority=50,
        )
        registry.register_shell(
            name="hook2",
            script_path="/hook2.sh",
            events=[HookEvent.PRE_TOOL_CALL],
            priority=10,
        )
        registry.register_shell(
            name="hook3",
            script_path="/hook3.sh",
            events=[HookEvent.POST_TOOL_CALL],
            priority=30,
        )

        hooks = registry.get_shell_hooks(HookEvent.PRE_TOOL_CALL)

        assert len(hooks) == 2
        # Should be sorted by priority (lower first)
        assert hooks[0].name == "hook2"  # priority 10
        assert hooks[1].name == "hook1"  # priority 50


class TestHookExecutor:
    """Test HookExecutor executing hooks."""

    @pytest.mark.asyncio
    async def test_execute_python_hook(self):
        """Test executing a Python hook."""
        registry = HookRegistry()
        executor = HookExecutor(registry)

        # Create a mock hook that returns success
        mock_hook = AsyncMock(spec=HookProtocol)
        mock_hook.name = "test_hook"
        mock_hook.events = [HookEvent.PRE_TOOL_CALL]
        mock_hook.priority = 50
        mock_hook.execute.return_value = {"continue_execution": True, "message": "Hook executed"}

        registry.register(mock_hook)

        context = HookContext(
            event=HookEvent.PRE_TOOL_CALL,
            data={"tool": "test"},
            session_state={},
        )

        result = await executor.execute(context)

        assert result["continue_execution"] is True
        mock_hook.execute.assert_called_once_with(context)

    @pytest.mark.asyncio
    async def test_execute_hook_that_blocks(self):
        """Test hook that blocks execution."""
        registry = HookRegistry()
        executor = HookExecutor(registry)

        mock_hook = AsyncMock(spec=HookProtocol)
        mock_hook.name = "blocking_hook"
        mock_hook.events = [HookEvent.PRE_TOOL_CALL]
        mock_hook.priority = 50
        mock_hook.execute.return_value = {
            "continue_execution": False,
            "error": "Tool not allowed",
        }

        registry.register(mock_hook)

        context = HookContext(
            event=HookEvent.PRE_TOOL_CALL,
            data={"tool": "dangerous_tool"},
            session_state={},
        )

        result = await executor.execute(context)

        assert result["continue_execution"] is False
        assert result["error"] == "Tool not allowed"

    @pytest.mark.asyncio
    async def test_execute_hook_that_modifies_data(self):
        """Test hook that modifies data."""
        registry = HookRegistry()
        executor = HookExecutor(registry)

        mock_hook = AsyncMock(spec=HookProtocol)
        mock_hook.name = "modifier_hook"
        mock_hook.events = [HookEvent.PRE_TOOL_CALL]
        mock_hook.priority = 50
        mock_hook.execute.return_value = {
            "continue_execution": True,
            "modified_data": {"tool": "test", "args": {"modified": True}},
        }

        registry.register(mock_hook)

        context = HookContext(
            event=HookEvent.PRE_TOOL_CALL,
            data={"tool": "test", "args": {}},
            session_state={},
        )

        result = await executor.execute(context)

        assert result["continue_execution"] is True
        assert result["modified_data"]["args"]["modified"] is True

    @pytest.mark.asyncio
    async def test_execute_multiple_hooks_in_priority_order(self):
        """Test that multiple hooks execute in priority order."""
        registry = HookRegistry()
        executor = HookExecutor(registry)

        execution_order = []

        async def create_hook(name: str, priority: int):
            mock_hook = AsyncMock(spec=HookProtocol)
            mock_hook.name = name
            mock_hook.events = [HookEvent.PRE_TOOL_CALL]
            mock_hook.priority = priority

            async def execute_fn(ctx):
                execution_order.append(name)
                return {"continue_execution": True}

            mock_hook.execute = execute_fn
            return mock_hook

        hook1 = await create_hook("hook1", 50)
        hook2 = await create_hook("hook2", 10)
        hook3 = await create_hook("hook3", 30)

        registry.register(hook1)
        registry.register(hook2)
        registry.register(hook3)

        context = HookContext(
            event=HookEvent.PRE_TOOL_CALL,
            data={},
            session_state={},
        )

        await executor.execute(context)

        # Should execute in order: hook2 (10), hook3 (30), hook1 (50)
        assert execution_order == ["hook2", "hook3", "hook1"]

    @pytest.mark.asyncio
    async def test_execute_hook_error_handling(self):
        """Test that hook errors are handled gracefully."""
        registry = HookRegistry()
        executor = HookExecutor(registry)

        mock_hook = AsyncMock(spec=HookProtocol)
        mock_hook.name = "failing_hook"
        mock_hook.events = [HookEvent.PRE_TOOL_CALL]
        mock_hook.priority = 50
        mock_hook.execute.side_effect = Exception("Hook failed!")

        registry.register(mock_hook)

        context = HookContext(
            event=HookEvent.PRE_TOOL_CALL,
            data={},
            session_state={},
        )

        result = await executor.execute(context)

        assert result["continue_execution"] is False
        assert "Hook failed!" in result["error"]

    @pytest.mark.asyncio
    @patch("asyncio.create_subprocess_exec")
    async def test_execute_shell_hook(self, mock_subprocess):
        """Test executing a shell hook."""
        registry = HookRegistry()
        executor = HookExecutor(registry)

        # Mock the subprocess
        mock_process = AsyncMock()
        mock_process.returncode = 0
        mock_process.communicate.return_value = (
            json.dumps({"continue_execution": True, "message": "Shell hook executed"}).encode(),
            b"",
        )
        mock_subprocess.return_value = mock_process

        registry.register_shell(
            name="test_shell_hook",
            script_path="/test.sh",
            events=[HookEvent.PRE_TOOL_CALL],
        )

        context = HookContext(
            event=HookEvent.PRE_TOOL_CALL,
            data={"test": "data"},
            session_state={},
        )

        result = await executor.execute(context)

        assert result["continue_execution"] is True
        mock_subprocess.assert_called_once()

    @pytest.mark.asyncio
    @patch("asyncio.create_subprocess_exec")
    async def test_execute_shell_hook_error(self, mock_subprocess):
        """Test shell hook that returns error."""
        registry = HookRegistry()
        executor = HookExecutor(registry)

        # Mock the subprocess to fail
        mock_process = AsyncMock()
        mock_process.returncode = 1
        mock_process.communicate.return_value = (b"", b"Script error")
        mock_subprocess.return_value = mock_process

        registry.register_shell(
            name="failing_shell_hook",
            script_path="/fail.sh",
            events=[HookEvent.PRE_TOOL_CALL],
        )

        context = HookContext(
            event=HookEvent.PRE_TOOL_CALL,
            data={},
            session_state={},
        )

        result = await executor.execute(context)

        assert result["continue_execution"] is False
        assert "exited with code 1" in result["error"]


class TestHooksMiddleware:
    """Test HooksMiddleware integration."""

    def test_middleware_initialization(self):
        """Test creating HooksMiddleware."""
        middleware = HooksMiddleware()

        assert middleware.registry is not None
        assert middleware.executor is not None
        assert middleware.assistant_id is None

    def test_middleware_with_registry(self):
        """Test creating HooksMiddleware with custom registry."""
        registry = HookRegistry()
        middleware = HooksMiddleware(registry=registry)

        assert middleware.registry == registry

    def test_middleware_with_assistant_id(self):
        """Test creating HooksMiddleware with assistant ID."""
        middleware = HooksMiddleware(assistant_id="test-assistant")

        assert middleware.assistant_id == "test-assistant"

    @pytest.mark.asyncio
    async def test_pre_tool_call(self):
        """Test pre_tool_call hook execution."""
        middleware = HooksMiddleware()

        # Create mock request
        mock_request = Mock()
        mock_request.tool_call = {"id": "call_123", "name": "read_file"}
        mock_request.tool = Mock()
        mock_request.runtime = Mock()
        mock_request.runtime.state = {}

        result = await middleware.pre_tool_call(mock_request)

        # With no hooks, should return None to continue
        assert result is None

    @pytest.mark.asyncio
    async def test_pre_tool_call_blocking(self):
        """Test pre_tool_call that blocks execution."""
        registry = HookRegistry()
        middleware = HooksMiddleware(registry=registry)

        # Add a blocking hook
        mock_hook = AsyncMock(spec=HookProtocol)
        mock_hook.name = "blocking_hook"
        mock_hook.events = [HookEvent.PRE_TOOL_CALL]
        mock_hook.priority = 50
        mock_hook.execute.return_value = {
            "continue_execution": False,
            "error": "Blocked",
        }
        registry.register(mock_hook)

        # Create mock request
        mock_request = Mock()
        mock_request.tool_call = {"id": "call_123", "name": "dangerous_tool"}
        mock_request.tool = Mock()
        mock_request.runtime = Mock()
        mock_request.runtime.state = {}

        result = await middleware.pre_tool_call(mock_request)

        # Should return a ToolMessage with error
        assert result is not None
        assert "Blocked" in result.content

    @pytest.mark.asyncio
    async def test_post_tool_call(self):
        """Test post_tool_call hook execution."""
        from langchain_core.messages import ToolMessage

        middleware = HooksMiddleware()

        # Create mock request and result
        mock_request = Mock()
        mock_request.tool_call = {"id": "call_123", "name": "read_file"}
        mock_request.tool = Mock()
        mock_request.runtime = Mock()
        mock_request.runtime.state = {}

        mock_result = ToolMessage(content="File content", tool_call_id="call_123")

        result = await middleware.post_tool_call(mock_request, mock_result)

        # With no hooks, should return original result
        assert result == mock_result

    @pytest.mark.asyncio
    async def test_awrap_tool_call(self):
        """Test awrap_tool_call integration."""
        from langchain_core.messages import ToolMessage

        middleware = HooksMiddleware()

        # Create mock request
        mock_request = Mock()
        mock_request.tool_call = {"id": "call_123", "name": "test_tool"}
        mock_request.tool = Mock()
        mock_request.runtime = Mock()
        mock_request.runtime.state = {}

        # Create mock handler
        async def mock_handler(req):
            return ToolMessage(content="Success", tool_call_id="call_123")

        result = await middleware.awrap_tool_call(mock_request, mock_handler)

        assert result.content == "Success"

    def test_wrap_tool_call_not_implemented(self):
        """Test that sync wrap_tool_call raises NotImplementedError."""
        middleware = HooksMiddleware()

        mock_request = Mock()

        def mock_handler(req):
            return Mock()

        with pytest.raises(NotImplementedError, match="requires async execution"):
            middleware.wrap_tool_call(mock_request, mock_handler)
