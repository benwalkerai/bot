# Contributing to inzen-bot

Thanks for your interest in contributing.

## Getting started

### Prerequisites

- Python 3.12+
- [uv](https://github.com/astral-sh/uv)
- Git
- Optional on Windows for packaging:
- [PyInstaller](https://pyinstaller.org/)
- [Inno Setup](https://jrsoftware.org/isinfo.php) or [NSIS](https://nsis.sourceforge.io/)

### Setup

```bash
git clone https://github.com/yourusername/bot.git
cd bot
uv sync --extra dev
uv run pytest -v
```

### Running locally

```bash
bot --setup
bot --help
bot hello
```

Use `bot --setup` to enable providers and store API keys securely in the OS keyring.

## Project structure

```text
bot/
    bot/
        main.py
        config.py
        credentials.py
        setup.py
        providers/
    tests/
    pyproject.toml
    README.md
```

## Making changes

Create a branch:

```bash
git checkout -b feat/your-feature-name
```

Run checks before opening a PR:

```bash
uv run ruff check .
uv run pytest -v
```

## Windows packaging

Build EXE:

```bash
build_exe.bat
```

Build installer:

- Open `installer.iss` in Inno Setup
- Compile to produce installer EXE

## Security and secrets

- Never commit real API keys or secrets.
- `.env.example` is safe to commit; `.env` is ignored.
- API keys should be stored via `bot --setup` or `--credentials-update`, which use OS keyring storage.

## Credential commands

```bash
bot --credentials-list
bot --credentials-update anthropic
bot --credentials-remove anthropic
```

## Adding a new provider

1. Add a provider class under `bot/providers/` inheriting from `BaseProvider`.
2. Register it in `bot/providers/__init__.py`.
3. Add default settings in `bot/config.py`.
4. Add tests in `tests/test_providers.py` and `tests/test_main.py`.
5. Update README usage/setup docs.

## Submitting a pull request

1. Push your branch.
2. Open a PR with a clear summary.
3. Ensure tests pass.
4. Link related issues.

## Reporting bugs

Open a GitHub issue with:

- OS and Python version
- Command run
- Full error output
- Provider used
