"""Tests for self-update helpers."""

from unittest.mock import patch


def test_select_linux_asset_prefers_matching_arch():
    from bot.update import _select_linux_asset

    assets = [
        {"name": "inzen-bot_0.3.7_arm64.deb", "browser_download_url": "https://example/arm64.deb"},
        {"name": "inzen-bot_0.3.7_amd64.deb", "browser_download_url": "https://example/amd64.deb"},
    ]

    with patch("bot.update._arch_aliases", return_value={"amd64", "x86_64"}):
        selected = _select_linux_asset(assets, ".deb")

    assert selected is not None
    assert selected["name"].endswith("amd64.deb")


def test_detect_linux_package_kind_deb():
    from bot.update import _detect_linux_package_kind

    with (
        patch("bot.update.shutil.which", side_effect=lambda x: "/usr/bin/dpkg" if x == "dpkg" else None),
        patch("bot.update.subprocess.run") as mock_run,
    ):
        mock_run.return_value.returncode = 0
        kind = _detect_linux_package_kind()

    assert kind == "deb"


def test_detect_linux_package_kind_rpm():
    from bot.update import _detect_linux_package_kind

    def which(name: str):
        if name == "dpkg":
            return None
        if name == "rpm":
            return "/usr/bin/rpm"
        return None

    with (
        patch("bot.update.shutil.which", side_effect=which),
        patch("bot.update.subprocess.run") as mock_run,
    ):
        mock_run.return_value.returncode = 0
        kind = _detect_linux_package_kind()

    assert kind == "rpm"


def test_run_self_update_uses_linux_package_path_when_available():
    from bot.update import run_self_update

    release = {"tag_name": "v0.3.7", "assets": []}
    with (
        patch("bot.update._fetch_latest_release", return_value=release),
        patch("bot.update._update_linux_package_install", return_value=(True, "linux-updated")) as mock_linux,
        patch("bot.update._update_python_install", return_value=(True, "pip-updated")) as mock_pip,
        patch("bot.update.sys.platform", "linux"),
    ):
        ok, msg = run_self_update()

    assert ok is True
    assert msg == "linux-updated"
    mock_linux.assert_called_once()
    mock_pip.assert_not_called()
