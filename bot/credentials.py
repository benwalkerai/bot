"""Credential helpers for secure API key storage and retrieval.

Keys are stored in the OS keyring when available. Environment variables remain
supported as a fallback for CI and automation use cases.
"""

from __future__ import annotations

import os

import keyring
from keyring.errors import KeyringError, NoKeyringError, PasswordDeleteError

KEYRING_SERVICE = "inzen-bot"


def _entry_name(provider: str) -> str:
    return f"{provider.lower()}_api_key"


def keyring_is_available() -> bool:
    try:
        backend = keyring.get_keyring()
        if backend is None:
            return False
        # keyring's fail backend raises NoKeyringError on access.
        try:
            keyring.get_password(KEYRING_SERVICE, "__availability_probe__")
        except NoKeyringError:
            return False
        return True
    except Exception:
        return False


def get_api_key(provider: str, env_var: str) -> str | None:
    """Return API key from keyring first, then environment variable fallback."""
    try:
        value = keyring.get_password(KEYRING_SERVICE, _entry_name(provider))
        if value:
            return value
    except Exception:
        # Fall through to env var fallback for systems without keyring support.
        pass

    return os.environ.get(env_var)


def set_api_key(provider: str, value: str) -> None:
    if not value:
        raise ValueError("API key cannot be empty")
    try:
        keyring.set_password(KEYRING_SERVICE, _entry_name(provider), value)
    except KeyringError as e:
        raise RuntimeError(
            "Could not store API key in system keyring. "
            "Configure a supported keyring backend or use environment variables."
        ) from e


def has_stored_api_key(provider: str) -> bool:
    try:
        return bool(keyring.get_password(KEYRING_SERVICE, _entry_name(provider)))
    except Exception:
        return False


def delete_api_key(provider: str) -> bool:
    """Delete an API key from keyring. Returns True when a key was removed."""
    entry = _entry_name(provider)
    try:
        if not keyring.get_password(KEYRING_SERVICE, entry):
            return False
        keyring.delete_password(KEYRING_SERVICE, entry)
        return True
    except PasswordDeleteError:
        return False
    except NoKeyringError as e:
        raise RuntimeError("No supported system keyring backend is available.") from e