"""Registry - maps provider name -> class."""

from .anthropic import AnthropicProvider
from .base import BaseProvider
from .llamacpp import LlamaCppProvider
from .ollama import OllamaProvider
from .openai import OpenAIProvider

PROVIDERS: dict[str, type[BaseProvider]] = {
    "anthropic": AnthropicProvider,
    "openai": OpenAIProvider,
    "ollama": OllamaProvider,
    "llamacpp": LlamaCppProvider,
}


def get_provider(name: str, config: dict) -> BaseProvider:
    if name not in PROVIDERS:
        raise ValueError(
            f"Unknown provider: '{name}'. Available: {', '.join(PROVIDERS.keys())}"
        )
    return PROVIDERS[name](config)
