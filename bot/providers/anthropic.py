"""Anthropic Provider."""

from collections.abc import Iterator

from ..credentials import get_api_key
from .base import BaseProvider, ProviderConnectionError, ProviderTimeoutError


class AnthropicProvider(BaseProvider):
    def __init__(self, config: dict):
        try:
            import anthropic
        except ImportError:
            raise ImportError("Run: uv add anthropic")

        api_key_env = config.get("api_key_env", "ANTHROPIC_API_KEY")
        api_key = get_api_key("anthropic", api_key_env)
        if not api_key:
            raise OSError(
                f"Missing API key. Run 'bot --setup' or set the {api_key_env} environment variable."
            )
        self.client = anthropic.Anthropic(
            api_key=api_key,
            timeout=int(config.get("request_timeout_seconds", 30)),
            max_retries=int(config.get("max_retries", 2)),
        )
        self.model = config.get("model", "claude-opus-4-5")

    def stream_chat(self, messages: list[dict], system: str) -> Iterator[str]:
        try:
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
        except TimeoutError as e:
            raise ProviderTimeoutError(
                "Anthropic request timed out. Increase security.request_timeout_seconds if needed."
            ) from e
        except Exception as e:
            msg = str(e).lower()
            if "timeout" in msg:
                raise ProviderTimeoutError(
                    "Anthropic request timed out. Increase security.request_timeout_seconds if needed."
                ) from e
            raise ProviderConnectionError(f"Anthropic request failed: {e}") from e
