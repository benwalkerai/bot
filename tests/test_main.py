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
    mock_provider.last_usage = None
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
    mock_provider.last_usage = None
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


def test_clear_session_rejects_invalid_name(runner, mock_config):
    with patch("bot.main.load_config", return_value=mock_config):
        from bot.main import cli

        result = runner.invoke(cli, ["--clear-session", "../bad"])
        assert result.exit_code == 1
        assert "Invalid session name" in result.output


def test_chat_with_session_loads_session(runner, mock_config):
    mock_provider = MagicMock()
    mock_provider.stream_chat.return_value = iter(["response"])
    mock_provider.last_usage = None
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
    mock_provider.last_usage = None
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
        mock_save.assert_called_once_with("myproject", mock_save.call_args[0][1], "anthropic")
        saved_history = mock_save.call_args[0][1]
        assert saved_history[-1]["role"] == "assistant"
        assert saved_history[-1]["content"] == "the answer"


def test_chat_with_session_rejects_invalid_name(runner, mock_config):
    with patch("bot.main.load_config", return_value=mock_config):
        from bot.main import cli

        result = runner.invoke(cli, ["--session", "../bad", "hello"])
        assert result.exit_code == 1
        assert "Invalid session name" in result.output


def test_chat_without_session_does_not_call_save_session(runner, mock_config):
    mock_provider = MagicMock()
    mock_provider.stream_chat.return_value = iter(["response"])
    mock_provider.last_usage = None
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


# --- System prompt tests ---


def test_system_prompt_override_is_used(runner, mock_config):
    mock_provider = MagicMock()
    mock_provider.stream_chat.return_value = iter(["response"])
    mock_provider.last_usage = None
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

        result = runner.invoke(cli, ["--system", "You are a Python expert", "explain decorators"])
        assert result.exit_code == 0
        _, called_system = mock_provider.stream_chat.call_args[0]
        assert called_system == "You are a Python expert"


def test_default_system_prompt_used_when_no_override(runner, mock_config):
    from bot.main import SYSTEM_PROMPT

    mock_provider = MagicMock()
    mock_provider.stream_chat.return_value = iter(["response"])
    mock_provider.last_usage = None
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

        result = runner.invoke(cli, ["hello"])
        assert result.exit_code == 0
        _, called_system = mock_provider.stream_chat.call_args[0]
        assert called_system == SYSTEM_PROMPT


# --- Interactive mode tests ---


def test_chat_mode_multiple_turns_saves_history_each_turn(runner, mock_config):
    mock_provider = MagicMock()
    mock_provider.stream_chat.side_effect = [iter(["first reply"]), iter(["second reply"])]
    mock_provider.last_usage = None
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

        result = runner.invoke(cli, ["--chat"], input="hello\nworld\n/exit\n")
        assert result.exit_code == 0
        assert mock_provider.stream_chat.call_count == 2
        assert mock_save.call_count == 2


def test_chat_mode_with_session_uses_save_session(runner, mock_config):
    mock_provider = MagicMock()
    mock_provider.stream_chat.return_value = iter(["response"])
    mock_provider.last_usage = None
    with (
        patch("bot.main.load_config", return_value=mock_config),
        patch("bot.main.load_session", return_value=[]) as mock_load,
        patch("bot.main.save_session") as mock_save,
        patch(
            "bot.main.get_provider_config",
            return_value=mock_config["providers"]["anthropic"],
        ),
        patch("bot.main.get_provider", return_value=mock_provider),
    ):
        from bot.main import cli

        result = runner.invoke(
            cli,
            ["--session", "myproject", "--chat", "hello"],
            input="/exit\n",
        )
        assert result.exit_code == 0
        mock_load.assert_called_once_with("myproject")
        mock_save.assert_called_once()


def test_chat_mode_exit_without_message_does_not_call_provider(runner, mock_config):
    mock_provider = MagicMock()
    mock_provider.last_usage = None
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

        result = runner.invoke(cli, ["--chat"], input="/exit\n")
        assert result.exit_code == 0
        mock_provider.stream_chat.assert_not_called()
        mock_save.assert_not_called()


def test_chat_mode_system_prompt_override_is_used(runner, mock_config):
    mock_provider = MagicMock()
    mock_provider.stream_chat.return_value = iter(["response"])
    mock_provider.last_usage = None
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

        result = runner.invoke(
            cli,
            ["--chat", "--system", "You are concise", "hello"],
            input="/exit\n",
        )
        assert result.exit_code == 0
        _, called_system = mock_provider.stream_chat.call_args[0]
        assert called_system == "You are concise"


