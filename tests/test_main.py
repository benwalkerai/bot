"""Tests for the CLI."""

from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def mock_config():
    return {
        "provider": "anthropic",
        "providers": {
            "anthropic": {
                "model": "claude-haiku-4-5",
                "api_key_env": "ANTHROPIC_API_KEY",
            },
            "openai": {"model": "gpt-4o-mini", "api_key_env": "OPENAI_API_KEY"},
            "ollama": {"model": "llama3", "base_url": "http://localhost:11434"},
            "llamacpp": {"model": "local", "base_url": "http://localhost:8080"},
        },
    }


def test_help(runner):
    from bot.main import cli

    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "Usage" in result.output


def test_no_args_shows_usage(runner, mock_config):
    with patch("bot.main.load_config", return_value=mock_config):
        from bot.main import cli

        result = runner.invoke(cli, [])
        assert result.exit_code == 0
        assert "Usage" in result.output


def test_list_providers(runner, mock_config):
    with patch("bot.main.load_config", return_value=mock_config):
        from bot.main import cli

        result = runner.invoke(cli, ["--providers"])
        assert result.exit_code == 0
        assert "anthropic" in result.output
        assert "openai" in result.output
        assert "ollama" in result.output
        assert "llamacpp" in result.output


def test_set_provider(runner, mock_config):
    with (
        patch("bot.main.load_config", return_value=mock_config),
        patch("bot.main.save_config") as mock_save,
    ):
        from bot.main import cli

        result = runner.invoke(cli, ["--set-provider", "openai"])
        assert result.exit_code == 0
        assert "openai" in result.output
        mock_save.assert_called_once()


def test_set_provider_unknown(runner, mock_config):
    with patch("bot.main.load_config", return_value=mock_config):
        from bot.main import cli

        result = runner.invoke(cli, ["--set-provider", "nonexistent"])
        assert result.exit_code == 1


def test_set_model(runner, mock_config):
    with (
        patch("bot.main.load_config", return_value=mock_config),
        patch("bot.main.save_config") as mock_save,
    ):
        from bot.main import cli

        result = runner.invoke(cli, ["--set-model", "claude-opus-4-5"])
        assert result.exit_code == 0
        assert "claude-opus-4-5" in result.output
        mock_save.assert_called_once()


def test_clear_history(runner, mock_config):
    with (
        patch("bot.main.load_config", return_value=mock_config),
        patch("bot.main.clear_history") as mock_clear,
    ):
        from bot.main import cli

        result = runner.invoke(cli, ["--clear"])
        assert result.exit_code == 0
        mock_clear.assert_called_once_with("anthropic")


def test_show_history_empty(runner, mock_config):
    with (
        patch("bot.main.load_config", return_value=mock_config),
        patch("bot.main.load_history", return_value=[]),
    ):
        from bot.main import cli

        result = runner.invoke(cli, ["--history"])
        assert result.exit_code == 0
        assert "No history" in result.output


def test_show_history_with_messages(runner, mock_config):
    history = [
        {"role": "user", "content": "hello"},
        {"role": "assistant", "content": "hi there"},
    ]
    with (
        patch("bot.main.load_config", return_value=mock_config),
        patch("bot.main.load_history", return_value=history),
    ):
        from bot.main import cli

        result = runner.invoke(cli, ["--history"])
        assert result.exit_code == 0
        assert "hello" in result.output
        assert "hi there" in result.output


def test_chat_calls_provider(runner, mock_config):
    mock_provider = MagicMock()
    mock_provider.stream_chat.return_value = iter(["hello ", "world"])
    with (
        patch("bot.main.load_config", return_value=mock_config),
        patch("bot.main.load_history", return_value=[]),
        patch("bot.main.save_history"),
        patch(
            "bot.main.get_provider_config",
            return_value=mock_config["providers"]["anthropic"],
        ),
        patch("bot.main.get_provider", return_value=mock_provider),
    ):
        from bot.main import cli

        result = runner.invoke(cli, ["say", "hello"])
        assert result.exit_code == 0
        mock_provider.stream_chat.assert_called_once()


