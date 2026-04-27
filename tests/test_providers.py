"""Tests for providers."""

from unittest.mock import patch

import pytest


def test_anthropic_raises_on_missing_key():
    with patch.dict("os.environ", {}, clear=True):
        from bot.providers.anthropic import AnthropicProvider

        with pytest.raises(OSError, match="Missing API key"):
            AnthropicProvider(
                {"model": "claude-haiku-4-5", "api_key_env": "ANTHROPIC_API_KEY"}
            )


def test_openai_raises_on_missing_key():
    with patch.dict("os.environ", {}, clear=True):
        from bot.providers.openai import OpenAIProvider

        with pytest.raises(OSError, match="Missing API key"):
            OpenAIProvider({"model": "gpt-4o-mini", "api_key_env": "OPENAI_API_KEY"})


def test_anthropic_initialises_with_key():
    with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
        with patch("anthropic.Anthropic"):
            from bot.providers.anthropic import AnthropicProvider

            provider = AnthropicProvider(
                {"model": "claude-haiku-4-5", "api_key_env": "ANTHROPIC_API_KEY"}
            )
            assert provider.model == "claude-haiku-4-5"


def test_openai_initialises_with_key():
    with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):
        with patch("openai.OpenAI"):
            from bot.providers.openai import OpenAIProvider

            provider = OpenAIProvider(
                {"model": "gpt-4o-mini", "api_key_env": "OPENAI_API_KEY"}
            )
            assert provider.model == "gpt-4o-mini"


def test_openai_uses_base_url_if_provided():
    with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):
        with patch("openai.OpenAI") as mock_openai:
            from bot.providers.openai import OpenAIProvider

            OpenAIProvider(
                {
                    "model": "gpt-4o-mini",
                    "api_key_env": "OPENAI_API_KEY",
                    "base_url": "http://localhost:8080/v1",
                }
            )
            call_kwargs = mock_openai.call_args[1]
            assert call_kwargs["base_url"] == "http://localhost:8080/v1"


def test_ollama_default_base_url():
    from bot.providers.ollama import OllamaProvider

    provider = OllamaProvider({"model": "llama3"})
    assert provider.base_url == "http://localhost:11434"
    assert provider.model == "llama3"


def test_ollama_custom_base_url():
    from bot.providers.ollama import OllamaProvider

    provider = OllamaProvider(
        {"model": "llama3", "base_url": "http://192.168.1.10:11434"}
    )
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

            provider = get_provider(
                "anthropic",
                {"model": "claude-haiku-4-5", "api_key_env": "ANTHROPIC_API_KEY"},
            )
            from bot.providers.anthropic import AnthropicProvider

            assert isinstance(provider, AnthropicProvider)


def test_get_provider_raises_on_unknown():
    from bot.providers import get_provider

    with pytest.raises(ValueError, match="Unknown provider"):
        get_provider("nonexistent", {})


# --- Usage capture tests ---


def test_anthropic_stream_chat_sets_last_usage():
    from unittest.mock import MagicMock, patch

    with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
        with patch("anthropic.Anthropic"):
            from bot.providers.anthropic import AnthropicProvider

            provider = AnthropicProvider(
                {"model": "claude-haiku-4-5", "api_key_env": "ANTHROPIC_API_KEY"}
            )
            mock_stream = MagicMock()
            mock_stream.text_stream = iter(["hello ", "world"])
            mock_stream.get_final_message.return_value.usage.input_tokens = 10
            mock_stream.get_final_message.return_value.usage.output_tokens = 20
            mock_stream.__enter__ = lambda s: mock_stream
            mock_stream.__exit__ = MagicMock(return_value=False)
            provider.client.messages.stream.return_value = mock_stream

            chunks = list(provider.stream_chat([{"role": "user", "content": "hi"}], "system"))
            assert chunks == ["hello ", "world"]
            assert provider.last_usage == {"input_tokens": 10, "output_tokens": 20}


def test_ollama_stream_chat_sets_last_usage():
    import json
    from unittest.mock import MagicMock, patch

    from bot.providers.ollama import OllamaProvider

    provider = OllamaProvider({"model": "llama3"})
    lines = [
        json.dumps({"message": {"content": "hi"}, "done": False}).encode(),
        json.dumps({"message": {"content": ""}, "done": True, "prompt_eval_count": 5, "eval_count": 15}).encode(),
    ]
    mock_resp = MagicMock()
    mock_resp.__enter__ = lambda s: iter(lines)
    mock_resp.__exit__ = MagicMock(return_value=False)

    with patch("bot.providers.ollama.request.urlopen", return_value=mock_resp):
        chunks = list(provider.stream_chat([{"role": "user", "content": "hi"}], "system"))
    assert "hi" in chunks
    assert provider.last_usage == {"input_tokens": 5, "output_tokens": 15}


def test_openai_stream_chat_sets_last_usage():
    from unittest.mock import MagicMock, patch

    with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):
        with patch("openai.OpenAI"):
            from bot.providers.openai import OpenAIProvider

            provider = OpenAIProvider(
                {"model": "gpt-4o-mini", "api_key_env": "OPENAI_API_KEY"}
            )
            chunk1 = MagicMock()
            chunk1.choices = [MagicMock()]
            chunk1.choices[0].delta.content = "hello"
            chunk1.usage = None
            chunk2 = MagicMock()
            chunk2.choices = []
            chunk2.usage = MagicMock()
            chunk2.usage.prompt_tokens = 8
            chunk2.usage.completion_tokens = 12
            provider.client.chat.completions.create.return_value = iter([chunk1, chunk2])

            chunks = list(provider.stream_chat([{"role": "user", "content": "hi"}], "system"))
            assert chunks == ["hello"]
            assert provider.last_usage == {"input_tokens": 8, "output_tokens": 12}
