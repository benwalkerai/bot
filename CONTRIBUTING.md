# Contributing to inzen-bot

Thanks for your interest in contributing! This document covers everything you need to get started.

---

## Getting started

### Prerequisites

- Python 3.12+
- [uv](https://github.com/astral-sh/uv) for dependency management
- Git

### Setup

```bash
# Clone the repo
git clone https://github.com/yourusername/bot.git
cd bot

# Create the venv and install all dependencies including dev tools
uv sync --extra dev

# Verify everything is working
uv run pytest -v
```

### Running the bot locally

```bash
# Activate the venv
source .venv/bin/activate

# Set your API key
export ANTHROPIC_API_KEY="sk-ant-..."

# Run
bot --help
bot what is the ls command
```

---

## Project structure

```
bot/
├── bot/
│   ├── __init__.py        # package version
│   ├── main.py            # CLI entry point (Click)
│   ├── config.py          # config and history management
│   └── providers/
│       ├── __init__.py    # provider registry
│       ├── base.py        # abstract base class
│       ├── anthropic.py   # Anthropic/Claude provider
│       ├── openai.py      # OpenAI provider (also Groq, Together etc.)
│       ├── ollama.py      # Ollama local inference
│       └── llamacpp.py    # llama.cpp local inference
├── tests/
│   ├── test_config.py
│   ├── test_providers.py
│   └── test_main.py
├── pyproject.toml
└── README.md
```

---

## Making changes

### Branching

Create a branch for your change:

```bash
git checkout -b feat/your-feature-name
# or
git checkout -b fix/your-bug-fix
```

### Running tests

Always run the full test suite before submitting:

```bash
uv run pytest -v
```

All tests must pass. If you're adding a feature, add tests for it. If you're fixing a bug, add a test that would have caught it.

### Code style

- Follow existing patterns in the codebase
- Add type hints to all functions
- Keep functions small and focused
- Use descriptive variable names

---

## Adding a new provider

This is the most common contribution. Here's how:

**1.** Create `bot/providers/yourprovider.py` inheriting from `BaseProvider`:

```python
"""Your provider."""

from typing import Iterator
from .base import BaseProvider


class YourProvider(BaseProvider):
    def __init__(self, config: dict):
        self.model = config.get("model", "default-model-name")
        # initialise your client here

    def stream_chat(self, messages: list[dict], system: str) -> Iterator[str]:
        # yield text chunks here
        yield "your response"
```

**2.** Register it in `bot/providers/__init__.py`:

```python
from .yourprovider import YourProvider

PROVIDERS: dict[str, type[BaseProvider]] = {
    ...
    "yourprovider": YourProvider,
}
```

**3.** Add default config in `bot/config.py`:

```python
"yourprovider": {
    "model": "default-model-name",
    "base_url": "http://...",  # if applicable
},
```

**4.** Add tests in `tests/test_providers.py`.

**5.** Update `README.md` with setup instructions for the new provider.

---

## Submitting a pull request

1. Push your branch: `git push origin feat/your-feature-name`
2. Open a pull request on GitHub
3. Describe what you changed and why
4. Make sure all tests pass
5. Link any related issues

---

## Reporting bugs

Open an issue on GitHub and include:

- Your OS and Python version
- The command you ran
- The full error output
- Which provider you were using

---

## Feature requests

Open an issue with the `enhancement` label. Describe the use case — what problem does it solve and how would you use it day to day?

---

## Questions

Open an issue with the `question` label, or reach out via [Inzen](https://inzen.ai).
