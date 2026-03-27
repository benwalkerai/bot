"""
bot - multi-provider chatbot for the terminal.

Usage examples:
bot what is the fdisk command to list drives
bot --provider openai explain LVM volumes
bot --set-provider ollama
bot --set-model llama3.2
bot --clear
bot --history
bot --providers
"""

import sys
import click
from rich.console import Console
from .config import (
    load_config,
    save_config,
    load_history,
    save_history,
    clear_history,
    get_provider_config,
)
from .providers import get_provider, PROVIDERS

console = Console()

SYSTEM_PROMPT = """
You are a helpful terminal assistant. The user is working in a command-line environment, likely on Linux, macOS or Windows. Keep answers concise and practical.
Format commands in code blocks. When giving multi-step instructions, number the steps clearly
so the user can follow along one step at a time. If the user says things like 'step 2?' or
'next?' they're continuing from the previous response - refer to context and continue.
"""

def resolve_provider(config: dict, override: str | None) -> str:
    name = override or config.get("provider", "anthropic")
    if name not in PROVIDERS:
        console.print(
            f"[red]Unknown provider '{name}'."
            f"Available: {', '.join(PROVIDERS.keys())}[/red]"
        )
        sys.exit(1)
    return name