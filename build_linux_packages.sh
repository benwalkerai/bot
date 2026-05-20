#!/usr/bin/env bash
set -euo pipefail

uv run python tools/build_linux_packages.py "$@"