"""OpenAI model provider."""

from langchain_core.language_models import BaseChatModel

from deepagents_cli.models.base import ModelProvider, ProviderConfig


class OpenAIProvider(ModelProvider):
    """Provider for OpenAI models (GPT-4, GPT-4o, etc.)."""

    @property
    def name(self) -> str:
        """Human-readable provider name."""
        return "OpenAI"

    @property
    def env_key(self) -> str:
        """Environment variable name for API key."""
        return "OPENAI_API_KEY"

    @property
    def model_env_key(self) -> str:
        """Environment variable name for model selection."""
        return "OPENAI_MODEL"

    @property
    def default_model(self) -> str:
        """Default model name if not specified."""
        return "gpt-4o-mini"

    @property
    def priority(self) -> int:
        """Priority for auto-selection (lower = higher priority)."""
        return 10

    def create_model(self, config: ProviderConfig) -> BaseChatModel:
        """Create and return the ChatOpenAI instance."""
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=config.model_name,
            api_key=config.api_key,
            **config.extra_params,
        )
