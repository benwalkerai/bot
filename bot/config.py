"""
Config and history management for bot.
All data lives in ~/.bot/ - works on Linux, macOS and Windows.
"""

import json
import os
import re
import time
from copy import deepcopy
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

BOT_DIR = Path.home() / ".bot"
CONFIG_FILE = BOT_DIR / "config.json"
MAX_HISTORY = 50
SESSIONS_DIR = BOT_DIR / "sessions"
SECURITY_LOG_FILE = BOT_DIR / "security.log"
SESSION_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
SECRET_VALUE_RE = re.compile(
    r"\b(?:sk-[A-Za-z0-9_-]{10,}|sk-ant-[A-Za-z0-9_-]{10,}|ghp_[A-Za-z0-9]{20,}|AIza[0-9A-Za-z\\-_]{20,}|AKIA[0-9A-Z]{16})\b|"
    r"\b(?:api[_-]?key|token|secret|password)\s*[:=]\s*['\"]?[^\s'\"]{8,}['\"]?",
    re.IGNORECASE,
)

SECURITY_DEFAULTS: dict[str, Any] = {
    "safe_output": True,
    "redact_secrets": False,
    "warn_dangerous_commands": True,
    "allowed_export_dirs": [],
    "allowed_hosts": [],
    "allow_insecure_http": False,
    "request_timeout_seconds": 30,
    "max_retries": 2,
    "retention_days": 30,
}

DEFAULT_CONFIG: dict[str, Any] = {
    "provider": "anthropic",
    "security": SECURITY_DEFAULTS,
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
        return deepcopy(DEFAULT_CONFIG)
    with open(CONFIG_FILE) as f:
        saved = json.load(f)
    merged = deepcopy(DEFAULT_CONFIG)
    merged.update(saved)
    providers = DEFAULT_CONFIG["providers"].copy()
    providers.update(saved.get("providers", {}))
    merged["providers"] = providers
    security = SECURITY_DEFAULTS.copy()
    security.update(saved.get("security", {}))
    merged["security"] = security
    return merged


def save_config(config: dict[str, Any]) -> None:
    ensure_dir()
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)
    _secure_file(CONFIG_FILE)


def _redact_security_value(value: Any) -> Any:
    if isinstance(value, str):
        return SECRET_VALUE_RE.sub("[REDACTED]", value)
    if isinstance(value, dict):
        redacted: dict[str, Any] = {}
        for key, item in value.items():
            lowered = str(key).lower()
            if any(token in lowered for token in ("password", "token", "secret", "api_key", "apikey")):
                redacted[key] = "[REDACTED]"
            else:
                redacted[key] = _redact_security_value(item)
        return redacted
    if isinstance(value, list):
        return [_redact_security_value(item) for item in value]
    return value


def log_security_event(action: str, **details: Any) -> None:
    if os.environ.get("BOT_DISABLE_SECURITY_LOG") == "1":
        return
    ensure_dir()
    entry = {
        "timestamp": time.time(),
        "action": action,
        "details": _redact_security_value(details),
    }
    with open(SECURITY_LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, separators=(",", ":")))
        f.write("\n")
    _secure_file(SECURITY_LOG_FILE)


def history_file(provider: str) -> Path:
    return BOT_DIR / f"history_{provider}.json"


def load_history(provider: str) -> list[dict]:
    path = history_file(provider)
    if not path.exists():
        return []
    try:
        with open(path) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return []


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
    try:
        with open(path) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {"input_tokens": 0, "output_tokens": 0, "cost_usd": 0.0}


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
    cfg = providers[provider].copy()
    security = config.get("security", {})

    if "base_url" in cfg:
        _validate_base_url(str(cfg["base_url"]), security)

    cfg.setdefault(
        "request_timeout_seconds",
        int(security.get("request_timeout_seconds", SECURITY_DEFAULTS["request_timeout_seconds"])),
    )
    cfg.setdefault(
        "max_retries",
        int(security.get("max_retries", SECURITY_DEFAULTS["max_retries"])),
    )
    return cfg


def _validate_base_url(url: str, security: dict[str, Any]) -> None:
    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        raise ValueError(f"Invalid base_url '{url}'. Use an absolute URL.")

    host = (parsed.hostname or "").lower()
    is_local = host in {"localhost", "127.0.0.1", "::1"}
    allow_insecure_http = bool(security.get("allow_insecure_http", False))

    if parsed.scheme.lower() != "https" and not (is_local or allow_insecure_http):
        raise ValueError(
            f"Insecure base_url '{url}'. Use https, localhost, or enable allow_insecure_http."
        )

    allowed_hosts = security.get("allowed_hosts", []) or []
    if allowed_hosts and host not in {str(h).lower() for h in allowed_hosts}:
        raise ValueError(
            f"Host '{host}' is not in security.allowed_hosts."
        )


def session_file(name: str) -> Path:
    safe_name = validate_session_name(name)
    return SESSIONS_DIR / f"{safe_name}.json"


def load_session(name: str) -> list[dict]:
    path = session_file(name)
    if not path.exists():
        return []
    try:
        with open(path) as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return []
    # Support both old format (plain list) and new format (dict with metadata)
    if isinstance(data, list):
        return data
    return data.get("history", [])


def load_session_with_meta(name: str) -> dict:
    """Return {"provider": str|None, "history": list[dict]} or None if not found."""
    path = session_file(name)
    if not path.exists():
        return None
    try:
        with open(path) as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return None
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


def purge_old_data(retention_days: int) -> dict[str, int]:
    if retention_days < 0:
        raise ValueError("retention_days must be zero or positive")

    cutoff = time.time() - (retention_days * 86400)
    removed = {"history": 0, "usage": 0, "sessions": 0}

    for path in BOT_DIR.glob("history_*.json"):
        try:
            if path.stat().st_mtime < cutoff:
                path.unlink()
                removed["history"] += 1
        except OSError:
            continue

    for path in BOT_DIR.glob("usage_*.json"):
        try:
            if path.stat().st_mtime < cutoff:
                path.unlink()
                removed["usage"] += 1
        except OSError:
            continue

    if SESSIONS_DIR.exists():
        for path in SESSIONS_DIR.glob("*.json"):
            try:
                if path.stat().st_mtime < cutoff:
                    path.unlink()
                    removed["sessions"] += 1
            except OSError:
                continue

    return removed