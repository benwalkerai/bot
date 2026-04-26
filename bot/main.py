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
bot --system "You are a Python expert" explain decorators
bot --export myproject
bot --export myproject --format text
bot --export myproject --output myproject.md
bot --usage
"""

import sys
from datetime import datetime

import click
from rich.console import Console

from .config import (
    accumulate_usage,
    clear_history,
    clear_session,
    get_provider_config,
    list_sessions,
    load_config,
    load_history,
    load_session,
    load_session_with_meta,
    load_usage,
    save_config,
    save_history,
    save_session,
)
from .providers import PROVIDERS, get_provider

console = Console()

# Pricing in USD per 1M tokens: (input, output)
PRICING: dict[str, tuple[float, float]] = {
    "claude-haiku-4-5": (0.80, 4.00),
    "claude-sonnet-4-5": (3.00, 15.00),
    "claude-opus-4-5": (15.00, 75.00),
    "gpt-4o-mini": (0.15, 0.60),
    "gpt-4o": (2.50, 10.00),
}


def estimate_cost(model: str, input_tokens: int, output_tokens: int) -> float | None:
    rates = PRICING.get(model)
    if rates is None:
        return None
    return (input_tokens * rates[0] + output_tokens * rates[1]) / 1_000_000


SYSTEM_PROMPT = """
You are a helpful terminal assistant. The user is working in a command-line environment, likely on Linux, macOS or Windows. Keep answers concise and practical.
Format commands in code blocks. When giving multi-step instructions, number the steps clearly
so the user can follow along one step at a time. If the user says things like 'step 2?' or
'next?' they're continuing from the previous response - refer to context and continue.
"""


def format_export(name: str, history: list[dict], provider: str | None, fmt: str) -> str:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    if fmt == "markdown":
        lines = [f"# Session: {name}"]
        if provider:
            lines.append(f"Provider: {provider}")
        lines += [f"Exported: {ts}", "", "---", ""]
        for msg in history:
            role = "User" if msg["role"] == "user" else "Assistant"
            lines += [f"**{role}:** {msg['content']}", ""]
        return "\n".join(lines).rstrip() + "\n"
    else:  # text
        lines = [f"Session: {name}"]
        if provider:
            lines.append(f"Provider: {provider}")
        lines += [f"Exported: {ts}", "", "---", ""]
        for msg in history:
            role = "USER" if msg["role"] == "user" else "ASSISTANT"
            lines += [f"{role}: {msg['content']}", ""]
        return "\n".join(lines).rstrip() + "\n"


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
@click.option(
    "--system",
    "system_prompt",
    default=None,
    help="Override the system prompt for this query.",
)
@click.option(
    "--export",
    "export_session",
    default=None,
    help="Export a named session to stdout or a file.",
)
@click.option(
    "--format",
    "export_format",
    default="markdown",
    type=click.Choice(["markdown", "text"], case_sensitive=False),
    help="Export format: markdown (default) or text.",
)
@click.option(
    "--output",
    "output_file",
    default=None,
    help="Write export to this file instead of stdout.",
)
@click.option(
    "--usage",
    "show_usage",
    is_flag=True,
    help="Show cumulative token and cost totals per provider.",
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
    system_prompt: str | None,
    export_session: str | None,
    export_format: str,
    output_file: str | None,
    show_usage: bool,
) -> None:
    config = load_config()

    if show_usage:
        from .providers import PROVIDERS as _PROVIDERS
        any_data = False
        console.print("\n[bold]Token usage:[/bold]\n")
        console.print(f"  {'Provider':<12} {'Input':>10} {'Output':>10} {'Est. cost':>12}")
        console.print(f"  {'-'*12} {'-'*10} {'-'*10} {'-'*12}")
        for name in _PROVIDERS:
            data = load_usage(name)
            if data["input_tokens"] == 0 and data["output_tokens"] == 0:
                continue
            any_data = True
            cost = f"${data['cost_usd']:.4f}" if data["cost_usd"] else "n/a"
            console.print(
                f"  [cyan]{name:<12}[/cyan]"
                f" {data['input_tokens']:>10,}"
                f" {data['output_tokens']:>10,}"
                f" {cost:>12}"
            )
        if not any_data:
            console.print("  [dim]No usage recorded yet.[/dim]")
        console.print()
        return

    if export_session:
        meta = load_session_with_meta(export_session)
        if meta is None:
            console.print(f"[red]No session named '{export_session}' found.[/red]")
            sys.exit(1)
        if not meta["history"]:
            console.print(f"[yellow]Session '{export_session}' is empty.[/yellow]")
            return
        content = format_export(export_session, meta["history"], meta["provider"], export_format)
        if output_file:
            from pathlib import Path
            Path(output_file).write_text(content, encoding="utf-8")
            console.print(f"[green]Exported '{export_session}' to {output_file}[/green]")
        else:
            print(content, end="")
        return

    if list_sessions_flag:
        sessions = list_sessions()
        if not sessions:
            console.print("[dim]No saved sessions.[/dim]")
            return
        console.print("\n[bold]Saved sessions:[/bold]")
        for s in sessions:
            ts = datetime.fromtimestamp(s["modified"]).strftime("%Y-%m-%d %H:%M")
            provider_tag = f"[magenta]{s['provider']}[/magenta] · " if s.get("provider") else ""
            console.print(
                f"  [cyan]{s['name']}[/cyan]  "
                f"[dim]{provider_tag}{s['messages']} messages · {ts}[/dim]"
            )
            if s.get("preview"):
                console.print(f"  [dim]  {s['preview']}[/dim]")
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
    active_system = system_prompt if system_prompt is not None else SYSTEM_PROMPT
    model = config["providers"][active_provider].get("model", "")
    try:
        console.print()
        for chunk in prov.stream_chat(history, active_system):
            print(chunk, end="", flush=True)
            full_response += chunk
        print("\n")
        if prov.last_usage:
            in_tok = prov.last_usage["input_tokens"]
            out_tok = prov.last_usage["output_tokens"]
            cost = estimate_cost(model, in_tok, out_tok)
            cost_str = f" · ~${cost:.4f}" if cost is not None else ""
            console.print(f"[dim]↑ {in_tok:,} in · ↓ {out_tok:,} out{cost_str}[/dim]")
            accumulate_usage(active_provider, in_tok, out_tok, cost or 0.0)

    except ConnectionError as e:
        console.print(f"\n[red]Connection error:[/red] {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        console.print("\n[dim]Interrupted.[/dim]")
        if full_response:
            history.append({"role": "assistant", "content": full_response})
            if session_name:
                save_session(session_name, history, active_provider)
            else:
                save_history(active_provider, history)
        sys.exit(0)
    except Exception as e:
        console.print(f"\n[red]Error:[/red] {e}")
        sys.exit(1)

    history.append({"role": "assistant", "content": full_response})
    if session_name:
        save_session(session_name, history, active_provider)
    else:
        save_history(active_provider, history)