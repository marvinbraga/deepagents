"""Tests for deepagents_cli.models.base."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING
from unittest.mock import patch

from deepagents_cli.models.base import ModelProvider, ProviderConfig

if TYPE_CHECKING:
    from langchain_core.language_models import BaseChatModel


class TestProviderConfig:
    """Tests for ProviderConfig dataclass."""

    def test_create_config(self):
        config = ProviderConfig(api_key="test-key", model_name="test-model")
        assert config.api_key == "test-key"
        assert config.model_name == "test-model"
        assert config.extra_params == {}

    def test_config_with_extra_params(self):
        config = ProviderConfig(
            api_key="key",
            model_name="model",
            extra_params={"temperature": 0.7},
        )
        assert config.extra_params == {"temperature": 0.7}


class ConcreteProvider(ModelProvider):
    """Concrete provider for testing."""

    @property
    def name(self) -> str:
        return "TestProvider"

    @property
    def env_key(self) -> str:
        return "TEST_API_KEY"

    @property
    def model_env_key(self) -> str:
        return "TEST_MODEL"

    @property
    def default_model(self) -> str:
        return "test-default"

    def create_model(self, config: ProviderConfig) -> BaseChatModel:  # type: ignore[return-value]
        """Create mock model."""
        return f"MockModel({config.model_name})"  # type: ignore[return-value]


class TestModelProvider:
    """Tests for ModelProvider ABC."""

    def test_default_priority(self):
        provider = ConcreteProvider()
        assert provider.priority == 100

    def test_is_available_without_key(self):
        provider = ConcreteProvider()
        with patch.dict(os.environ, {}, clear=True):
            assert provider.is_available() is False

    def test_is_available_with_key(self):
        provider = ConcreteProvider()
        with patch.dict(os.environ, {"TEST_API_KEY": "key"}, clear=True):
            assert provider.is_available() is True

    def test_get_api_key(self):
        provider = ConcreteProvider()
        with patch.dict(os.environ, {"TEST_API_KEY": "my-secret-key"}, clear=True):
            assert provider.get_api_key() == "my-secret-key"

    def test_get_model_name_default(self):
        provider = ConcreteProvider()
        with patch.dict(os.environ, {}, clear=True):
            assert provider.get_model_name() == "test-default"

    def test_get_model_name_from_env(self):
        provider = ConcreteProvider()
        with patch.dict(os.environ, {"TEST_MODEL": "custom-model"}, clear=True):
            assert provider.get_model_name() == "custom-model"

    def test_get_config_without_key(self):
        provider = ConcreteProvider()
        with patch.dict(os.environ, {}, clear=True):
            assert provider.get_config() is None

    def test_get_config_with_key(self):
        provider = ConcreteProvider()
        with patch.dict(os.environ, {"TEST_API_KEY": "key"}, clear=True):
            config = provider.get_config()
            assert config is not None
            assert config.api_key == "key"
            assert config.model_name == "test-default"

    def test_build_without_key_returns_none(self):
        provider = ConcreteProvider()
        with patch.dict(os.environ, {}, clear=True):
            assert provider.build() is None

    def test_build_with_key_returns_model(self):
        provider = ConcreteProvider()
        with patch.dict(os.environ, {"TEST_API_KEY": "key"}, clear=True):
            model = provider.build()
            assert model == "MockModel(test-default)"