def test_chat_saves_history(runner, mock_config):
    mock_provider = MagicMock()
    mock_provider.stream_chat.return_value = iter(["the answer"])
    with (
        patch("bot.main.load_config", return_value=mock_config),
        patch("bot.main.load_history", return_value=[]),
        patch("bot.main.save_history") as mock_save,
        patch(
            "bot.main.get_provider_config",
            return_value=mock_config["providers"]["anthropic"],
        ),
        patch("bot.main.get_provider", return_value=mock_provider),
    ):
        from bot.main import cli

        result = runner.invoke(cli, ["say", "hello"])
        assert result.exit_code == 0
        mock_save.assert_called_once()
        saved_history = mock_save.call_args[0][1]
        assert saved_history[-1]["role"] == "assistant"
        assert saved_history[-1]["content"] == "the answer"


# --- Session tests ---


def test_list_sessions_empty(runner, mock_config):
    with (
        patch("bot.main.load_config", return_value=mock_config),
        patch("bot.main.list_sessions", return_value=[]),
    ):
        from bot.main import cli

        result = runner.invoke(cli, ["--sessions"])
        assert result.exit_code == 0
        assert "No saved sessions" in result.output


def test_list_sessions_shows_names(runner, mock_config):
    import time

    sessions = [
        {"name": "myproject", "messages": 4, "modified": time.time()},
        {"name": "devwork", "messages": 2, "modified": time.time()},
    ]
    with (
        patch("bot.main.load_config", return_value=mock_config),
        patch("bot.main.list_sessions", return_value=sessions),
    ):
        from bot.main import cli

        result = runner.invoke(cli, ["--sessions"])
        assert result.exit_code == 0
        assert "myproject" in result.output
        assert "devwork" in result.output


def test_clear_session_flag(runner, mock_config):
    with (
        patch("bot.main.load_config", return_value=mock_config),
        patch("bot.main.clear_session") as mock_clear,
    ):
        from bot.main import cli

        result = runner.invoke(cli, ["--clear-session", "myproject"])
        assert result.exit_code == 0
        assert "myproject" in result.output
        mock_clear.assert_called_once_with("myproject")


def test_chat_with_session_loads_session(runner, mock_config):
    mock_provider = MagicMock()
    mock_provider.stream_chat.return_value = iter(["response"])
    with (
        patch("bot.main.load_config", return_value=mock_config),
        patch("bot.main.load_session", return_value=[]) as mock_load,
        patch("bot.main.save_session"),
        patch(
            "bot.main.get_provider_config",
            return_value=mock_config["providers"]["anthropic"],
        ),
        patch("bot.main.get_provider", return_value=mock_provider),
    ):
        from bot.main import cli

        result = runner.invoke(cli, ["--session", "myproject", "hello"])
        assert result.exit_code == 0
        mock_load.assert_called_once_with("myproject")


def test_chat_with_session_saves_session(runner, mock_config):
    mock_provider = MagicMock()
    mock_provider.stream_chat.return_value = iter(["the answer"])
    with (
        patch("bot.main.load_config", return_value=mock_config),
        patch("bot.main.load_session", return_value=[]),
        patch("bot.main.save_session") as mock_save,
        patch(
            "bot.main.get_provider_config",
            return_value=mock_config["providers"]["anthropic"],
        ),
        patch("bot.main.get_provider", return_value=mock_provider),
    ):
        from bot.main import cli

        result = runner.invoke(cli, ["--session", "myproject", "hello"])
        assert result.exit_code == 0
        mock_save.assert_called_once_with("myproject", mock_save.call_args[0][1])
        saved_history = mock_save.call_args[0][1]
        assert saved_history[-1]["role"] == "assistant"
        assert saved_history[-1]["content"] == "the answer"


def test_chat_without_session_does_not_call_save_session(runner, mock_config):
    mock_provider = MagicMock()
    mock_provider.stream_chat.return_value = iter(["response"])
    with (
        patch("bot.main.load_config", return_value=mock_config),
        patch("bot.main.load_history", return_value=[]),
        patch("bot.main.save_history"),
        patch("bot.main.save_session") as mock_save_session,
        patch(
            "bot.main.get_provider_config",
            return_value=mock_config["providers"]["anthropic"],
        ),
        patch("bot.main.get_provider", return_value=mock_provider),
    ):
        from bot.main import cli

        result = runner.invoke(cli, ["hello"])
        assert result.exit_code == 0
        mock_save_session.assert_not_called()