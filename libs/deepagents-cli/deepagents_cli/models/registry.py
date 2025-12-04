"""Provider registry for managing LLM providers."""

from collections.abc import Iterator

from deepagents_cli.models.base import ModelProvider


class ProviderRegistry:
    """Registry for LLM providers (Registry Pattern).

    Maintains a collection of available providers and provides
    methods for discovery and retrieval.

    Usage:
        registry = ProviderRegistry()
        registry.register(OpenAIProvider())
        registry.register(AnthropicProvider())

        # Get first available provider
        provider = registry.get_first_available()

        # Get specific provider
        provider = registry.get_by_name("openai")
    """

    _instance: "ProviderRegistry | None" = None

    def __new__(cls) -> "ProviderRegistry":
        """Singleton pattern for global registry."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._providers = {}
        return cls._instance

    def __init__(self) -> None:
        """Initialize registry."""
        # Avoid re-initializing on subsequent calls
        if not hasattr(self, "_providers"):
            self._providers: dict[str, ModelProvider] = {}

    def register(self, provider: ModelProvider) -> "ProviderRegistry":
        """Register a provider.

        Args:
            provider: ModelProvider instance to register.

        Returns:
            Self for method chaining.
        """
        self._providers[provider.name.lower()] = provider
        return self

    def unregister(self, name: str) -> bool:
        """Unregister a provider by name.

        Args:
            name: Provider name to unregister.

        Returns:
            True if provider was removed, False if not found.
        """
        name_lower = name.lower()
        if name_lower in self._providers:
            del self._providers[name_lower]
            return True
        return False

    def get_by_name(self, name: str) -> ModelProvider | None:
        """Get a provider by name.

        Args:
            name: Provider name (case-insensitive).

        Returns:
            ModelProvider if found, None otherwise.
        """
        return self._providers.get(name.lower())

    def get_all(self) -> list[ModelProvider]:
        """Get all registered providers sorted by priority."""
        return sorted(self._providers.values(), key=lambda p: p.priority)

    def get_available(self) -> list[ModelProvider]:
        """Get all providers that have API keys configured."""
        return [p for p in self.get_all() if p.is_available()]

    def get_first_available(self) -> ModelProvider | None:
        """Get the first available provider by priority.

        Returns:
            First available ModelProvider, or None if none available.
        """
        available = self.get_available()
        return available[0] if available else None

    def __iter__(self) -> Iterator[ModelProvider]:
        """Iterate over all providers."""
        return iter(self.get_all())

    def __len__(self) -> int:
        """Return number of registered providers."""
        return len(self._providers)

    def __contains__(self, name: str) -> bool:
        """Check if a provider is registered."""
        return name.lower() in self._providers

    @classmethod
    def reset(cls) -> None:
        """Reset the singleton instance (for testing)."""
        cls._instance = None
