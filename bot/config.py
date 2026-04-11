"""
Config and history management for bot.
All data lives in ~/.bot/ - works on Linux, macOS and Windows.
"""

import json
from pathlib import Path
from typing import Any

BOT_DIR = Path.home() / ".bot"
CONFIG_FILE = BOT_DIR / "config.json"
MAX_HISTORY = 50
SESSIONS_DIR = BOT_DIR / "sessions"

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


def ensure_sessions_dir() -> None:
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)


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
    with open(history_file(provider), "w") as f:
        json.dump(trimmed, f, indent=2)


def clear_history(provider: str) -> None:
    path = history_file(provider)
    if path.exists():
        path.unlink()


def get_provider_config(config: dict, provider: str) -> dict:
    providers = config.get("providers", {})
    if provider not in providers:
        raise ValueError(
            f"Unknown provider '{provider}'. Available: {', '.join(providers.keys())}"
        )
    return providers[provider]


def session_file(name: str) -> Path:
    return SESSIONS_DIR / f"{name}.json"


def load_session(name: str) -> list[dict]:
    path = session_file(name)
    if not path.exists():
        return []
    with open(path) as f:
        return json.load(f)


def save_session(name: str, history: list[dict]) -> None:
    ensure_sessions_dir()
    trimmed = history[-(MAX_HISTORY * 2) :]
    with open(session_file(name), "w") as f:
        json.dump(trimmed, f, indent=2)


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
                history = json.load(f)
            sessions.append({
                "name": path.stem,
                "messages": len(history),
                "modified": path.stat().st_mtime,
            })
        except (json.JSONDecodeError, OSError):
            continue
    return sessions