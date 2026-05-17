"""Ollama provider - talks to a local Ollama server via its REST API."""

import json
from collections.abc import Iterator
from urllib import error as url_error
from urllib import request

from .base import BaseProvider, ProviderConnectionError, ProviderTimeoutError


class OllamaProvider(BaseProvider):
    def __init__(self, config: dict):
        self.base_url = config.get("base_url", "http://localhost:11434").strip("/")
        self.model = config.get("model", "llama3")
        self.timeout_seconds = int(config.get("request_timeout_seconds", 30))
        self.max_retries = int(config.get("max_retries", 2))

    def stream_chat(self, messages: list[dict], system: str) -> Iterator[str]:
        payload = json.dumps(
            {
                "model": self.model,
                "messages": [{"role": "system", "content": system}] + messages,
                "stream": True,
            }
        ).encode()

        req = request.Request(
            f"{self.base_url}/api/chat",
            data=payload,
            headers={"Content-Type": "application/json"},
        )

        last_error = None
        attempts = max(self.max_retries + 1, 1)
        for attempt in range(attempts):
            try:
                with request.urlopen(req, timeout=self.timeout_seconds) as resp:
                    for line in resp:
                        if not line.strip():
                            continue
                        chunk = json.loads(line)
                        content = chunk.get("message", {}).get("content", "")
                        if content:
                            yield content
                        if chunk.get("done"):
                            self.last_usage = {
                                "input_tokens": chunk.get("prompt_eval_count", 0),
                                "output_tokens": chunk.get("eval_count", 0),
                            }
                            return
                    return
            except TimeoutError as e:
                last_error = e
            except url_error.URLError as e:
                last_error = e

        if isinstance(last_error, TimeoutError):
            raise ProviderTimeoutError(
                f"Ollama request timed out after {attempts} attempt(s) to {self.base_url}."
            ) from last_error

        raise ProviderConnectionError(
            f"Cannot reach Ollama at {self.base_url} after {attempts} attempt(s). "
            "Is 'ollama serve' running?"
        ) from last_error
