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
- [ ] **Automatic version bumping** — e.g. `bump-my-version` so the version is never out of sync with the tag
- [ ] **Changelog generation** — e.g. `git-cliff` to auto-generate a changelog from conventional commits

## Distribution

- [ ] **Homebrew formula** — so Mac users can `brew install inzen-bot`
- [ ] **Windows installer / winget package** — native Windows distribution
- [ ] **Docker image** — for containerised or server environments