# Inzen-Bot Roadmap

A running list of planned improvements and future features.

## Features

- [x] **Token/cost tracking** — per-message and cumulative totals, broken down by provider
- [x] **Session listing improvements** — show provider used and first message as a preview
- [x] **Session export** — dump a session to markdown or plain text
- [x] **Interactive mode** — `bot --chat` for a persistent REPL instead of one-shot messages
- [x] **System prompt override** — `--system` flag to replace the default prompt per query

## Developer Experience

- [x] **CI on every push** — run tests and ruff check on every PR and push to main, not just tags
- [x] **Automatic version bumping** — e.g. `bump-my-version` so the version is never out of sync with the tag
- [x] **Changelog generation** — e.g. `git-cliff` to auto-generate a changelog from conventional commits

## Distribution

- [ ] **Homebrew formula** — so Mac users can `brew install inzen-bot`
- [ ] **Windows installer / winget package** — native Windows distribution
- [ ] **Docker image** — for containerised or server environments

## Security
- [x] **Security baseline hardening** — lock down local storage permissions for `~/.bot` and session/history files to user-only access
- [x] **Session name validation** — reject path traversal and unsafe filenames for `--session`, `--clear-session`, and `--export`
- [ ] **Safe export paths** — add `--safe-output` mode (default on) to block writing exports outside allowed directories
- [ ] **Secrets redaction in output** — optional `--redact-secrets` mode to mask common API key/token patterns in exports/history views
- [ ] **Data retention controls** — add configurable retention policy and `--purge` command for old session/history/usage data
- [ ] **Provider endpoint allowlist** — restrict custom `base_url` values to https and optionally to trusted hosts
- [ ] **Network safety defaults** — request timeout, retry caps, and clearer network error classes for all providers
- [ ] **Prompt safety guardrails** — optional local prompt-injection warnings for dangerous command suggestions before display
- [ ] **Dependency and supply-chain checks** — add `uv lock` hygiene checks plus `pip-audit` in CI
- [ ] **Security policy and disclosure docs** — add `SECURITY.md` with reporting process, supported versions, and response SLAs
- [ ] **Structured security logging** — add local security event log (redacted) for export, clear, and config-changing actions
- [ ] **Threat model and abuse tests** — maintain a lightweight threat model and add regression tests for traversal, malformed JSON, and hostile prompts