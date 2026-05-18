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
bot --chat
bot --session myproject --chat
"""

import re
import sys
from datetime import datetime
from pathlib import Path

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
    log_security_event,
    purge_old_data,
    save_config,
    save_history,
    save_session,
    validate_session_name,
)
from .providers import PROVIDERS, get_provider
from .providers.base import ProviderConnectionError, ProviderTimeoutError

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

SECRET_PATTERNS = [
    re.compile(r"\bsk-[A-Za-z0-9_-]{10,}\b"),
    re.compile(r"\bsk-ant-[A-Za-z0-9_-]{10,}\b"),
    re.compile(r"\bghp_[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bAIza[0-9A-Za-z\\-_]{20,}\b"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"\b(?:api[_-]?key|token|secret|password)\s*[:=]\s*['\"]?[^\s'\"]{8,}['\"]?", re.IGNORECASE),
]

DANGEROUS_COMMAND_PATTERNS = [
    re.compile(r"\brm\s+-rf\s+/"),
    re.compile(r"\bdd\s+if=.*\s+of=/dev/"),
    re.compile(r"\bmkfs(\.[a-z0-9]+)?\b", re.IGNORECASE),
    re.compile(r"\bshutdown\b|\breboot\b", re.IGNORECASE),
    re.compile(r"\bdel\s+/[sf].*\\\\"),
    re.compile(r"\bformat\s+[A-Za-z]:", re.IGNORECASE),
    re.compile(r"\bcurl\b.*\|\s*(sh|bash|zsh|powershell|pwsh)\b", re.IGNORECASE),
    re.compile(r"\bInvoke-Expression\b|\bIEX\b", re.IGNORECASE),
]


def redact_text(text: str) -> str:
    redacted = text
    for pattern in SECRET_PATTERNS:
        redacted = pattern.sub("[REDACTED]", redacted)
    return redacted


def looks_dangerous(text: str) -> bool:
    return any(pattern.search(text) for pattern in DANGEROUS_COMMAND_PATTERNS)


def _resolve_allowed_export_dirs(config: dict) -> list[Path]:
    security = config.get("security", {})
    configured = security.get("allowed_export_dirs", []) or [str(Path.cwd())]
    resolved: list[Path] = []
    for path_str in configured:
        p = Path(path_str).expanduser()
        if not p.is_absolute():
            p = (Path.cwd() / p).resolve()
        else:
            p = p.resolve()
        resolved.append(p)
    return resolved


def _validate_export_output_path(output_file: str, config: dict) -> None:
    target = Path(output_file).expanduser()
    if not target.is_absolute():
        target = (Path.cwd() / target).resolve()
    else:
        target = target.resolve()

    allowed_dirs = _resolve_allowed_export_dirs(config)
    parent = target.parent
    if not any(parent.is_relative_to(allowed) for allowed in allowed_dirs):
        allowed = ", ".join(str(p) for p in allowed_dirs)
        raise ValueError(
            f"Output path '{target}' is outside allowed directories: {allowed}"
        )


def format_export(
    name: str,
    history: list[dict],
    provider: str | None,
    fmt: str,
    redact: bool = False,
) -> str:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    if fmt == "markdown":
        lines = [f"# Session: {name}"]
        if provider:
            lines.append(f"Provider: {provider}")
        lines += [f"Exported: {ts}", "", "---", ""]
        for msg in history:
            role = "User" if msg["role"] == "user" else "Assistant"
            content = redact_text(msg["content"]) if redact else msg["content"]
            lines += [f"**{role}:** {content}", ""]
        return "\n".join(lines).rstrip() + "\n"
    else:  # text
        lines = [f"Session: {name}"]
        if provider:
            lines.append(f"Provider: {provider}")
        lines += [f"Exported: {ts}", "", "---", ""]
        for msg in history:
            role = "USER" if msg["role"] == "user" else "ASSISTANT"
            content = redact_text(msg["content"]) if redact else msg["content"]
            lines += [f"{role}: {content}", ""]
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


def persist_history(history: list[dict], session_name: str | None, active_provider: str) -> None:
    if session_name:
        save_session(session_name, history, active_provider)
    else:
        save_history(active_provider, history)


def run_turn(
    prov,
    history: list[dict],
    user_text: str,
    active_system: str,
    active_provider: str,
    model: str,
    session_name: str | None,
    warn_dangerous: bool,
) -> bool:
    """Run one chat turn. Returns False if interrupted mid-stream."""
    history.append({"role": "user", "content": user_text})
    full_response = ""

    try:
        console.print()
        for chunk in prov.stream_chat(history, active_system):
            full_response += chunk
        if warn_dangerous and looks_dangerous(full_response):
            console.print(
                "[yellow]Warning:[/yellow] Potentially dangerous command suggestions detected. "
                "Review carefully before running anything."
            )
        print(full_response)
        print()
        if prov.last_usage:
            in_tok = prov.last_usage["input_tokens"]
            out_tok = prov.last_usage["output_tokens"]
            cost = estimate_cost(model, in_tok, out_tok)
            cost_str = f" · ~${cost:.4f}" if cost is not None else ""
            console.print(f"[dim]↑ {in_tok:,} in · ↓ {out_tok:,} out{cost_str}[/dim]")
            accumulate_usage(active_provider, in_tok, out_tok, cost or 0.0)
    except ProviderTimeoutError as e:
        console.print(f"\n[red]Network timeout:[/red] {e}")
        sys.exit(1)
    except ProviderConnectionError as e:
        console.print(f"\n[red]Connection error:[/red] {e}")
        sys.exit(1)
    except ConnectionError as e:
        console.print(f"\n[red]Connection error:[/red] {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        console.print("\n[dim]Interrupted.[/dim]")
        if full_response:
            history.append({"role": "assistant", "content": full_response})
            persist_history(history, session_name, active_provider)
        return False
    except Exception as e:
        console.print(f"\n[red]Error:[/red] {e}")
        sys.exit(1)

    history.append({"role": "assistant", "content": full_response})
    persist_history(history, session_name, active_provider)
    return True


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
    "--safe-output/--unsafe-output",
    "safe_output",
    default=None,
    help="Restrict --output paths to allowed directories (default from config).",
)
@click.option(
    "--redact-secrets/--no-redact-secrets",
    "redact_secrets_flag",
    default=None,
    help="Mask likely secrets in --history and --export output (default from config).",
)
@click.option(
    "--purge",
    "do_purge",
    is_flag=True,
    help="Delete history, usage, and session data older than the retention window.",
)
@click.option(
    "--days",
    "purge_days",
    type=int,
    default=None,
    help="Retention window in days for --purge (defaults to config).",
)
@click.option(
    "--usage",
    "show_usage",
    is_flag=True,
    help="Show cumulative token and cost totals per provider.",
)
@click.option(
    "--chat",
    "chat_mode",
    is_flag=True,
    help="Start interactive chat mode (persistent REPL).",
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
    safe_output: bool | None,
    redact_secrets_flag: bool | None,
    do_purge: bool,
    purge_days: int | None,
    show_usage: bool,
    chat_mode: bool,
) -> None:
    config = load_config()
    security = config.get("security", {})
    safe_output_enabled = (
        bool(security.get("safe_output", True))
        if safe_output is None
        else safe_output
    )
    redact_output = (
        bool(security.get("redact_secrets", False))
        if redact_secrets_flag is None
        else redact_secrets_flag
    )
    warn_dangerous = bool(security.get("warn_dangerous_commands", True))
    retention_days = int(security.get("retention_days", 30))

    for candidate in (session_name, clear_session_name, export_session):
        if candidate is None:
            continue
        try:
            validate_session_name(candidate)
        except ValueError as e:
            console.print(f"[red]Error:[/red] {e}")
            sys.exit(1)

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

    if do_purge:
        days = retention_days if purge_days is None else purge_days
        try:
            removed = purge_old_data(days)
        except ValueError as e:
            console.print(f"[red]Error:[/red] {e}")
            sys.exit(1)
        console.print(
            "[green]Purged old data:[/green] "
            f"{removed['history']} history, {removed['usage']} usage, {removed['sessions']} sessions "
            f"older than {days} day(s)."
        )
        log_security_event("purge", retention_days=days, removed=removed)
        return

    if export_session:
        meta = load_session_with_meta(export_session)
        if meta is None:
            console.print(f"[red]No session named '{export_session}' found.[/red]")
            sys.exit(1)
        if not meta["history"]:
            console.print(f"[yellow]Session '{export_session}' is empty.[/yellow]")
            return
        content = format_export(
            export_session,
            meta["history"],
            meta["provider"],
            export_format,
            redact=redact_output,
        )
        if output_file:
            if safe_output_enabled:
                try:
                    _validate_export_output_path(output_file, config)
                except ValueError as e:
                    console.print(f"[red]Error:[/red] {e}")
                    sys.exit(1)
            Path(output_file).write_text(content, encoding="utf-8")
            console.print(f"[green]Exported '{export_session}' to {output_file}[/green]")
            log_security_event(
                "export",
                session=export_session,
                format=export_format,
                output=str(output_file),
                redacted=redact_output,
                safe_output=safe_output_enabled,
            )
        else:
            print(content, end="")
            log_security_event(
                "export",
                session=export_session,
                format=export_format,
                output="stdout",
                redacted=redact_output,
                safe_output=safe_output_enabled,
            )
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
        log_security_event("clear_session", session=clear_session_name)
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
        log_security_event("set_provider", provider=set_provider)
        return

    if set_model:
        active = resolve_provider(config, provider)
        config["providers"][active]["model"] = set_model
        save_config(config)
        console.print(f"[green]Model for '{active}' set to '{set_model}'.[/green]")
        log_security_event("set_model", provider=active, model=set_model)
        return

    active_provider = resolve_provider(config, provider)

    if do_clear:
        clear_history(active_provider)
        console.print(f"[green]History cleared for '{active_provider}'.[/green]")
        log_security_event("clear_history", provider=active_provider)
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
            content = redact_text(msg["content"]) if redact_output else msg["content"]
            console.print(f"[{colour}][{role}][/{colour}] {content}\n")
        return

    if not chat_mode and not message:
        console.print(
            "[yellow]Usage:[/yellow] bot [OPTIONS] YOUR MESSAGE\n"
            "       bot --help  for all options"
        )
        sys.exit(0)

    try:
        provider_config = get_provider_config(config, active_provider)
        prov = get_provider(active_provider, provider_config)
    except (OSError, ValueError, ImportError) as e:
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)

    active_system = system_prompt if system_prompt is not None else SYSTEM_PROMPT
    model = config["providers"][active_provider].get("model", "")
    history = load_session(session_name) if session_name else load_history(active_provider)

    if chat_mode:
        console.print(
            "[dim]Interactive mode. Type [bold]/help[/bold] for commands, "
            "[bold]/exit[/bold] to leave.[/dim]"
        )
        if message:
            first_message = " ".join(message)
            if not run_turn(
                prov,
                history,
                first_message,
                active_system,
                active_provider,
                model,
                session_name,
                warn_dangerous,
            ):
                return

        while True:
            try:
                user_text = input("You: ").strip()
            except EOFError:
                console.print("\n[dim]Exited.[/dim]")
                return
            except KeyboardInterrupt:
                console.print("\n[dim]Interrupted.[/dim]")
                return

            if not user_text:
                continue

            if user_text.lower() in {"/exit", "/quit", "q"}:
                console.print("[dim]Exited.[/dim]")
                return

            if user_text.lower() == "/help":
                console.print(
                    "\n[bold]Chat mode commands:[/bold]\n"
                    "  [cyan]/help[/cyan]     Show this message\n"
                    "  [cyan]/history[/cyan]  Print the conversation so far\n"
                    "  [cyan]/clear[/cyan]    Clear conversation history for this session\n"
                    "  [cyan]/exit[/cyan]     Exit chat mode (also: /quit, q)\n"
                )
                continue

            if user_text.lower() == "/history":
                if not history:
                    console.print("[dim]No messages yet.[/dim]")
                else:
                    console.print()
                    for msg in history:
                        role = msg["role"].upper()
                        colour = "cyan" if msg["role"] == "user" else "green"
                        content = redact_text(msg["content"]) if redact_output else msg["content"]
                        console.print(f"[{colour}][{role}][/{colour}] {content}\n")
                continue

            if user_text.lower() == "/clear":
                history.clear()
                persist_history(history, session_name, active_provider)
                console.print("[green]History cleared.[/green]")
                continue

            if not run_turn(
                prov,
                history,
                user_text,
                active_system,
                active_provider,
                model,
                session_name,
                warn_dangerous,
            ):
                return
        return

    user_text = " ".join(message)
    if not run_turn(
        prov,
        history,
        user_text,
        active_system,
        active_provider,
        model,
        session_name,
        warn_dangerous,
    ):
        sys.exit(0)