def test_chat_mode_keyboard_interrupt_at_prompt_exits_cleanly(runner, mock_config):
    mock_provider = MagicMock()
    mock_provider.last_usage = None
    with (
        patch("bot.main.load_config", return_value=mock_config),
        patch("bot.main.load_history", return_value=[]),
        patch(
            "bot.main.get_provider_config",
            return_value=mock_config["providers"]["anthropic"],
        ),
        patch("bot.main.get_provider", return_value=mock_provider),
        patch("builtins.input", side_effect=KeyboardInterrupt),
    ):
        from bot.main import cli

        result = runner.invoke(cli, ["--chat"])
        assert result.exit_code == 0
        assert "Interrupted" in result.output


def test_chat_mode_help_command_shows_commands(runner, mock_config):
    mock_provider = MagicMock()
    mock_provider.last_usage = None
    with (
        patch("bot.main.load_config", return_value=mock_config),
        patch("bot.main.load_history", return_value=[]),
        patch(
            "bot.main.get_provider_config",
            return_value=mock_config["providers"]["anthropic"],
        ),
        patch("bot.main.get_provider", return_value=mock_provider),
    ):
        from bot.main import cli

        result = runner.invoke(cli, ["--chat"], input="/help\n/exit\n")
        assert result.exit_code == 0
        assert "/history" in result.output
        assert "/clear" in result.output
        mock_provider.stream_chat.assert_not_called()


def test_chat_mode_history_command_prints_messages(runner, mock_config):
    existing = [
        {"role": "user", "content": "what is ssh"},
        {"role": "assistant", "content": "Secure Shell"},
    ]
    mock_provider = MagicMock()
    mock_provider.last_usage = None
    with (
        patch("bot.main.load_config", return_value=mock_config),
        patch("bot.main.load_history", return_value=existing),
        patch(
            "bot.main.get_provider_config",
            return_value=mock_config["providers"]["anthropic"],
        ),
        patch("bot.main.get_provider", return_value=mock_provider),
    ):
        from bot.main import cli

        result = runner.invoke(cli, ["--chat"], input="/history\n/exit\n")
        assert result.exit_code == 0
        assert "what is ssh" in result.output
        assert "Secure Shell" in result.output
        mock_provider.stream_chat.assert_not_called()


def test_chat_mode_clear_command_clears_history(runner, mock_config):
    existing = [
        {"role": "user", "content": "old message"},
        {"role": "assistant", "content": "old reply"},
    ]
    mock_provider = MagicMock()
    mock_provider.last_usage = None
    with (
        patch("bot.main.load_config", return_value=mock_config),
        patch("bot.main.load_history", return_value=existing),
        patch("bot.main.save_history") as mock_save,
        patch(
            "bot.main.get_provider_config",
            return_value=mock_config["providers"]["anthropic"],
        ),
        patch("bot.main.get_provider", return_value=mock_provider),
    ):
        from bot.main import cli

        result = runner.invoke(cli, ["--chat"], input="/clear\n/exit\n")
        assert result.exit_code == 0
        assert "cleared" in result.output
        # save_history called with empty history
        mock_save.assert_called_once()
        assert mock_save.call_args[0][1] == []


# --- Export tests ---


def test_export_markdown_to_stdout(runner, mock_config):
    meta = {
        "provider": "anthropic",
        "history": [
            {"role": "user", "content": "what is a venv"},
            {"role": "assistant", "content": "a virtual environment"},
        ],
    }
    with (
        patch("bot.main.load_config", return_value=mock_config),
        patch("bot.main.load_session_with_meta", return_value=meta),
    ):
        from bot.main import cli

        result = runner.invoke(cli, ["--export", "myproject"])
        assert result.exit_code == 0
        assert "# Session: myproject" in result.output
        assert "Provider: anthropic" in result.output
        assert "**User:** what is a venv" in result.output
        assert "**Assistant:** a virtual environment" in result.output


def test_export_text_format(runner, mock_config):
    meta = {
        "provider": "openai",
        "history": [
            {"role": "user", "content": "hello"},
            {"role": "assistant", "content": "hi there"},
        ],
    }
    with (
        patch("bot.main.load_config", return_value=mock_config),
        patch("bot.main.load_session_with_meta", return_value=meta),
    ):
        from bot.main import cli

        result = runner.invoke(cli, ["--export", "myproject", "--format", "text"])
        assert result.exit_code == 0
        assert "Session: myproject" in result.output
        assert "USER: hello" in result.output
        assert "ASSISTANT: hi there" in result.output


