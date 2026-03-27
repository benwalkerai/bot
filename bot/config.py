"""
Config and history management for bot.
All data lives in ~/.bot/ - works on Linux, macOS and Windows.
"""

import json
import os
from pathlib import Path
from typing import Any

BOT_DIR = Path.home() /".bot"
CONFIG_FILE = BOT_DIR / "config.json"
MAX_HISTORY = 50 # max messages to keep in history

DEFAULT_CONFIG : dict[str, Any] = {
    "provider": "anthropic",
    "providers": {
        "anthropic": {
            "model": "claude-haiku-4-5-20251001",
            "api_key_env": "ANTHROPIC_API_KEY",
        },
        "openai": {
            "model": "gpt-5.4-nano",
            "api_key_env": "OPENAI_API_KEY",
        },
        "ollama": {
            "model": "llama3",
            "base_url": "http://localhost:11434",
        },
        "llamacpp": {
            "model"; "local",
            "base_url": "http://localhost:8080",
        },
    }
}

def ensure_dir() -> None:
    BOT_DIR.mkdir(exist_ok=True)

def load_config() -> dict[str, Any]:
    ensure_dir()
    if not CONFIG_FILE.exists():
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG.copy()
    with open(CONFIG_FILE) as f:
        saved = json.load(f)
    # Merge so new default providers appear for existing users
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
    trimmed = history[-(MAX_HISTORY * 2):]
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
            f"Unknown provder '{provider}'. "
            f"Available: {', '.join(providers.keys())}"
        )
    return providers[provider]

