"""Tests for providers."""

import pytest
from unittest.mock import patch, MagicMock


def test_anthropic_raises_on_missing_key():
    with patch.dict("os.environ", {}, clear=True):
        from bot.providers.anthropic import AnthropicProvider
        with pytest.raises(EnvironmentError, match="Missing API key"):
            AnthropicProvider({"model": "claude-haiku-4-5", "api_key_env": "ANTHROPIC_API_KEY"})


def test_openai_raises_on_missing_key():
    with patch.dict("os.environ", {}, clear=True):
        from bot.providers.openai import OpenAIProvider
        with pytest.raises(EnvironmentError, match="Missing API key"):
            OpenAIProvider({"model": "gpt-4o-mini", "api_key_env": "OPENAI_API_KEY"})


def test_anthropic_initialises_with_key():
    with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
        with patch("anthropic.Anthropic"):
            from bot.providers.anthropic import AnthropicProvider
            provider = AnthropicProvider({"model": "claude-haiku-4-5", "api_key_env": "ANTHROPIC_API_KEY"})
            assert provider.model == "claude-haiku-4-5"


def test_openai_initialises_with_key():
    with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):
        with patch("openai.OpenAI"):
            from bot.providers.openai import OpenAIProvider
            provider = OpenAIProvider({"model": "gpt-4o-mini", "api_key_env": "OPENAI_API_KEY"})
            assert provider.model == "gpt-4o-mini"


def test_openai_uses_base_url_if_provided():
    with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):
        with patch("openai.OpenAI") as mock_openai:
            from bot.providers.openai import OpenAIProvider
            OpenAIProvider({
                "model": "gpt-4o-mini",
                "api_key_env": "OPENAI_API_KEY",
                "base_url": "http://localhost:8080/v1"
            })
            call_kwargs = mock_openai.call_args[1]
            assert call_kwargs["base_url"] == "http://localhost:8080/v1"


def test_ollama_default_base_url():
    from bot.providers.ollama import OllamaProvider
    provider = OllamaProvider({"model": "llama3"})
    assert provider.base_url == "http://localhost:11434"
    assert provider.model == "llama3"


def test_ollama_custom_base_url():
    from bot.providers.ollama import OllamaProvider
    provider = OllamaProvider({"model": "llama3", "base_url": "http://192.168.1.10:11434"})
    assert provider.base_url == "http://192.168.1.10:11434"


def test_llamacpp_uses_dummy_key():
    with patch("openai.OpenAI"):
        from bot.providers.llamacpp import LlamaCppProvider
        provider = LlamaCppProvider({})
        assert provider.model == "local"


def test_get_provider_returns_correct_class():
    with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
        with patch("anthropic.Anthropic"):
            from bot.providers import get_provider
            provider = get_provider("anthropic", {
                "model": "claude-haiku-4-5",
                "api_key_env": "ANTHROPIC_API_KEY"
            })
            from bot.providers.anthropic import AnthropicProvider
            assert isinstance(provider, AnthropicProvider)


def test_get_provider_raises_on_unknown():
    from bot.providers import get_provider
    with pytest.raises(ValueError, match="Unknown provider"):
        get_provider("nonexistent", {})