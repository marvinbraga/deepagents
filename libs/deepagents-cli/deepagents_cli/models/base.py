"""Base classes and interfaces for model providers."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from langchain_core.language_models import BaseChatModel


@dataclass
class ProviderConfig:
    """Configuration for a model provider."""

    api_key: str
    model_name: str
    extra_params: dict[str, Any] = field(default_factory=dict)


class ModelProvider(ABC):
    """Abstract base class for LLM providers (Strategy Pattern).

    Each provider implements its own strategy for:
    - Checking availability (API key presence)
    - Creating the appropriate ChatModel instance
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable provider name."""
        ...

    @property
    @abstractmethod
    def env_key(self) -> str:
        """Environment variable name for API key."""
        ...

    @property
    @abstractmethod
    def model_env_key(self) -> str:
        """Environment variable name for model selection."""
        ...

    @property
    @abstractmethod
    def default_model(self) -> str:
        """Default model name if not specified."""
        ...

    @property
    def priority(self) -> int:
        """Priority for auto-selection (lower = higher priority)."""
        return 100

    def is_available(self) -> bool:
        """Check if this provider is available (API key is set)."""
        import os

        return bool(os.environ.get(self.env_key))

    def get_api_key(self) -> str | None:
        """Get the API key from environment."""
        import os

        return os.environ.get(self.env_key)

    def get_model_name(self) -> str:
        """Get the model name from environment or default."""
        import os

        return os.environ.get(self.model_env_key, self.default_model)

    def get_config(self) -> ProviderConfig | None:
        """Build configuration for this provider."""
        api_key = self.get_api_key()
        if not api_key:
            return None
        return ProviderConfig(
            api_key=api_key,
            model_name=self.get_model_name(),
        )

    @abstractmethod
    def create_model(self, config: ProviderConfig) -> BaseChatModel:
        """Create and return the ChatModel instance.

        Args:
            config: Provider configuration with API key and model name.

        Returns:
            Configured BaseChatModel instance.
        """
        ...

    def build(self) -> BaseChatModel | None:
        """Template method: check availability and create model.

        Returns:
            BaseChatModel if available, None otherwise.
        """
        config = self.get_config()
        if config is None:
            return None
        return self.create_model(config)
