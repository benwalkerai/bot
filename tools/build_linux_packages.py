from __future__ import annotations

import argparse
import os
import shutil
import stat
import subprocess
import sys
import textwrap
from pathlib import Path

import tomllib


ROOT = Path(__file__).resolve().parents[1]
DIST_DIR = ROOT / "dist" / "linux"
STAGE_DIR = DIST_DIR / "stage"
PAYLOAD_DIR = STAGE_DIR / "payload"
SCRIPTS_DIR = DIST_DIR / "scripts"


def load_project_metadata() -> dict[str, str]:
    with (ROOT / "pyproject.toml").open("rb") as handle:
        pyproject = tomllib.load(handle)

    project = pyproject["project"]
    urls = project.get("urls", {})
    return {
        "name": project["name"],
        "version": project["version"],
        "description": project["description"],
        "homepage": urls.get("Homepage", ""),
        "license": project.get("license", {}).get("text", ""),
    }


def normalize_arch(raw_arch: str | None) -> str:
    machine = (raw_arch or os.environ.get("NPM_ARCH") or os.environ.get("ARCH") or "").strip().lower()
    if not machine:
        machine = os.uname().machine.lower() if hasattr(os, "uname") else ""

    aliases = {
        "x86_64": "amd64",
        "amd64": "amd64",
        "aarch64": "arm64",
        "arm64": "arm64",
        "armv7l": "arm7",
        "armhf": "arm7",
    }
    normalized = aliases.get(machine)
    if normalized is None:
        supported = ", ".join(sorted(aliases))
        raise SystemExit(
            f"Unsupported architecture '{machine or raw_arch}'. Supported values: {supported}."
        )
    return normalized


