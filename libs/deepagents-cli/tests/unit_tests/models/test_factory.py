"""Tests for deepagents_cli.models.factory."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from deepagents_cli.models.base import ModelProvider, ProviderConfig
from deepagents_cli.models.factory import ModelFactory
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
        return "default-model"

    @property
    def priority(self) -> int:
        return self._priority

    def is_available(self) -> bool:
        return self._available

    def create_model(self, config: ProviderConfig) -> BaseChatModel:  # type: ignore[return-value]
        """Create mock model."""
        return f"Model({self._name}, {config.model_name})"  # type: ignore[return-value]

    def get_config(self) -> ProviderConfig | None:
        """Get config if available."""
        if not self._available:
            return None
        return ProviderConfig(api_key="test-key", model_name=self.default_model)


class TestModelFactory:
    """Tests for ModelFactory."""

    @pytest.fixture(autouse=True)
    def reset_registry(self):
        """Reset singleton before each test."""
        ProviderRegistry.reset()
        yield
        ProviderRegistry.reset()

    def test_create_auto_selects_first_available(self):
        registry = ProviderRegistry()
        registry.register(MockProvider("Second", priority=20, available=True))
        registry.register(MockProvider("First", priority=10, available=True))

        factory = ModelFactory(registry)
        model = factory.create()
        assert "First" in model

    def test_create_specific_provider(self):
        registry = ProviderRegistry()
        registry.register(MockProvider("Target", available=True))

        factory = ModelFactory(registry)
        model = factory.create("target")
        assert "Target" in model

    def test_create_specific_provider_not_found(self):
        registry = ProviderRegistry()
        factory = ModelFactory(registry)

        with pytest.raises(ValueError, match="not found"):
            factory.create("nonexistent")

    def test_create_specific_provider_not_available(self):
        registry = ProviderRegistry()
        registry.register(MockProvider("Unavailable", available=False))

        factory = ModelFactory(registry)
        with pytest.raises(ValueError, match="not available"):
            factory.create("unavailable")

    def test_create_no_providers_available(self):
        registry = ProviderRegistry()
        registry.register(MockProvider("Unavailable", available=False))

        factory = ModelFactory(registry)
        with pytest.raises(RuntimeError, match="No API key configured"):
            factory.create()

    def test_create_no_providers_registered(self):
        registry = ProviderRegistry()
        factory = ModelFactory(registry)

        with pytest.raises(RuntimeError, match="No model providers registered"):
            factory.create()

    def test_get_provider_info(self):
        registry = ProviderRegistry()
        registry.register(MockProvider("TestProvider", priority=10, available=True))

        factory = ModelFactory(registry)
        info = factory.get_provider_info()

        assert "TestProvider" in info
        assert info["TestProvider"]["available"] is True
        assert info["TestProvider"]["priority"] == 10

    def test_get_active_provider(self):
        registry = ProviderRegistry()
        registry.register(MockProvider("Active", priority=10, available=True))
        registry.register(MockProvider("Inactive", priority=5, available=False))

        factory = ModelFactory(registry)
        active = factory.get_active_provider()
        assert active is not None
        assert active.name == "Active"

    def test_registry_property(self):
        registry = ProviderRegistry()
        factory = ModelFactory(registry)
        assert factory.registry is registry
