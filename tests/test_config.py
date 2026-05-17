"""Tests for config and history management."""

import os
import stat
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
        assert "security" in config
        assert config["security"]["safe_output"] is True
        assert config["security"]["retention_days"] == 30


def test_get_provider_config_rejects_insecure_remote_http():
    from bot.config import get_provider_config

    config = {
        "providers": {"openai": {"model": "gpt-4o-mini", "base_url": "http://example.com/v1"}},
        "security": {"allow_insecure_http": False},
    }

    with pytest.raises(ValueError, match="Insecure base_url"):
        get_provider_config(config, "openai")


def test_get_provider_config_allows_local_http():
    from bot.config import get_provider_config

    config = {
        "providers": {"ollama": {"model": "llama3", "base_url": "http://localhost:11434"}},
        "security": {"allow_insecure_http": False},
    }

    result = get_provider_config(config, "ollama")
    assert result["base_url"] == "http://localhost:11434"


def test_get_provider_config_enforces_allowed_hosts():
    from bot.config import get_provider_config

    config = {
        "providers": {"openai": {"model": "gpt-4o-mini", "base_url": "https://api.openai.com/v1"}},
        "security": {"allowed_hosts": ["api.groq.com"]},
    }

    with pytest.raises(ValueError, match="not in security.allowed_hosts"):
        get_provider_config(config, "openai")


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


def test_load_history_returns_empty_if_malformed(tmp_path):
    bot_dir = tmp_path / ".bot"
    bot_dir.mkdir()
    (bot_dir / "history_anthropic.json").write_text("{not-json", encoding="utf-8")
    with patch("bot.config.BOT_DIR", bot_dir):
        from bot.config import load_history

        assert load_history("anthropic") == []


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


def test_validate_session_name_accepts_safe_values():
    from bot.config import validate_session_name

    assert validate_session_name("myproject") == "myproject"
    assert validate_session_name("proj_1.test-2") == "proj_1.test-2"


@pytest.mark.parametrize(
    "name",
    ["", "../etc/passwd", "my/project", "..", "name with spaces", "💥"],
)
def test_validate_session_name_rejects_unsafe_values(name):
    from bot.config import validate_session_name

    with pytest.raises(ValueError, match="Invalid session name"):
        validate_session_name(name)


def test_save_session_rejects_path_traversal_name(tmp_path):
    sessions_dir = tmp_path / ".bot" / "sessions"
    with patch("bot.config.SESSIONS_DIR", sessions_dir):
        from bot.config import save_session

        with pytest.raises(ValueError, match="Invalid session name"):
            save_session("../bad", [{"role": "user", "content": "x"}], "anthropic")


def test_saved_files_use_private_permissions_on_unix(tmp_path):
    if os.name == "nt":
        pytest.skip("Windows ACL semantics differ from Unix mode bits")

    bot_dir = tmp_path / ".bot"
    sessions_dir = bot_dir / "sessions"
    config_file = bot_dir / "config.json"
    with (
        patch("bot.config.BOT_DIR", bot_dir),
        patch("bot.config.SESSIONS_DIR", sessions_dir),
        patch("bot.config.CONFIG_FILE", config_file),
    ):
        from bot.config import save_config, save_history, save_session, save_usage

        save_config({"provider": "anthropic", "providers": {}})
        save_history("anthropic", [{"role": "user", "content": "hello"}])
        save_usage("anthropic", {"input_tokens": 1, "output_tokens": 2, "cost_usd": 0.0})
        save_session("secure", [{"role": "user", "content": "hello"}], "anthropic")

    assert stat.S_IMODE(bot_dir.stat().st_mode) == 0o700
    assert stat.S_IMODE(sessions_dir.stat().st_mode) == 0o700
    assert stat.S_IMODE(config_file.stat().st_mode) == 0o600
    assert stat.S_IMODE((bot_dir / "history_anthropic.json").stat().st_mode) == 0o600
    assert stat.S_IMODE((bot_dir / "usage_anthropic.json").stat().st_mode) == 0o600
    assert stat.S_IMODE((sessions_dir / "secure.json").stat().st_mode) == 0o600


def test_purge_old_data_deletes_expired_files(tmp_path):
    import time

    bot_dir = tmp_path / ".bot"
    sessions_dir = bot_dir / "sessions"
    old_ts = time.time() - (40 * 86400)

    with (
        patch("bot.config.BOT_DIR", bot_dir),
        patch("bot.config.SESSIONS_DIR", sessions_dir),
    ):
        from bot.config import purge_old_data, save_history, save_session, save_usage

        save_history("anthropic", [{"role": "user", "content": "old history"}])
        save_usage("anthropic", {"input_tokens": 1, "output_tokens": 2, "cost_usd": 0.0})
        save_session("old-session", [{"role": "user", "content": "old session"}], "anthropic")

        save_history("openai", [{"role": "user", "content": "new history"}])
        save_usage("openai", {"input_tokens": 3, "output_tokens": 4, "cost_usd": 0.0})
        save_session("new-session", [{"role": "user", "content": "new session"}], "openai")

        for path in [
            bot_dir / "history_anthropic.json",
            bot_dir / "usage_anthropic.json",
            sessions_dir / "old-session.json",
        ]:
            os.utime(path, (old_ts, old_ts))

        removed = purge_old_data(30)

    assert removed == {"history": 1, "usage": 1, "sessions": 1}
    assert not (bot_dir / "history_anthropic.json").exists()
    assert not (bot_dir / "usage_anthropic.json").exists()
    assert not (sessions_dir / "old-session.json").exists()
    assert (bot_dir / "history_openai.json").exists()
    assert (bot_dir / "usage_openai.json").exists()
    assert (sessions_dir / "new-session.json").exists()


