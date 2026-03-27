"""Registry - maps provider name -> class."""

from .base import BaseProvider
from .anthropic import AnthropicProvider
from .llamacpp import LlamaCppProvider
from .openai import OpenAIProvider
from ollama import OllamaProvider

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