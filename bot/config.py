"""
Config and history management for bot.
All data lives in ~/.bot/ - works on Linux, macOS and Windows.
"""

import json
import os
import re
from pathlib import Path
from typing import Any

BOT_DIR = Path.home() / ".bot"
CONFIG_FILE = BOT_DIR / "config.json"
MAX_HISTORY = 50
SESSIONS_DIR = BOT_DIR / "sessions"
SESSION_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")

DEFAULT_CONFIG: dict[str, Any] = {
    "provider": "anthropic",
    "providers": {
        "anthropic": {
            "model": "claude-haiku-4-5",
            "api_key_env": "ANTHROPIC_API_KEY",
        },
        "openai": {
            "model": "gpt-4o-mini",
            "api_key_env": "OPENAI_API_KEY",
        },
        "ollama": {
            "model": "llama3",
            "base_url": "http://localhost:11434",
        },
        "llamacpp": {
            "model": "local",
            "base_url": "http://localhost:8080",
        },
    },
}


def ensure_dir() -> None:
    BOT_DIR.mkdir(exist_ok=True)
    _secure_dir(BOT_DIR)


def ensure_sessions_dir() -> None:
    ensure_dir()
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
    _secure_dir(SESSIONS_DIR)


def _secure_dir(path: Path) -> None:
    # On Unix, keep bot data private to the current user.
    if os.name != "nt":
        try:
            path.chmod(0o700)
        except OSError:
            pass


def _secure_file(path: Path) -> None:
    # Best-effort hardening; permission changes may fail on some filesystems.
    if os.name != "nt":
        try:
            path.chmod(0o600)
        except OSError:
            pass


def validate_session_name(name: str) -> str:
    name = name.strip()
    if not SESSION_NAME_RE.fullmatch(name):
        raise ValueError(
            "Invalid session name. Use 1-64 chars: letters, numbers, '.', '_' or '-'."
        )
    return name


def load_config() -> dict[str, Any]:
    ensure_dir()
    if not CONFIG_FILE.exists():
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG.copy()
    with open(CONFIG_FILE) as f:
        saved = json.load(f)
    merged = DEFAULT_CONFIG.copy()
    merged.update(saved)
    providers = DEFAULT_CONFIG["providers"].copy()
    providers.update(saved.get("providers", {}))
    merged["providers"] = providers
    return merged


def save_config(config: dict[str, Any]) -> None:
    ensure_dir()
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)
    _secure_file(CONFIG_FILE)


def history_file(provider: str) -> Path:
    return BOT_DIR / f"history_{provider}.json"


def load_history(provider: str) -> list[dict]:
    path = history_file(provider)
    if not path.exists():
        return []
    with open(path) as f:
        return json.load(f)


def save_history(provider: str, history: list[dict]) -> None:
    ensure_dir()
    trimmed = history[-(MAX_HISTORY * 2) :]
    path = history_file(provider)
    with open(path, "w") as f:
        json.dump(trimmed, f, indent=2)
    _secure_file(path)


def clear_history(provider: str) -> None:
    path = history_file(provider)
    if path.exists():
        path.unlink()


def usage_file(provider: str) -> Path:
    return BOT_DIR / f"usage_{provider}.json"


def load_usage(provider: str) -> dict:
    path = usage_file(provider)
    if not path.exists():
        return {"input_tokens": 0, "output_tokens": 0, "cost_usd": 0.0}
    with open(path) as f:
        return json.load(f)


def save_usage(provider: str, data: dict) -> None:
    ensure_dir()
    path = usage_file(provider)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
    _secure_file(path)


def accumulate_usage(provider: str, input_tokens: int, output_tokens: int, cost: float) -> None:
    data = load_usage(provider)
    data["input_tokens"] += input_tokens
    data["output_tokens"] += output_tokens
    data["cost_usd"] += cost
    save_usage(provider, data)


def get_provider_config(config: dict, provider: str) -> dict:
    providers = config.get("providers", {})
    if provider not in providers:
        raise ValueError(
            f"Unknown provider '{provider}'. Available: {', '.join(providers.keys())}"
        )
    return providers[provider]


def session_file(name: str) -> Path:
    safe_name = validate_session_name(name)
    return SESSIONS_DIR / f"{safe_name}.json"


def load_session(name: str) -> list[dict]:
    path = session_file(name)
    if not path.exists():
        return []
    with open(path) as f:
        data = json.load(f)
    # Support both old format (plain list) and new format (dict with metadata)
    if isinstance(data, list):
        return data
    return data.get("history", [])


def load_session_with_meta(name: str) -> dict:
    """Return {"provider": str|None, "history": list[dict]} or None if not found."""
    path = session_file(name)
    if not path.exists():
        return None
    with open(path) as f:
        data = json.load(f)
    if isinstance(data, list):
        return {"provider": None, "history": data}
    return {"provider": data.get("provider"), "history": data.get("history", [])}


def save_session(name: str, history: list[dict], provider: str | None = None) -> None:
    ensure_sessions_dir()
    trimmed = history[-(MAX_HISTORY * 2) :]
    payload: Any = {"provider": provider, "history": trimmed}
    path = session_file(name)
    with open(path, "w") as f:
        json.dump(payload, f, indent=2)
    _secure_file(path)


def clear_session(name: str) -> None:
    path = session_file(name)
    if path.exists():
        path.unlink()


def list_sessions() -> list[dict]:
    ensure_sessions_dir()
    sessions = []
    for path in sorted(SESSIONS_DIR.glob("*.json")):
        try:
            with open(path) as f:
                data = json.load(f)
            if isinstance(data, list):
                history = data
                provider = None
            else:
                history = data.get("history", [])
                provider = data.get("provider")
            first_user = next(
                (m["content"] for m in history if m.get("role") == "user"), None
            )
            preview = (first_user[:60] + "…") if first_user and len(first_user) > 60 else first_user
            sessions.append({
                "name": path.stem,
                "messages": len(history),
                "modified": path.stat().st_mtime,
                "provider": provider,
                "preview": preview,
            })
        except (json.JSONDecodeError, OSError):
            continue
    return sessions