def ensure_clean_dir(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def run(command: list[str]) -> None:
    subprocess.run(command, cwd=ROOT, check=True)


def build_binary(explicit_binary: str | None, skip_build: bool) -> Path:
    if explicit_binary:
        binary_path = Path(explicit_binary).expanduser().resolve()
        if not binary_path.is_file():
            raise SystemExit(f"Binary not found: {binary_path}")
        return binary_path

    if skip_build:
        raise SystemExit("--skip-build requires --binary to point at an existing standalone executable.")

    run(
        [
            "uv",
            "run",
            "pyinstaller",
            "--clean",
            "--noconfirm",
            "--onefile",
            "--name",
            "inzen_cli_bot",
            "run_inzen_cli_bot.py",
        ]
    )

    candidates = [ROOT / "dist" / "inzen_cli_bot", ROOT / "dist" / "inzen_cli_bot.exe"]
    for candidate in candidates:
        if candidate.is_file():
            return candidate.resolve()

    raise SystemExit("PyInstaller finished, but dist/inzen_cli_bot was not created.")


def stage_payload(binary_path: Path) -> Path:
    ensure_clean_dir(PAYLOAD_DIR)
    ensure_clean_dir(SCRIPTS_DIR)

    app_dir = PAYLOAD_DIR / "opt" / "inzen-cli-bot"
    doc_dir = PAYLOAD_DIR / "usr" / "share" / "doc" / "inzen-cli-bot"
    app_dir.mkdir(parents=True, exist_ok=True)
    doc_dir.mkdir(parents=True, exist_ok=True)

    staged_binary = app_dir / "inzen_cli_bot"
    shutil.copy2(binary_path, staged_binary)
    current_mode = staged_binary.stat().st_mode
    staged_binary.chmod(current_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    for doc_name in ("README.md", "CHANGELOG.md", "LICENSE"):
        source = ROOT / doc_name
        if source.exists():
            shutil.copy2(source, doc_dir / doc_name)

    install_notes = doc_dir / "INSTALL-LINUX.txt"
    install_notes.write_text(
        textwrap.dedent(
            """\
            Inzen CLI Bot Linux package

            Installed commands:
            - bot
            - inzen_cli_bot

            Recommended first step:
            - Run `bot --setup` to configure providers and store credentials.
            """
        ),
        encoding="utf-8",
    )

    for script_name in ("postinstall.sh", "postremove.sh"):
        source = ROOT / "packaging" / "linux" / script_name
        destination = SCRIPTS_DIR / script_name
        shutil.copy2(source, destination)
        destination.chmod(destination.stat().st_mode | stat.S_IXUSR)

    return staged_binary


def render_nfpm_config(metadata: dict[str, str], arch: str) -> Path:
    config_path = DIST_DIR / "nfpm.yaml"
    escaped_description = metadata["description"].replace("\n", " ").strip()
    config_path.write_text(
        textwrap.dedent(
            f"""\
            name: {metadata['name']}
            arch: {arch}
            platform: linux
            version: {metadata['version']}
            section: utils
            priority: optional
            maintainer: Inzen CLI Bot Maintainers
            description: |
              {escaped_description}
            homepage: {metadata['homepage']}
            license: {metadata['license']}
            contents:
              - src: ./stage/payload/opt/inzen-cli-bot/inzen_cli_bot
                dst: /opt/inzen-cli-bot/inzen_cli_bot
                file_info:
                  mode: 0755
              - src: ./stage/payload/usr/share/doc/inzen-cli-bot/README.md
                dst: /usr/share/doc/inzen-cli-bot/README.md
              - src: ./stage/payload/usr/share/doc/inzen-cli-bot/CHANGELOG.md
                dst: /usr/share/doc/inzen-cli-bot/CHANGELOG.md
              - src: ./stage/payload/usr/share/doc/inzen-cli-bot/LICENSE
                dst: /usr/share/doc/inzen-cli-bot/LICENSE
              - src: ./stage/payload/usr/share/doc/inzen-cli-bot/INSTALL-LINUX.txt
                dst: /usr/share/doc/inzen-cli-bot/INSTALL-LINUX.txt
              - src: /opt/inzen-cli-bot/inzen_cli_bot
                dst: /usr/bin/inzen_cli_bot
                type: symlink
              - src: /usr/bin/inzen_cli_bot
                dst: /usr/bin/bot
                type: symlink
            scripts:
              postinstall: ./scripts/postinstall.sh
              postremove: ./scripts/postremove.sh
            deb:
              compression: xz
            rpm:
              compression: xz
            """
        ),
        encoding="utf-8",
    )
    return config_path


def build_packages(metadata: dict[str, str], arch: str, config_path: Path) -> list[Path]:
    if shutil.which("nfpm") is None:
        raise SystemExit(
            "nfpm is required to produce .deb and .rpm files. Install it from https://nfpm.goreleaser.com/install/."
        )

    outputs: list[Path] = []
    for packager, extension in (("deb", "deb"), ("rpm", "rpm")):
        target = DIST_DIR / f"{metadata['name']}_{metadata['version']}_{arch}.{extension}"
        # nfpm resolves relative src: paths from cwd, so run it from DIST_DIR
        # where the nfpm.yaml and stage/ directory both live.
        subprocess.run(
            [
                "nfpm",
                "package",
                "--config",
                str(config_path),
                "--packager",
                packager,
                "--target",
                str(target),
            ],
            cwd=DIST_DIR,
            check=True,
        )
        outputs.append(target)
    return outputs


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build Linux .deb and .rpm packages for the standalone Inzen CLI Bot binary."
    )
    parser.add_argument(
        "--binary",
        help="Path to an existing standalone executable to package instead of rebuilding with PyInstaller.",
    )
    parser.add_argument(
        "--arch",
        help="Target Linux package architecture (for example: amd64, x86_64, arm64, aarch64).",
    )
    parser.add_argument(
        "--skip-build",
        action="store_true",
        help="Skip the PyInstaller step. Requires --binary.",
    )
    parser.add_argument(
        "--skip-package",
        action="store_true",
        help="Only stage files and render nfpm.yaml without invoking nfpm.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    metadata = load_project_metadata()
    arch = normalize_arch(args.arch)
    binary_path = build_binary(args.binary, args.skip_build)

    DIST_DIR.mkdir(parents=True, exist_ok=True)
    stage_payload(binary_path)
    config_path = render_nfpm_config(metadata, arch)

    print(f"Prepared Linux package staging in {DIST_DIR}")
    print(f"Rendered nfpm config: {config_path}")

    if args.skip_package:
        print("Skipping nfpm packaging as requested.")
        return 0

    outputs = build_packages(metadata, arch, config_path)
    for output in outputs:
        print(f"Created {output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())