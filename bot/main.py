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
bot --session myproject what is a venv
bot --sessions
bot --clear-session myproject
"""

import sys
from datetime import datetime

import click
from rich.console import Console

from .config import (
    clear_history,
    clear_session,
    get_provider_config,
    list_sessions,
    load_config,
    load_history,
    load_session,
    save_config,
    save_history,
    save_session,
)
from .providers import PROVIDERS, get_provider

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


@click.command(context_settings={"ignore_unknown_options": True})
@click.argument("message", nargs=-1)
@click.option("--provider", "-p", default=None, help="Provider to use for this query.")
@click.option("--set-provider", default=None, help="Set the default provider.")
@click.option(
    "--set-model", default=None, help="Set the model for the current provider."
)
@click.option("--clear", "do_clear", is_flag=True, help="Clear conversation history.")
@click.option(
    "--history", "show_history", is_flag=True, help="Print conversation history"
)
@click.option(
    "--providers", "list_providers", is_flag=True, help="List all configured providers"
)
@click.option("--session", "session_name", default=None, help="Named session to use.")
@click.option(
    "--sessions", "list_sessions_flag", is_flag=True, help="List saved sessions."
)
@click.option(
    "--clear-session",
    "clear_session_name",
    default=None,
    help="Delete a named session.",
)
def cli(
    message: tuple,
    provider: str | None,
    set_provider: str | None,
    set_model: str | None,
    do_clear: bool,
    show_history: bool,
    list_providers: bool,
    session_name: str | None,
    list_sessions_flag: bool,
    clear_session_name: str | None,
) -> None:
    config = load_config()

    if list_sessions_flag:
        sessions = list_sessions()
        if not sessions:
            console.print("[dim]No saved sessions.[/dim]")
            return
        console.print("\n[bold]Saved sessions:[/bold]")
        for s in sessions:
            ts = datetime.fromtimestamp(s["modified"]).strftime("%Y-%m-%d %H:%M")
            console.print(
                f"  [cyan]{s['name']}[/cyan]  "
                f"[dim]{s['messages']} messages · {ts}[/dim]"
            )
        console.print()
        return

    if clear_session_name:
        clear_session(clear_session_name)
        console.print(f"[green]Session '{clear_session_name}' cleared.[/green]")
        return

    if list_providers:
        current = config.get("provider", "anthropic")
        console.print("\n[bold]Configured providers:[/bold]")
        for name, cfg in config["providers"].items():
            marker = "●" if name == current else " "
            model = cfg.get("model", "?")
            base = f"  [dim]{cfg['base_url']}[/dim]" if "base_url" in cfg else ""
            console.print(f"  {marker} [cyan]{name}[/cyan]  {model}{base}")
        console.print(f"\n  [dim]Default: {current}[/dim]\n")
        return

    if set_provider:
        if set_provider not in PROVIDERS:
            console.print(
                f"[red]Unknown provider '{set_provider}'. "
                f"Available: {', '.join(PROVIDERS.keys())}[/red]"
            )
            sys.exit(1)
        config["provider"] = set_provider
        save_config(config)
        console.print(f"[green]Default provider set to '{set_provider}'.[/green]")
        return

    if set_model:
        active = resolve_provider(config, provider)
        config["providers"][active]["model"] = set_model
        save_config(config)
        console.print(f"[green]Model for '{active}' set to '{set_model}'.[/green]")
        return

    active_provider = resolve_provider(config, provider)

    if do_clear:
        clear_history(active_provider)
        console.print(f"[green]History cleared for '{active_provider}'.[/green]")
        return

    if show_history:
        history = load_history(active_provider)
        if not history:
            console.print(f"[dim]No history for '{active_provider}'.[/dim]")
            return
        console.print(f"\n[bold]History for '{active_provider}':[/bold]\n")
        for msg in history:
            role = msg["role"].upper()
            colour = "cyan" if msg["role"] == "user" else "green"
            console.print(f"[{colour}][{role}][/{colour}] {msg['content']}\n")
        return

    if not message:
        console.print(
            "[yellow]Usage:[/yellow] bot [OPTIONS] YOUR MESSAGE\n"
            "       bot --help  for all options"
        )
        sys.exit(0)

    user_text = " ".join(message)
    history = load_session(session_name) if session_name else load_history(active_provider)
    history.append({"role": "user", "content": user_text})

    try:
        provider_config = get_provider_config(config, active_provider)
        prov = get_provider(active_provider, provider_config)
    except (OSError, ValueError, ImportError) as e:
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)

    full_response = ""
    try:
        console.print()
        for chunk in prov.stream_chat(history, SYSTEM_PROMPT):
            print(chunk, end="", flush=True)
            full_response += chunk
        print("\n")

    except ConnectionError as e:
        console.print(f"\n[red]Connection error:[/red] {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        console.print("\n[dim]Interrupted.[/dim]")
        if full_response:
            history.append({"role": "assistant", "content": full_response})
            if session_name:
                save_session(session_name, history)
            else:
                save_history(active_provider, history)
        sys.exit(0)
    except Exception as e:
        console.print(f"\n[red]Error:[/red] {e}")
        sys.exit(1)

    history.append({"role": "assistant", "content": full_response})
    if session_name:
        save_session(session_name, history)
    else:
        save_history(active_provider, history)