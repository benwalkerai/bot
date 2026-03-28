# inzen-bot 🤖

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

Set your API key as an environment variable. Add to your `~/.bashrc` or `~/.zshrc`:

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
export OPENAI_API_KEY="sk-..."        # optional
```

Reload your shell:

```bash
source ~/.bashrc
```

For Ollama and llama.cpp no API key is needed — just make sure the server is running.

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

## Providers

| Provider    | Requires             | Notes                                          |
|-------------|----------------------|------------------------------------------------|
| `anthropic` | `ANTHROPIC_API_KEY`  | Default. Claude models.                        |
| `openai`    | `OPENAI_API_KEY`     | GPT models. Also works for Groq, Together etc. |
| `ollama`    | Ollama running       | Local inference. Free to run.                  |
| `llamacpp`  | llama.cpp running    | Local inference via OpenAI-compatible server.  |

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
# Build llama.cpp, then run the server:
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
└── history_ollama.json
```

Each provider keeps its own history so context doesn't bleed across models.

You can edit `~/.bot/config.json` directly to add custom providers or point the OpenAI provider at any OpenAI-compatible endpoint:

```json
{
  "provider": "anthropic",
  "providers": {
    "anthropic": { "model": "claude-haiku-4-5", "api_key_env": "ANTHROPIC_API_KEY" },
    "openai":    { "model": "gpt-4o",           "api_key_env": "OPENAI_API_KEY" },
    "groq":      { "model": "mixtral-8x7b-32768", "api_key_env": "GROQ_API_KEY",
                   "base_url": "https://api.groq.com/openai/v1" },
    "ollama":    { "model": "llama3",  "base_url": "http://localhost:11434" },
    "llamacpp":  { "model": "local",   "base_url": "http://localhost:8080" }
  }
}
```

History is capped at 50 message pairs per provider to keep API costs under control.

---

## Cross-platform

Works on Linux, macOS, and Windows. Config and history paths resolve correctly on all platforms via `Path.home()`.

---

## Requirements

- Python 3.12+
- `anthropic` — Anthropic/Claude provider
- `openai` — OpenAI and llama.cpp providers
- `rich` — terminal rendering
- `click` — CLI framework

---

## Built by

[Inzen](https://inzen.ai) — AI consulting and LLM application development.

---

## License

GPL-3.0
