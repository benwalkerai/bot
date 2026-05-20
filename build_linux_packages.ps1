#!/usr/bin/env pwsh
# Build Linux .deb and .rpm packages on Windows.
# nfpm works cross-platform so packages can be created locally without a Linux VM.
#
# One-time setup: install nfpm
#   scoop install nfpm          (if you have Scoop)
#   choco install nfpm          (if you have Chocolatey)
#   winget install GoReleaser.nfpm
#   -- or --
#   # Direct binary download (no package manager required):
#   $url = "https://github.com/goreleaser/nfpm/releases/download/v2.43.2/nfpm_2.43.2_Windows_x86_64.zip"
#   Invoke-WebRequest $url -OutFile "$env:TEMP\nfpm.zip"
#   Expand-Archive "$env:TEMP\nfpm.zip" -DestinationPath "$env:LOCALAPPDATA\nfpm" -Force
#   $env:PATH += ";$env:LOCALAPPDATA\nfpm"   # Add to PATH for this session
#
# Usage:
#   .\build_linux_packages.ps1 [-Arch amd64] [-Binary path\to\binary] [-SkipBuild] [-SkipPackage]

param(
    [string]$Arch = "amd64",
    [string]$Binary = "",
    [switch]$SkipBuild,
    [switch]$SkipPackage
)

$ErrorActionPreference = "Stop"

$args_list = @("--arch", $Arch)

if ($Binary) {
    $args_list += @("--binary", $Binary)
}
if ($SkipBuild) {
    $args_list += "--skip-build"
}
if ($SkipPackage) {
    $args_list += "--skip-package"
}

uv run python tools/build_linux_packages.py @args_list
