"""Google model provider."""

from langchain_core.language_models import BaseChatModel

from deepagents_cli.models.base import ModelProvider, ProviderConfig


class GoogleProvider(ModelProvider):
    """Provider for Google Gemini models."""

    @property
    def name(self) -> str:
        """Human-readable provider name."""
        return "Google"

    @property
    def env_key(self) -> str:
        """Environment variable name for API key."""
        return "GOOGLE_API_KEY"

    @property
    def model_env_key(self) -> str:
        """Environment variable name for model selection."""
        return "GOOGLE_MODEL"

    @property
    def default_model(self) -> str:
        """Default model name if not specified."""
        return "gemini-2.0-flash"

    @property
    def priority(self) -> int:
        """Priority for auto-selection (lower = higher priority)."""
        return 30

    def create_model(self, config: ProviderConfig) -> BaseChatModel:
        """Create and return the ChatGoogleGenerativeAI instance."""
        from langchain_google_genai import ChatGoogleGenerativeAI

        return ChatGoogleGenerativeAI(
            model=config.model_name,
            google_api_key=config.api_key,
            temperature=0,
            max_tokens=None,
            **config.extra_params,
        )
