"""Ollama provider - talks to a local Ollama server via its REST API."""

import json
from collections.abc import Iterator
from urllib import error as url_error
from urllib import request

from .base import BaseProvider


class OllamaProvider(BaseProvider):
    def __init__(self, config: dict):
        self.base_url = config.get("base_url", "http://localhost:11434").strip("/")
        self.model = config.get("model", "llama3")

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

        try:
            with request.urlopen(req) as resp:
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
                        break
        except url_error.URLError as e:
            raise ConnectionError(
                f"Cannot reach Ollama at {self.base_url}."
                "Is 'ollama server' running?\n"
                f"Details: {e}"
            )
