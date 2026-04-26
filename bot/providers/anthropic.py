"""Anthropic Provider."""

import os
from collections.abc import Iterator

from .base import BaseProvider


class AnthropicProvider(BaseProvider):
    def __init__(self, config: dict):
        try:
            import anthropic
        except ImportError:
            raise ImportError("Run: uv add anthropic")

        api_key_env = config.get("api_key_env", "ANTHROPIC_API_KEY")
        api_key = os.environ.get(api_key_env)
        if not api_key:
            raise OSError(
                f"Missing API key. Set the {api_key_env} environment variable."
            )
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = config.get("model", "claude-opus-4-5")

    def stream_chat(self, messages: list[dict], system: str) -> Iterator[str]:
        with self.client.messages.stream(
            model=self.model,
            max_tokens=2048,
            system=system,
            messages=messages,
        ) as stream:
            yield from stream.text_stream
            msg = stream.get_final_message()
            self.last_usage = {
                "input_tokens": msg.usage.input_tokens,
                "output_tokens": msg.usage.output_tokens,
            }