def test_purge_old_data_rejects_negative_window():
    from bot.config import purge_old_data

    with pytest.raises(ValueError, match="zero or positive"):
        purge_old_data(-1)


def test_log_security_event_redacts_sensitive_values(tmp_path):
    bot_dir = tmp_path / ".bot"
    log_file = bot_dir / "security.log"
    with (
        patch("bot.config.BOT_DIR", bot_dir),
        patch("bot.config.SECURITY_LOG_FILE", log_file),
        patch.dict("os.environ", {"BOT_DISABLE_SECURITY_LOG": "0"}, clear=False),
    ):
        from bot.config import log_security_event

        log_security_event(
            "export",
            token="sk-ant-1234567890abcdef",
            nested={"password": "supersecret"},
        )

    payload = log_file.read_text().strip()
    assert "sk-ant-1234567890abcdef" not in payload
    assert "supersecret" not in payload
    assert "[REDACTED]" in payload


# --- Session tests ---


def test_save_and_load_session(tmp_path):
    sessions_dir = tmp_path / ".bot" / "sessions"
    with patch("bot.config.SESSIONS_DIR", sessions_dir):
        from bot.config import load_session, save_session

        messages = [
            {"role": "user", "content": "what is a venv"},
            {"role": "assistant", "content": "a virtual environment"},
        ]
        save_session("myproject", messages, "anthropic")
        loaded = load_session("myproject")
        assert loaded == messages


def test_load_session_returns_empty_if_missing(tmp_path):
    sessions_dir = tmp_path / ".bot" / "sessions"
    with patch("bot.config.SESSIONS_DIR", sessions_dir):
        from bot.config import load_session

        result = load_session("nonexistent")
        assert result == []


def test_load_session_returns_empty_if_malformed(tmp_path):
    sessions_dir = tmp_path / ".bot" / "sessions"
    sessions_dir.mkdir(parents=True)
    (sessions_dir / "broken.json").write_text("{broken", encoding="utf-8")
    with patch("bot.config.SESSIONS_DIR", sessions_dir):
        from bot.config import load_session

        assert load_session("broken") == []


def test_clear_session_removes_file(tmp_path):
    sessions_dir = tmp_path / ".bot" / "sessions"
    with patch("bot.config.SESSIONS_DIR", sessions_dir):
        from bot.config import clear_session, load_session, save_session

        save_session("myproject", [{"role": "user", "content": "hello"}], "anthropic")
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

        save_session("alpha", [{"role": "user", "content": "a"}], "anthropic")
        save_session("beta", [{"role": "user", "content": "b"}, {"role": "assistant", "content": "c"}], "openai")
        sessions = list_sessions()
        names = [s["name"] for s in sessions]
        assert "alpha" in names
        assert "beta" in names


def test_list_sessions_message_count(tmp_path):
    sessions_dir = tmp_path / ".bot" / "sessions"
    with patch("bot.config.SESSIONS_DIR", sessions_dir):
        from bot.config import list_sessions, save_session

        messages = [{"role": "user", "content": str(i)} for i in range(6)]
        save_session("counted", messages, "anthropic")
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
        save_session("trim-test", messages, "anthropic")
        loaded = load_session("trim-test")
        assert len(loaded) == 4  # MAX_HISTORY * 2


def test_list_sessions_includes_provider_and_preview(tmp_path):
    sessions_dir = tmp_path / ".bot" / "sessions"
    with patch("bot.config.SESSIONS_DIR", sessions_dir):
        from bot.config import list_sessions, save_session

        save_session("proj", [{"role": "user", "content": "explain decorators"}], "openai")
        sessions = list_sessions()
        s = next(x for x in sessions if x["name"] == "proj")
        assert s["provider"] == "openai"
        assert s["preview"] == "explain decorators"


def test_list_sessions_preview_truncated(tmp_path):
    sessions_dir = tmp_path / ".bot" / "sessions"
    with patch("bot.config.SESSIONS_DIR", sessions_dir):
        from bot.config import list_sessions, save_session

        long_msg = "a" * 80
        save_session("proj", [{"role": "user", "content": long_msg}], "anthropic")
        sessions = list_sessions()
        s = next(x for x in sessions if x["name"] == "proj")
        assert s["preview"].endswith("…")
        assert len(s["preview"]) == 61  # 60 chars + ellipsis


