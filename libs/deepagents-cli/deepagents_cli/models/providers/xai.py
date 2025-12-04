"""xAI (Grok) model provider."""

from langchain_core.language_models import BaseChatModel

from deepagents_cli.models.base import ModelProvider, ProviderConfig


class XAIProvider(ModelProvider):
    """Provider for xAI Grok models.

    Uses the official langchain-xai package with ChatXAI.
    """

    @property
    def name(self) -> str:
        """Human-readable provider name."""
        return "xAI"

    @property
    def env_key(self) -> str:
        """Environment variable name for API key."""
        return "XAI_API_KEY"

    @property
    def model_env_key(self) -> str:
        """Environment variable name for model selection."""
        return "GROK_MODEL"

    @property
    def default_model(self) -> str:
        """Default model name if not specified."""
        return "grok-3-mini"

    @property
    def priority(self) -> int:
        """Priority for auto-selection (lower = higher priority)."""
        return 40

    def create_model(self, config: ProviderConfig) -> BaseChatModel:
        """Create and return the ChatXAI instance."""
        from langchain_xai import ChatXAI

        return ChatXAI(
            model=config.model_name,
            xai_api_key=config.api_key,
            **config.extra_params,
        )
