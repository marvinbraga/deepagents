"""Anthropic model provider."""

from langchain_core.language_models import BaseChatModel

from deepagents_cli.models.base import ModelProvider, ProviderConfig


class AnthropicProvider(ModelProvider):
    """Provider for Anthropic models (Claude)."""

    @property
    def name(self) -> str:
        """Human-readable provider name."""
        return "Anthropic"

    @property
    def env_key(self) -> str:
        """Environment variable name for API key."""
        return "ANTHROPIC_API_KEY"

    @property
    def model_env_key(self) -> str:
        """Environment variable name for model selection."""
        return "ANTHROPIC_MODEL"

    @property
    def default_model(self) -> str:
        """Default model name if not specified."""
        return "claude-sonnet-4-5-20250929"

    @property
    def priority(self) -> int:
        """Priority for auto-selection (lower = higher priority)."""
        return 20

    def create_model(self, config: ProviderConfig) -> BaseChatModel:
        """Create and return the ChatAnthropic instance."""
        from langchain_anthropic import ChatAnthropic

        return ChatAnthropic(
            model_name=config.model_name,
            api_key=config.api_key,
            max_tokens=20_000,
            **config.extra_params,
        )