def test_load_session_backward_compat_plain_list(tmp_path):
    import json

    sessions_dir = tmp_path / ".bot" / "sessions"
    sessions_dir.mkdir(parents=True)
    # Write old-format plain list directly
    old_data = [{"role": "user", "content": "hello"}, {"role": "assistant", "content": "hi"}]
    (sessions_dir / "legacy.json").write_text(json.dumps(old_data))
    with patch("bot.config.SESSIONS_DIR", sessions_dir):
        from bot.config import load_session

        loaded = load_session("legacy")
        assert loaded == old_data


def test_list_sessions_backward_compat_plain_list(tmp_path):
    import json

    sessions_dir = tmp_path / ".bot" / "sessions"
    sessions_dir.mkdir(parents=True)
    old_data = [{"role": "user", "content": "hello"}]
    (sessions_dir / "legacy.json").write_text(json.dumps(old_data))
    with patch("bot.config.SESSIONS_DIR", sessions_dir):
        from bot.config import list_sessions

        sessions = list_sessions()
        s = next(x for x in sessions if x["name"] == "legacy")
        assert s["provider"] is None
        assert s["preview"] == "hello"
        assert s["messages"] == 1


# --- load_session_with_meta tests ---


def test_load_session_with_meta_returns_provider_and_history(tmp_path):
    sessions_dir = tmp_path / ".bot" / "sessions"
    with patch("bot.config.SESSIONS_DIR", sessions_dir):
        from bot.config import load_session_with_meta, save_session

        messages = [{"role": "user", "content": "hello"}]
        save_session("proj", messages, "openai")
        meta = load_session_with_meta("proj")
        assert meta["provider"] == "openai"
        assert meta["history"] == messages


def test_load_session_with_meta_returns_none_if_missing(tmp_path):
    sessions_dir = tmp_path / ".bot" / "sessions"
    with patch("bot.config.SESSIONS_DIR", sessions_dir):
        from bot.config import load_session_with_meta

        assert load_session_with_meta("nonexistent") is None


def test_load_session_with_meta_returns_none_if_malformed(tmp_path):
    sessions_dir = tmp_path / ".bot" / "sessions"
    sessions_dir.mkdir(parents=True)
    (sessions_dir / "broken.json").write_text("{broken", encoding="utf-8")
    with patch("bot.config.SESSIONS_DIR", sessions_dir):
        from bot.config import load_session_with_meta

        assert load_session_with_meta("broken") is None


def test_load_session_with_meta_backward_compat(tmp_path):
    import json

    sessions_dir = tmp_path / ".bot" / "sessions"
    sessions_dir.mkdir(parents=True)
    old_data = [{"role": "user", "content": "hello"}]
    (sessions_dir / "legacy.json").write_text(json.dumps(old_data))
    with patch("bot.config.SESSIONS_DIR", sessions_dir):
        from bot.config import load_session_with_meta

        meta = load_session_with_meta("legacy")
        assert meta["provider"] is None
        assert meta["history"] == old_data


# --- Usage tracking tests ---


def test_load_usage_returns_zeros_if_missing(tmp_path):
    bot_dir = tmp_path / ".bot"
    with patch("bot.config.BOT_DIR", bot_dir):
        from bot.config import load_usage

        data = load_usage("anthropic")
        assert data == {"input_tokens": 0, "output_tokens": 0, "cost_usd": 0.0}


def test_load_usage_returns_zeros_if_malformed(tmp_path):
    bot_dir = tmp_path / ".bot"
    bot_dir.mkdir()
    (bot_dir / "usage_anthropic.json").write_text("{bad", encoding="utf-8")
    with patch("bot.config.BOT_DIR", bot_dir):
        from bot.config import load_usage

        data = load_usage("anthropic")
        assert data == {"input_tokens": 0, "output_tokens": 0, "cost_usd": 0.0}


def test_save_and_load_usage_roundtrip(tmp_path):
    bot_dir = tmp_path / ".bot"
    bot_dir.mkdir()
    with patch("bot.config.BOT_DIR", bot_dir):
        from bot.config import load_usage, save_usage

        save_usage("anthropic", {"input_tokens": 100, "output_tokens": 200, "cost_usd": 0.001})
        data = load_usage("anthropic")
        assert data["input_tokens"] == 100
        assert data["output_tokens"] == 200


def test_accumulate_usage_adds_to_totals(tmp_path):
    bot_dir = tmp_path / ".bot"
    bot_dir.mkdir()
    with patch("bot.config.BOT_DIR", bot_dir):
        from bot.config import accumulate_usage, load_usage

        accumulate_usage("anthropic", 50, 100, 0.001)
        accumulate_usage("anthropic", 30, 80, 0.0005)
        data = load_usage("anthropic")
        assert data["input_tokens"] == 80
        assert data["output_tokens"] == 180
        assert abs(data["cost_usd"] - 0.0015) < 1e-9