"""Models module for LLM provider management.

This module provides a flexible, extensible system for managing
multiple LLM providers using design patterns:

- Strategy Pattern: Each provider implements its own creation strategy
- Registry Pattern: Central registration and discovery of providers
- Factory Pattern: Unified model creation interface

Usage:
    from deepagents_cli.models import create_model, get_factory

    # Simple usage (auto-select provider)
    model = create_model()

    # Specific provider
    model = create_model("xai")

    # Access factory for more control
    factory = get_factory()
    info = factory.get_provider_info()
"""

from langchain_core.language_models import BaseChatModel

from deepagents_cli.models.base import ModelProvider, ProviderConfig
from deepagents_cli.models.factory import ModelFactory
from deepagents_cli.models.providers import (
    AnthropicProvider,
    GoogleProvider,
    OpenAIProvider,
    XAIProvider,
)
from deepagents_cli.models.registry import ProviderRegistry


def _initialize_registry() -> ProviderRegistry:
    """Initialize and populate the global provider registry."""
    registry = ProviderRegistry()
    registry.register(OpenAIProvider())
    registry.register(AnthropicProvider())
    registry.register(GoogleProvider())
    registry.register(XAIProvider())
    return registry


# Initialize global registry with all providers
_registry = _initialize_registry()

# Global factory instance
_factory = ModelFactory(_registry)


def get_registry() -> ProviderRegistry:
    """Get the global provider registry."""
    return _registry


def get_factory() -> ModelFactory:
    """Get the global model factory."""
    return _factory


def create_model(provider_name: str | None = None) -> BaseChatModel:
    """Create a model instance.

    Convenience function that delegates to the global factory.

    Args:
        provider_name: Specific provider to use. If None, auto-selects.

    Returns:
        Configured BaseChatModel instance.
    """
    from deepagents_cli.config import console

    factory = get_factory()

    if provider_name is None:
        provider = factory.get_active_provider()
    else:
        provider = factory.registry.get_by_name(provider_name)

    if provider:
        console.print(f"[dim]Using {provider.name} model: {provider.get_model_name()}[/dim]")

    return factory.create(provider_name)


__all__ = [
    # Core classes
    "ModelProvider",
    "ProviderConfig",
    "ProviderRegistry",
    "ModelFactory",
    # Providers
    "OpenAIProvider",
    "AnthropicProvider",
    "GoogleProvider",
    "XAIProvider",
    # Functions
    "get_registry",
    "get_factory",
    "create_model",
]
