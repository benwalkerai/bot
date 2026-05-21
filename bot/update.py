"""Self-update helpers for Inzen CLI Bot."""

from __future__ import annotations

import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen, urlretrieve

GITHUB_OWNER = "benwalkerai"
GITHUB_REPO = "bot"
LATEST_RELEASE_API = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/releases/latest"
GITHUB_TAG_ARCHIVE = (
    f"https://github.com/{GITHUB_OWNER}/{GITHUB_REPO}/archive/refs/tags/{{tag}}.tar.gz"
)
WINDOWS_INSTALLER_PREFIX = "inzen_cli_bot_installer_"
LINUX_PACKAGE_PREFIX = "inzen-bot_"


def _run_install_command(cmd: list[str]) -> tuple[bool, str]:
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0:
        return True, ""
    stderr = (result.stderr or result.stdout or "Unknown install failure").strip()
    return False, stderr


def _with_sudo_if_needed(cmd: list[str]) -> list[str]:
    if os.name != "posix":
        return cmd
    geteuid = getattr(os, "geteuid", None)
    if callable(geteuid) and geteuid() == 0:
        return cmd
    if shutil.which("sudo"):
        return ["sudo", *cmd]
    return cmd


def _fetch_latest_release(timeout: int = 15) -> dict:
    with urlopen(LATEST_RELEASE_API, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def _update_python_install(tag: str) -> tuple[bool, str]:
    archive_url = GITHUB_TAG_ARCHIVE.format(tag=tag)
    cmd = [sys.executable, "-m", "pip", "install", "--upgrade", archive_url]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0:
        return True, f"Updated from GitHub release {tag}."

    fallback = subprocess.run(
        [sys.executable, "-m", "pip", "install", "--upgrade", "inzen-bot"],
        capture_output=True,
        text=True,
    )
    if fallback.returncode == 0:
        return True, "Updated from package index fallback."

    stderr = (fallback.stderr or result.stderr or "Unknown update failure").strip()
    return False, f"Update failed: {stderr}"


def _select_windows_installer(assets: list[dict]) -> dict | None:
    for asset in assets:
        name = str(asset.get("name", ""))
        if name.startswith(WINDOWS_INSTALLER_PREFIX) and name.endswith("_windows_x64.exe"):
            return asset
    return None


def _arch_aliases() -> set[str]:
    machine = platform.machine().lower()
    aliases = {machine}
    if machine in {"x86_64", "amd64"}:
        aliases.update({"x86_64", "amd64"})
    elif machine in {"aarch64", "arm64"}:
        aliases.update({"aarch64", "arm64"})
    return aliases


def _select_linux_asset(assets: list[dict], ext: str) -> dict | None:
    aliases = _arch_aliases()
    pattern = re.compile(
        rf"^{re.escape(LINUX_PACKAGE_PREFIX)}.+_([A-Za-z0-9_]+){re.escape(ext)}$"
    )
    fallback: dict | None = None
    for asset in assets:
        name = str(asset.get("name", ""))
        if not (name.startswith(LINUX_PACKAGE_PREFIX) and name.endswith(ext)):
            continue
        fallback = fallback or asset
        match = pattern.match(name)
        if not match:
            continue
        arch = match.group(1).lower()
        if arch in aliases:
            return asset
    return fallback


def _detect_linux_package_kind() -> str | None:
    if shutil.which("dpkg"):
        result = subprocess.run(
            ["dpkg", "-s", "inzen-bot"],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            return "deb"
    if shutil.which("rpm"):
        result = subprocess.run(
            ["rpm", "-q", "inzen-bot"],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            return "rpm"
    return None


def _install_linux_deb(path: Path) -> tuple[bool, str]:
    if shutil.which("apt-get"):
        cmd = _with_sudo_if_needed(["apt-get", "install", "-y", str(path)])
        ok, err = _run_install_command(cmd)
        if ok:
            return True, "Installed latest .deb package via apt-get."
        return False, f"apt-get install failed: {err}"

    if shutil.which("dpkg"):
        cmd = _with_sudo_if_needed(["dpkg", "-i", str(path)])
        ok, err = _run_install_command(cmd)
        if ok:
            return True, "Installed latest .deb package via dpkg."
        return False, f"dpkg install failed: {err}"

    return False, "No supported .deb installer found (apt-get or dpkg)."


def _install_linux_rpm(path: Path) -> tuple[bool, str]:
    if shutil.which("dnf"):
        cmd = _with_sudo_if_needed(["dnf", "install", "-y", str(path)])
        ok, err = _run_install_command(cmd)
        if ok:
            return True, "Installed latest .rpm package via dnf."
        return False, f"dnf install failed: {err}"

    if shutil.which("yum"):
        cmd = _with_sudo_if_needed(["yum", "install", "-y", str(path)])
        ok, err = _run_install_command(cmd)
        if ok:
            return True, "Installed latest .rpm package via yum."
        return False, f"yum install failed: {err}"

    if shutil.which("zypper"):
        cmd = _with_sudo_if_needed(["zypper", "--non-interactive", "install", str(path)])
        ok, err = _run_install_command(cmd)
        if ok:
            return True, "Installed latest .rpm package via zypper."
        return False, f"zypper install failed: {err}"

    if shutil.which("rpm"):
        cmd = _with_sudo_if_needed(["rpm", "-Uvh", str(path)])
        ok, err = _run_install_command(cmd)
        if ok:
            return True, "Installed latest .rpm package via rpm."
        return False, f"rpm install failed: {err}"

    return False, "No supported .rpm installer found (dnf, yum, zypper, or rpm)."


def _update_linux_package_install(release: dict) -> tuple[bool, str]:
    package_kind = _detect_linux_package_kind()
    if package_kind not in {"deb", "rpm"}:
        return False, "Could not detect an installed inzen-bot .deb/.rpm package on this system."

    assets = release.get("assets", []) or []
    ext = ".deb" if package_kind == "deb" else ".rpm"
    asset = _select_linux_asset(assets, ext)
    if not asset:
        return False, f"No {ext} asset found in latest GitHub release for this platform."

    download_url = str(asset.get("browser_download_url", "")).strip()
    if not download_url:
        return False, f"Latest {ext} asset has no download URL."

    target = Path(tempfile.gettempdir()) / str(asset.get("name", f"inzen_update{ext}"))
    urlretrieve(download_url, target)

    if package_kind == "deb":
        return _install_linux_deb(target)
    return _install_linux_rpm(target)


def _update_windows_standalone(release: dict) -> tuple[bool, str]:
    assets = release.get("assets", []) or []
    installer = _select_windows_installer(assets)
    if not installer:
        return False, "No Windows installer asset found in latest GitHub release."

    download_url = str(installer.get("browser_download_url", "")).strip()
    if not download_url:
        return False, "Latest Windows installer has no download URL."

    target = Path(tempfile.gettempdir()) / str(installer.get("name", "inzen_update.exe"))
    urlretrieve(download_url, target)

    # Inno Setup supports silent install flags; launch and return immediately.
    subprocess.Popen([str(target), "/VERYSILENT", "/NORESTART"])
    return True, f"Launched installer update from {download_url}"


def run_self_update() -> tuple[bool, str]:
    """Run self-update and return (success, message)."""
    try:
        release = _fetch_latest_release()
    except URLError as e:
        return False, f"Could not contact GitHub releases API: {e}"
    except Exception as e:
        return False, f"Failed to fetch release metadata: {e}"

    tag = str(release.get("tag_name", "")).strip()
    if not tag:
        return False, "Latest release metadata missing tag_name."

    if getattr(sys, "frozen", False) and sys.platform == "win32":
        try:
            return _update_windows_standalone(release)
        except Exception as e:
            return False, f"Windows installer update failed: {e}"

    if sys.platform.startswith("linux") and getattr(sys, "frozen", False):
        try:
            return _update_linux_package_install(release)
        except Exception as e:
            return False, f"Linux package update failed: {e}"

    if sys.platform.startswith("linux"):
        try:
            package_update = _update_linux_package_install(release)
            if package_update[0]:
                return package_update
        except Exception:
            # Fall through to Python package update if package manager path is unavailable.
            pass

    try:
        return _update_python_install(tag)
    except Exception as e:
        return False, f"Python package update failed: {e}"
