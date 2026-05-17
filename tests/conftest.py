import pytest


@pytest.fixture(autouse=True)
def disable_security_log(monkeypatch):
    monkeypatch.setenv("BOT_DISABLE_SECURITY_LOG", "1")
