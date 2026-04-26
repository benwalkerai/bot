# inzen-bot 🤖

[![PyPI Downloads](https://static.pepy.tech/personalized-badge/inzen-bot?period=total&units=INTERNATIONAL_SYSTEM&left_color=BLACK&right_color=GREEN&left_text=downloads)](https://pepy.tech/projects/inzen-bot)
![Python Version](https://img.shields.io/badge/python-3.12%2B-blue)

A multi-provider AI chatbot for the terminal. Chat with Claude, GPT-4, Ollama, or llama.cpp without leaving your shell — with full conversation history so you can follow multi-step instructions one command at a time.

```
$ bot how do I format a drive in Ubuntu?

Step 1: List your drives to identify the correct device:
  sudo fdisk -l

$ bot step 2?

Step 2: Unmount the partition if it's currently mounted:
  sudo umount /dev/sdX1

$ bot step 3?

Step 3: Format the drive with your chosen filesystem:
  sudo mkfs.ext4 /dev/sdX
```

No browser. No switching apps. Just ask and keep working.

---

## Contents

- [Install](#install)
- [Setup](#setup)
- [Usage](#usage)
- [Named Sessions](#named-sessions)
- [Providers](#providers)
- [Configuration](#configuration)
- [Requirements](#requirements)
- [Contributing](#contributing)
- [Releasing to PyPI](#releasing-to-pypi)

---

## Install

```bash
pip install inzen-bot
```

Or with [uv](https://github.com/astral-sh/uv):

```bash
uv add inzen-bot
```

---

## Setup

### 1. Set your API key

inzen-bot reads your API keys from environment variables.

**Linux / macOS** — add to your `~/.bashrc` or `~/.zshrc`:

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
export OPENAI_API_KEY="sk-..."        # optional
```

Then reload:

```bash
source ~/.bashrc
```

**Windows (PowerShell)** — set permanently:

```powershell
[System.Environment]::SetEnvironmentVariable("ANTHROPIC_API_KEY", "sk-ant-...", "User")
```

Restart your terminal after running this.

> For Ollama and llama.cpp no API key is needed — just make sure the local server is running before use.

### 2. Verify it works

```bash
bot hello
```

You should see a response from Claude. If you get an error, check your API key is set correctly with:

```bash
# Linux / macOS
echo $ANTHROPIC_API_KEY

# Windows PowerShell
echo $env:ANTHROPIC_API_KEY
```

---

## Usage

```bash
# Ask anything
bot what is the mkfs command

# Follow up — history is automatic
bot what does the -t flag do
bot next step?

# Use a specific provider for one query
bot --provider openai explain RAID levels

# Switch default provider
bot --set-provider ollama

# Switch model
bot --set-model claude-opus-4-5

# View conversation history
bot --history

# Clear history
bot --clear

# List all configured providers
bot --providers
```

---

## Named Sessions

Named sessions let you maintain separate, persistent conversation threads — useful for keeping different projects or topics isolated.

```bash
# Start or continue a named session
bot --session myproject what is a venv

# Pick up where you left off
bot --session myproject how do I activate it

# List all saved sessions
bot --sessions

# Delete a session
bot --clear-session myproject
```

Sessions are stored as JSON files in `~/.bot/sessions/` and are independent of provider — you can switch providers mid-session.

---

## Providers

| Provider    | Requires            | Notes                                           |
|-------------|---------------------|-------------------------------------------------|
| `anthropic` | `ANTHROPIC_API_KEY` | Default. Claude models.                         |
| `openai`    | `OPENAI_API_KEY`    | GPT models. Also works for Groq, Together, etc. |
| `ollama`    | Ollama running      | Local inference. Free to run.                   |
| `llamacpp`  | llama.cpp running   | Local inference via OpenAI-compatible server.   |

### Ollama quickstart

```bash
# Install from https://ollama.ai, then:
ollama pull llama3
ollama serve
bot --set-provider ollama
bot hello from the terminal
```

### llama.cpp quickstart

```bash
# Build llama.cpp from https://github.com/ggerganov/llama.cpp, then run the server:
./server -m your-model.gguf --port 8080
bot --set-provider llamacpp
bot what is quantisation
```

---

## Configuration

Config and history live in `~/.bot/`:

```
~/.bot/
├── config.json               # provider settings and defaults
├── history_anthropic.json    # conversation history per provider
├── history_openai.json
├── history_ollama.json
└── sessions/                 # named sessions
    └── myproject.json
```

Each provider keeps its own history so context doesn't bleed across models. History is capped at 50 message pairs per provider to keep context and API costs under control.

You can edit `~/.bot/config.json` directly to add custom providers or point the OpenAI provider at any OpenAI-compatible endpoint:

```json
{
  "provider": "anthropic",
  "providers": {
    "anthropic": { "model": "claude-haiku-4-5",       "api_key_env": "ANTHROPIC_API_KEY" },
    "openai":    { "model": "gpt-4o",                 "api_key_env": "OPENAI_API_KEY" },
    "groq":      { "model": "mixtral-8x7b-32768",     "api_key_env": "GROQ_API_KEY",
                   "base_url": "https://api.groq.com/openai/v1" },
    "ollama":    { "model": "llama3",  "base_url": "http://localhost:11434" },
    "llamacpp":  { "model": "local",   "base_url": "http://localhost:8080"  }
  }
}
```

---

## Requirements

- Python 3.12+
- `anthropic` — Anthropic/Claude provider
- `openai` — OpenAI and llama.cpp providers
- `rich` — terminal rendering
- `click` — CLI framework

---

## Cross-platform

Works on Linux, macOS, and Windows. Config and history paths resolve correctly on all platforms via `Path.home()`.

---

## Built by

[Inzen](https://inzen.ai) — AI consulting and LLM application development.

---

## Contributing

```bash
git clone https://github.com/benwalkerai/bot
cd bot
uv sync --group dev
uv run pytest          # run tests
uv run ruff check .    # lint
```

CI runs automatically on every push and pull request via GitHub Actions — tests and ruff must pass before merging.

---

## Releasing to PyPI

1. **Bump the version** in `pyproject.toml`:

   ```toml
   [project]
   version = "0.3.0"
   ```

2. **Commit the change:**

   ```bash
   git add pyproject.toml
   git commit -m "chore: bump version to 0.3.0"
   git push
   ```

3. **Tag the release** — this is what triggers the PyPI publish workflow:

   ```bash
   git tag v0.3.0
   git push --tags
   ```

The `publish.yml` GitHub Actions workflow will run the tests, build the package, and publish to PyPI automatically using the `PYPI_API_TOKEN` secret. A regular `git push` without a tag only triggers CI — it will never publish to PyPI.

---

## License

GPL-3.0
