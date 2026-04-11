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
