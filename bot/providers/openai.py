"""OpenAI provider - also works for Groq, Together, etc. via base_url."""

import os
from collections.abc import Iterator

from .base import BaseProvider


class OpenAIProvider(BaseProvider):
    def __init__(self, config: dict):
        try:
            import openai
        except ImportError:
            raise ImportError("Run: uv add openai")

        api_key_env = config.get("api_key_env", "OPENAI_API_KEY")
        api_key = os.environ.get(api_key_env)
        if not api_key:
            raise OSError(
                f"Missing API key. Set the {api_key_env} environment variable."
            )
        kwargs = {"api_key": api_key}
        if "base_url" in config:
            kwargs["base_url"] = config["base_url"]

        self.client = openai.OpenAI(**kwargs)
        self.model = config.get("model", "gpt-4o-mini")

    def stream_chat(self, messages: list[dict], system: str) -> Iterator[str]:
        full_messages = [{"role": "system", "content": system}] + messages
        stream = self.client.chat.completions.create(
            model=self.model,
            messages=full_messages,
            stream=True,
            stream_options={"include_usage": True},
        )
        for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
            if chunk.usage:
                self.last_usage = {
                    "input_tokens": chunk.usage.prompt_tokens,
                    "output_tokens": chunk.usage.completion_tokens,
                }
