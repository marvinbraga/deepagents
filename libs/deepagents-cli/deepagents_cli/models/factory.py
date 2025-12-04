"""Model factory for creating LLM instances."""

from langchain_core.language_models import BaseChatModel

from deepagents_cli.models.base import ModelProvider
from deepagents_cli.models.registry import ProviderRegistry


class ModelFactory:
    """Factory for creating LLM model instances (Factory Pattern).

    Provides a unified interface for creating models from any
    registered provider.

    Usage:
        factory = ModelFactory()

        # Auto-select first available provider
        model = factory.create()

        # Create specific provider
        model = factory.create("xai")

        # Get provider info
        info = factory.get_provider_info()
    """

    def __init__(self, registry: ProviderRegistry | None = None) -> None:
        """Initialize factory with a registry.

        Args:
            registry: Provider registry. Uses global singleton if None.
        """
        self._registry = registry or ProviderRegistry()

    @property
    def registry(self) -> ProviderRegistry:
        """Get the provider registry."""
        return self._registry

    def create(self, provider_name: str | None = None) -> BaseChatModel:
        """Create a model instance.

        Args:
            provider_name: Specific provider to use. If None, uses
                          first available by priority.

        Returns:
            Configured BaseChatModel instance.

        Raises:
            ValueError: If specified provider not found or unavailable.
            RuntimeError: If no providers are available.
        """
        if provider_name:
            return self._create_specific(provider_name)
        return self._create_auto()

    def _create_specific(self, provider_name: str) -> BaseChatModel:
        """Create model from a specific provider."""
        provider = self._registry.get_by_name(provider_name)

        if provider is None:
            available = [p.name for p in self._registry.get_all()]
            msg = (
                f"Provider '{provider_name}' not found. Available: {', '.join(available) or 'none'}"
            )
            raise ValueError(msg)

        if not provider.is_available():
            msg = (
                f"Provider '{provider_name}' is not available. "
                f"Please set {provider.env_key} environment variable."
            )
            raise ValueError(msg)

        model = provider.build()
        if model is None:
            msg = f"Failed to create model from provider '{provider_name}'"
            raise RuntimeError(msg)

        return model

    def _create_auto(self) -> BaseChatModel:
        """Auto-select and create model from first available provider."""
        provider = self._registry.get_first_available()

        if provider is None:
            self._raise_no_provider_error()

        model = provider.build()
        if model is None:
            msg = f"Failed to create model from provider '{provider.name}'"
            raise RuntimeError(msg)

        return model

    def _raise_no_provider_error(self) -> None:
        """Raise error with helpful message about missing API keys."""
        all_providers = self._registry.get_all()

        if not all_providers:
            msg = "No model providers registered. Please ensure providers are properly initialized."
            raise RuntimeError(msg)

        env_vars = [f"  - {p.env_key} (for {p.name})" for p in all_providers]

        msg = (
            "No API key configured.\n\n"
            "Please set one of the following environment variables:\n"
            + "\n".join(env_vars)
            + "\n\nExample:\n"
            "  export XAI_API_KEY=your_api_key_here\n\n"
            "Or add it to your .env file."
        )
        raise RuntimeError(msg)

    def get_provider_info(self) -> dict[str, dict]:
        """Get information about all registered providers.

        Returns:
            Dict mapping provider names to their info.
        """
        return {
            p.name: {
                "available": p.is_available(),
                "env_key": p.env_key,
                "model_env_key": p.model_env_key,
                "default_model": p.default_model,
                "current_model": p.get_model_name() if p.is_available() else None,
                "priority": p.priority,
            }
            for p in self._registry.get_all()
        }

    def get_active_provider(self) -> ModelProvider | None:
        """Get the provider that would be used for auto-selection."""
        return self._registry.get_first_available()
