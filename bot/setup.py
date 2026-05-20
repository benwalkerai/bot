"""Interactive setup wizard for provider configuration and credentials."""

from __future__ import annotations

import click
from rich.console import Console

from .config import get_provider_config, load_config, save_config
from .credentials import has_stored_api_key, keyring_is_available, set_api_key
from .providers import get_provider

console = Console()

API_KEY_PROVIDERS = {
    "anthropic": {
        "env": "ANTHROPIC_API_KEY",
        "models": ["claude-haiku-4-5", "claude-sonnet-4-5", "claude-opus-4-5"],
    },
    "openai": {
        "env": "OPENAI_API_KEY",
        "models": ["gpt-4o-mini", "gpt-4o"],
    },
}


def _ask_enable(provider: str, current: bool) -> bool:
    return click.confirm(f"Use {provider}?", default=current)


def _choose_default_provider(enabled_providers: list[str], current_default: str) -> str:
    if len(enabled_providers) == 1:
        only = enabled_providers[0]
        console.print(f"[dim]Only one provider enabled. Default set to {only}.[/dim]")
        return only

    keep_current = click.confirm(
        f"Keep default provider as {current_default}?",
        default=True,
    )
    if keep_current:
        return current_default

    return click.prompt(
        "Choose default provider",
        type=click.Choice(enabled_providers, case_sensitive=False),
        default=current_default,
        show_default=True,
    )


def _print_next_steps(config: dict, use_keyring: bool) -> None:
    default_provider = config.get("provider", "anthropic")
    enabled_providers = [
        name for name, cfg in config.get("providers", {}).items() if cfg.get("enabled", True)
    ]

    console.print("\n[bold]What's next[/bold]")
    console.print(f"  1. Start chatting: inzen_bot --provider {default_provider} hello")
    console.print("  2. See configured providers: inzen_bot --providers")
    console.print("  3. Re-run setup any time: inzen_bot --setup")

    if use_keyring:
        console.print("  4. Manage keys: inzen_bot --credentials-list")
    else:
        console.print("  4. Add API keys with environment variables, then open a new terminal")

    if not enabled_providers:
        console.print("[yellow]No providers are enabled. Run setup again to enable at least one.[/yellow]")


def run_setup_wizard() -> None:
    config = load_config()
    providers = config.setdefault("providers", {})
    use_keyring = keyring_is_available()

    console.print("[bold]bot setup wizard[/bold]")
    if use_keyring:
        console.print("[green]Secure storage:[/green] OS keyring detected.")
    else:
        console.print(
            "[yellow]Secure storage unavailable:[/yellow] no keyring backend detected. "
            "Use environment variables for API keys."
        )

    for provider_name, provider_cfg in providers.items():
        enabled_default = bool(provider_cfg.get("enabled", True))
        enabled = _ask_enable(provider_name, enabled_default)
        provider_cfg["enabled"] = enabled
        if not enabled:
            continue

        if provider_name in API_KEY_PROVIDERS:
            details = API_KEY_PROVIDERS[provider_name]
            env_name = details["env"]
            provider_cfg.setdefault("api_key_env", env_name)

            model_choices = details["models"]
            current_model = provider_cfg.get("model", model_choices[0])
            provider_cfg["model"] = click.prompt(
                f"Model for {provider_name}",
                type=click.Choice(model_choices, case_sensitive=False),
                default=current_model,
                show_default=True,
            )

            if use_keyring:
                has_existing = has_stored_api_key(provider_name)
                should_set_key = True
                if has_existing:
                    should_set_key = click.confirm(
                        f"A stored {provider_name} key exists. Replace it?", default=False
                    )

                if should_set_key:
                    api_key = click.prompt(
                        f"Paste {provider_name} API key",
                        hide_input=True,
                        confirmation_prompt=True,
                    ).strip()
                    set_api_key(provider_name, api_key)
                    console.print(f"[green]{provider_name} key stored securely in OS keyring.[/green]")
                else:
                    console.print(f"[dim]Kept existing stored key for {provider_name}.[/dim]")
            else:
                console.print(
                    f"[yellow]Set {env_name} in your shell environment.[/yellow]"
                )
            continue

        if provider_name == "ollama":
            provider_cfg["base_url"] = click.prompt(
                "Ollama base URL",
                default=provider_cfg.get("base_url", "http://localhost:11434"),
                show_default=True,
            )
            provider_cfg["model"] = click.prompt(
                "Ollama model",
                default=provider_cfg.get("model", "llama3"),
                show_default=True,
            )
        elif provider_name == "llamacpp":
            provider_cfg["base_url"] = click.prompt(
                "llama.cpp base URL",
                default=provider_cfg.get("base_url", "http://localhost:8080"),
                show_default=True,
            )
            provider_cfg["model"] = click.prompt(
                "llama.cpp model",
                default=provider_cfg.get("model", "local"),
                show_default=True,
            )

    enabled_providers = [name for name, cfg in providers.items() if cfg.get("enabled", True)]
    if enabled_providers:
        current_default = config.get("provider", enabled_providers[0])
        if current_default not in enabled_providers:
            current_default = enabled_providers[0]
        config["provider"] = _choose_default_provider(enabled_providers, current_default)

    save_config(config)
    if click.confirm("Run a quick provider connectivity check now?", default=True):
        _connectivity_check(config)
    console.print("[green]Setup complete.[/green]")
    _print_next_steps(config, use_keyring)


def _connectivity_check(config: dict) -> None:
    console.print("\n[bold]Provider checks:[/bold]")
    for provider_name, provider_cfg in config.get("providers", {}).items():
        if not provider_cfg.get("enabled", True):
            console.print(f"  [dim]{provider_name}: skipped (disabled)[/dim]")
            continue
        try:
            effective_cfg = get_provider_config(config, provider_name)
            get_provider(provider_name, effective_cfg)
            console.print(f"  [green]{provider_name}: ok[/green]")
        except Exception as e:
            console.print(f"  [yellow]{provider_name}: {e}[/yellow]")