def test_export_to_file(runner, mock_config, tmp_path):
    meta = {
        "provider": "anthropic",
        "history": [{"role": "user", "content": "hello"}, {"role": "assistant", "content": "hi"}],
    }
    output = str(tmp_path / "out.md")
    with (
        patch("bot.main.load_config", return_value=mock_config),
        patch("bot.main.load_session_with_meta", return_value=meta),
    ):
        from bot.main import cli

        result = runner.invoke(cli, ["--export", "myproject", "--output", output])
        assert result.exit_code == 0
        assert "Exported" in result.output
        content = open(output).read()
        assert "# Session: myproject" in content
        assert "**User:** hello" in content


def test_export_unknown_session(runner, mock_config):
    with (
        patch("bot.main.load_config", return_value=mock_config),
        patch("bot.main.load_session_with_meta", return_value=None),
    ):
        from bot.main import cli

        result = runner.invoke(cli, ["--export", "nonexistent"])
        assert result.exit_code == 1


def test_export_rejects_invalid_session_name(runner, mock_config):
    with patch("bot.main.load_config", return_value=mock_config):
        from bot.main import cli

        result = runner.invoke(cli, ["--export", "../bad"])
        assert result.exit_code == 1
        assert "Invalid session name" in result.output


def test_export_empty_session(runner, mock_config):
    meta = {"provider": "anthropic", "history": []}
    with (
        patch("bot.main.load_config", return_value=mock_config),
        patch("bot.main.load_session_with_meta", return_value=meta),
    ):
        from bot.main import cli

        result = runner.invoke(cli, ["--export", "empty"])
        assert result.exit_code == 0
        assert "empty" in result.output


# --- Token/cost tracking tests ---


def test_estimate_cost_known_model():
    from bot.main import estimate_cost

    cost = estimate_cost("gpt-4o-mini", 1_000_000, 1_000_000)
    assert cost == pytest.approx(0.15 + 0.60)


def test_estimate_cost_unknown_model():
    from bot.main import estimate_cost

    assert estimate_cost("unknown-model", 100, 200) is None


def test_chat_displays_usage_footer(runner, mock_config):
    mock_provider = MagicMock()
    mock_provider.stream_chat.return_value = iter(["hello"])
    mock_provider.last_usage = {"input_tokens": 42, "output_tokens": 183}
    with (
        patch("bot.main.load_config", return_value=mock_config),
        patch("bot.main.load_history", return_value=[]),
        patch("bot.main.save_history"),
        patch("bot.main.accumulate_usage"),
        patch(
            "bot.main.get_provider_config",
            return_value=mock_config["providers"]["anthropic"],
        ),
        patch("bot.main.get_provider", return_value=mock_provider),
    ):
        from bot.main import cli

        result = runner.invoke(cli, ["hello"])
        assert result.exit_code == 0
        assert "42" in result.output
        assert "183" in result.output


def test_chat_no_footer_when_no_usage(runner, mock_config):
    mock_provider = MagicMock()
    mock_provider.stream_chat.return_value = iter(["hello"])
    mock_provider.last_usage = None
    with (
        patch("bot.main.load_config", return_value=mock_config),
        patch("bot.main.load_history", return_value=[]),
        patch("bot.main.save_history"),
        patch("bot.main.accumulate_usage"),
        patch(
            "bot.main.get_provider_config",
            return_value=mock_config["providers"]["anthropic"],
        ),
        patch("bot.main.get_provider", return_value=mock_provider),
    ):
        from bot.main import cli

        result = runner.invoke(cli, ["hello"])
        assert result.exit_code == 0
        assert "in ·" not in result.output


def test_show_usage_flag_no_data(runner, mock_config):
    with (
        patch("bot.main.load_config", return_value=mock_config),
        patch("bot.main.load_usage", return_value={"input_tokens": 0, "output_tokens": 0, "cost_usd": 0.0}),
    ):
        from bot.main import cli

        result = runner.invoke(cli, ["--usage"])
        assert result.exit_code == 0
        assert "No usage recorded" in result.output


def test_show_usage_flag_with_data(runner, mock_config):
    def fake_load_usage(provider):
        if provider == "anthropic":
            return {"input_tokens": 1000, "output_tokens": 2000, "cost_usd": 0.009}
        return {"input_tokens": 0, "output_tokens": 0, "cost_usd": 0.0}

    with (
        patch("bot.main.load_config", return_value=mock_config),
        patch("bot.main.load_usage", side_effect=fake_load_usage),
    ):
        from bot.main import cli

        result = runner.invoke(cli, ["--usage"])
        assert result.exit_code == 0
        assert "anthropic" in result.output
        assert "1,000" in result.output
        assert "2,000" in result.output