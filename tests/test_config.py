"""Tests for config and history management."""

from unittest.mock import patch

import pytest


def test_ensure_dir_create_directory(tmp_path):
    with patch("bot.config.BOT_DIR", tmp_path / ".bot"):
        from bot.config import ensure_dir

        ensure_dir()
        assert (tmp_path / ".bot").exists()


def test_load_config_creates_default_if_missing(tmp_path):
    bot_dir = tmp_path / ".bot"
    with (
        patch("bot.config.BOT_DIR", bot_dir),
        patch("bot.config.CONFIG_FILE", bot_dir / "config.json"),
    ):
        from bot.config import load_config

        config = load_config()
        assert config["provider"] == "anthropic"
        assert "anthropic" in config["providers"]
        assert "openai" in config["providers"]
        assert "ollama" in config["providers"]
        assert "llamacpp" in config["providers"]


def test_save_and_load_config_roundtrip(tmp_path):
    bot_dir = tmp_path / ".bot"
    bot_dir.mkdir()
    config_file = bot_dir / "config.json"
    with (
        patch("bot.config.BOT_DIR", bot_dir),
        patch("bot.config.CONFIG_FILE", config_file),
    ):
        from bot.config import load_config, save_config

        data = {"provider": "openai", "providers": {"openai": {"model": "gpt-4o-mini"}}}
        save_config(data)
        loaded = load_config()
        assert loaded["provider"] == "openai"


def test_save_history_and_load_history(tmp_path):
    bot_dir = tmp_path / ".bot"
    bot_dir.mkdir()
    with patch("bot.config.BOT_DIR", bot_dir):
        from bot.config import load_history, save_history

        messages = [
            {"role": "user", "content": "hello"},
            {"role": "assistant", "content": "hi there"},
        ]
        save_history("anthropic", messages)
        loaded = load_history("anthropic")
        assert loaded == messages


def test_load_history_returns_empty_if_missing(tmp_path):
    bot_dir = tmp_path / ".bot"
    bot_dir.mkdir()
    with patch("bot.config.BOT_DIR", bot_dir):
        from bot.config import load_history

        result = load_history("anthropic")
        assert result == []


def test_clear_history_removes_file(tmp_path):
    bot_dir = tmp_path / ".bot"
    bot_dir.mkdir()
    with patch("bot.config.BOT_DIR", bot_dir):
        from bot.config import clear_history, load_history, save_history

        save_history("anthropic", [{"role": "user", "content": "test"}])
        clear_history("anthropic")
        assert load_history("anthropic") == []


def test_history_trimmed_to_max(tmp_path):
    bot_dir = tmp_path / ".bot"
    bot_dir.mkdir()
    with patch("bot.config.BOT_DIR", bot_dir), patch("bot.config.MAX_HISTORY", 2):
        from bot.config import load_history, save_history

        messages = [{"role": "user", "content": str(i)} for i in range(10)]
        save_history("anthropic", messages)
        loaded = load_history("anthropic")
        assert len(loaded) == 4  # MAX_HISTORY * 2


def test_get_provider_config_returns_correct(tmp_path):
    bot_dir = tmp_path / ".bot"
    with patch("bot.config.BOT_DIR", bot_dir):
        from bot.config import get_provider_config

        config = {"providers": {"anthropic": {"model": "claude-haiku-4-5"}}}
        result = get_provider_config(config, "anthropic")
        assert result["model"] == "claude-haiku-4-5"


def test_get_provider_config_raises_on_unknown(tmp_path):
    bot_dir = tmp_path / ".bot"
    with patch("bot.config.BOT_DIR", bot_dir):
        from bot.config import get_provider_config

        config = {"providers": {"anthropic": {"model": "claude-haiku-4-5"}}}
        with pytest.raises(ValueError, match="Unknown"):
            get_provider_config(config, "nonexistent")


# --- Session tests ---


def test_save_and_load_session(tmp_path):
    sessions_dir = tmp_path / ".bot" / "sessions"
    with patch("bot.config.SESSIONS_DIR", sessions_dir):
        from bot.config import load_session, save_session

        messages = [
            {"role": "user", "content": "what is a venv"},
            {"role": "assistant", "content": "a virtual environment"},
        ]
        save_session("myproject", messages)
        loaded = load_session("myproject")
        assert loaded == messages


def test_load_session_returns_empty_if_missing(tmp_path):
    sessions_dir = tmp_path / ".bot" / "sessions"
    with patch("bot.config.SESSIONS_DIR", sessions_dir):
        from bot.config import load_session

        result = load_session("nonexistent")
        assert result == []


def test_clear_session_removes_file(tmp_path):
    sessions_dir = tmp_path / ".bot" / "sessions"
    with patch("bot.config.SESSIONS_DIR", sessions_dir):
        from bot.config import clear_session, load_session, save_session

        save_session("myproject", [{"role": "user", "content": "hello"}])
        clear_session("myproject")
        assert load_session("myproject") == []


def test_clear_session_noop_if_missing(tmp_path):
    sessions_dir = tmp_path / ".bot" / "sessions"
    with patch("bot.config.SESSIONS_DIR", sessions_dir):
        from bot.config import clear_session

        # Should not raise
        clear_session("nonexistent")


def test_list_sessions_returns_all(tmp_path):
    sessions_dir = tmp_path / ".bot" / "sessions"
    with patch("bot.config.SESSIONS_DIR", sessions_dir):
        from bot.config import list_sessions, save_session

        save_session("alpha", [{"role": "user", "content": "a"}])
        save_session("beta", [{"role": "user", "content": "b"}, {"role": "assistant", "content": "c"}])
        sessions = list_sessions()
        names = [s["name"] for s in sessions]
        assert "alpha" in names
        assert "beta" in names


def test_list_sessions_message_count(tmp_path):
    sessions_dir = tmp_path / ".bot" / "sessions"
    with patch("bot.config.SESSIONS_DIR", sessions_dir):
        from bot.config import list_sessions, save_session

        messages = [{"role": "user", "content": str(i)} for i in range(6)]
        save_session("counted", messages)
        sessions = list_sessions()
        match = next(s for s in sessions if s["name"] == "counted")
        assert match["messages"] == 6


def test_list_sessions_empty(tmp_path):
    sessions_dir = tmp_path / ".bot" / "sessions"
    with patch("bot.config.SESSIONS_DIR", sessions_dir):
        from bot.config import list_sessions

        assert list_sessions() == []


def test_session_trimmed_to_max(tmp_path):
    sessions_dir = tmp_path / ".bot" / "sessions"
    with patch("bot.config.SESSIONS_DIR", sessions_dir), patch("bot.config.MAX_HISTORY", 2):
        from bot.config import load_session, save_session

        messages = [{"role": "user", "content": str(i)} for i in range(10)]
        save_session("trim-test", messages)
        loaded = load_session("trim-test")
        assert len(loaded) == 4  # MAX_HISTORY * 2