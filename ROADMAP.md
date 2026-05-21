# Inzen CLI Bot Roadmap

A running list of planned improvements and future features.

## Features

- [x] **Token/cost tracking** — per-message and cumulative totals, broken down by provider
- [x] **Session listing improvements** — show provider used and first message as a preview
- [x] **Session export** — dump a session to markdown or plain text
- [x] **Interactive mode** — `bot --chat` for a persistent REPL instead of one-shot messages
- [x] **System prompt override** — `--system` flag to replace the default prompt per query
- [x] **Provider endpoint CLI editing** — add `--set-ollama-url` and `--set-llamacpp-url` to update local provider URLs without opening config files
- [ ] **Provider failover and fallback order** — allow a prioritized provider chain (e.g. ollama -> openai -> anthropic) when one provider is unavailable
- [ ] **Session tags and search** — add tags plus full-text search across saved sessions
- [ ] **Prompt/template library** — save reusable prompts and run them via named shortcuts
- [ ] **One-shot file context mode** — include selected local files in a single query without persisting file contents in history
- [ ] **Config profile switching** — support named profiles (work, personal, offline) with quick `--profile` switching

## Developer Experience

- [x] **CI on every push** — run tests and ruff check on every PR and push to main, not just tags
- [x] **Automatic version bumping** — e.g. `bump-my-version` so the version is never out of sync with the tag
- [x] **Changelog generation** — e.g. `git-cliff` to auto-generate a changelog from conventional commits
- [ ] **Typed config schema validation** — add strict validation with clearer diagnostics for malformed config files
- [ ] **Command telemetry opt-in** — optional anonymous usage metrics to guide feature prioritization
- [ ] **End-to-end CLI smoke tests** — run matrix smoke tests for common command flows in CI across OSes

## Distribution

- [ ] **MacOS installer** — so Mac users can run the bot in terminal
- [x] **Windows installer / winget package** — native Windows distribution
- [x] ** Linux packages** - so Linux users can download and install
- [ ] **Homebrew formula** — first-class install/update path for macOS and Linux users
- [ ] **Signed release artifacts** — publish checksums and signature verification instructions for all release assets
- [ ] **Delta update support** — reduce update download size for installer-based updates

## Security
- [x] **Security baseline hardening** — lock down local storage permissions for `~/.bot` and session/history files to user-only access
- [x] **Session name validation** — reject path traversal and unsafe filenames for `--session`, `--clear-session`, and `--export`
- [x] **Safe export paths** — add `--safe-output` mode (default on) to block writing exports outside allowed directories
- [x] **Secrets redaction in output** — optional `--redact-secrets` mode to mask common API key/token patterns in exports/history views
- [x] **Data retention controls** — add configurable retention policy and `--purge` command for old session/history/usage data
- [x] **Provider endpoint allowlist** — restrict custom `base_url` values to https and optionally to trusted hosts
- [x] **Network safety defaults** — request timeout, retry caps, and clearer network error classes for all providers
- [x] **Prompt safety guardrails** — optional local prompt-injection warnings for dangerous command suggestions before display
- [x] **Dependency and supply-chain checks** — add `uv lock` hygiene checks plus `pip-audit` in CI
- [x] **Security policy and disclosure docs** — add `SECURITY.md` with reporting process, supported versions, and response SLAs
- [x] **Structured security logging** — add local security event log (redacted) for export, clear, and config-changing actions
- [x] **Threat model and abuse tests** — maintain a lightweight threat model and add regression tests for traversal, malformed JSON, and hostile prompts
- [x] **In-app insecure HTTP controls** — add `--allow-insecure-http` / `--no-allow-insecure-http` and setup prompts when Ollama/llama.cpp use insecure non-local URLs
- [ ] **Per-provider certificate pinning** — optional TLS pinning for remote provider endpoints
- [ ] **Encrypted local session store** — optional passphrase-based encryption at rest for session/history files
- [ ] **Security profile presets** — quick presets for strict, balanced, and local-only modes

## Automation
- [x] **Automate package creation**
- [x] **Automate package updates in GitHub**
- [x] **In-app updater command** — add `bot --update` to fetch the latest GitHub release and auto-install (Python package or Windows installer)
- [x] **Package-aware in-app updates** — make `bot --update` auto-install latest Linux `.deb`/`.rpm` assets when package installs are detected
- [ ] **Rollback command for failed updates** — add `bot --rollback` to return to the previous installed version
- [ ] **Scheduled background update checks** — optional periodic checks with notify-only mode before install
