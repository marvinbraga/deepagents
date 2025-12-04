"""Tests for deepagents_cli.models.registry."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from deepagents_cli.models.base import ModelProvider, ProviderConfig
from deepagents_cli.models.registry import ProviderRegistry

if TYPE_CHECKING:
    from langchain_core.language_models import BaseChatModel


class MockProvider(ModelProvider):
    """Mock provider for testing."""

    def __init__(
        self,
        name: str,
        priority: int = 100,
        available: bool = False,  # noqa: FBT001, FBT002
    ) -> None:
        """Initialize mock provider."""
        self._name = name
        self._priority = priority
        self._available = available

    @property
    def name(self) -> str:
        return self._name

    @property
    def env_key(self) -> str:
        return f"{self._name.upper()}_API_KEY"

    @property
    def model_env_key(self) -> str:
        return f"{self._name.upper()}_MODEL"

    @property
    def default_model(self) -> str:
        return "default"

    @property
    def priority(self) -> int:
        return self._priority

    def is_available(self) -> bool:
        return self._available

    def create_model(self, config: ProviderConfig) -> BaseChatModel:  # type: ignore[return-value]
        """Create mock model."""
        _ = config  # Unused in mock
        return f"Model({self._name})"  # type: ignore[return-value]


class TestProviderRegistry:
    """Tests for ProviderRegistry."""

    @pytest.fixture(autouse=True)
    def reset_registry(self):
        """Reset singleton before each test."""
        ProviderRegistry.reset()
        yield
        ProviderRegistry.reset()

    def test_singleton_pattern(self):
        reg1 = ProviderRegistry()
        reg2 = ProviderRegistry()
        assert reg1 is reg2

    def test_register_provider(self):
        registry = ProviderRegistry()
        provider = MockProvider("Test")
        registry.register(provider)
        assert "test" in registry

    def test_register_returns_self_for_chaining(self):
        registry = ProviderRegistry()
        result = registry.register(MockProvider("A"))
        assert result is registry

    def test_get_by_name_case_insensitive(self):
        registry = ProviderRegistry()
        provider = MockProvider("MyProvider")
        registry.register(provider)
        assert registry.get_by_name("myprovider") is provider
        assert registry.get_by_name("MYPROVIDER") is provider
        assert registry.get_by_name("MyProvider") is provider

    def test_get_by_name_not_found(self):
        registry = ProviderRegistry()
        assert registry.get_by_name("nonexistent") is None

    def test_get_all_sorted_by_priority(self):
        registry = ProviderRegistry()
        registry.register(MockProvider("Low", priority=50))
        registry.register(MockProvider("High", priority=10))
        registry.register(MockProvider("Mid", priority=30))

        all_providers = registry.get_all()
        priorities = [p.priority for p in all_providers]
        assert priorities == [10, 30, 50]

    def test_get_available(self):
        registry = ProviderRegistry()
        registry.register(MockProvider("Available", available=True))
        registry.register(MockProvider("Unavailable", available=False))

        available = registry.get_available()
        assert len(available) == 1
        assert available[0].name == "Available"

    def test_get_first_available(self):
        registry = ProviderRegistry()
        registry.register(MockProvider("Second", priority=20, available=True))
        registry.register(MockProvider("First", priority=10, available=True))

        first = registry.get_first_available()
        assert first is not None
        assert first.name == "First"

    def test_get_first_available_none(self):
        registry = ProviderRegistry()
        registry.register(MockProvider("Unavailable", available=False))
        assert registry.get_first_available() is None

    def test_unregister(self):
        registry = ProviderRegistry()
        registry.register(MockProvider("ToRemove"))
        assert registry.unregister("toremove") is True
        assert "toremove" not in registry

    def test_unregister_nonexistent(self):
        registry = ProviderRegistry()
        assert registry.unregister("nonexistent") is False

    def test_len(self):
        registry = ProviderRegistry()
        assert len(registry) == 0
        registry.register(MockProvider("A"))
        registry.register(MockProvider("B"))
        assert len(registry) == 2

    def test_iter(self):
        registry = ProviderRegistry()
        registry.register(MockProvider("A", priority=20))
        registry.register(MockProvider("B", priority=10))

        names = [p.name for p in registry]
        assert names == ["B", "A"]  # Sorted by priority
