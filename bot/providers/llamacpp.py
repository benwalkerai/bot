"""llama.cpp provider - uses its OpenAI-compatible /v1 endpoint."""

import os
from .openai import OpenAIProvider

class LlamaCppProvider(OpenAIProvider):
    """
    llama.cpp exposes an OpenAI-compatible API at localhost:8080/v1,
    so we reuse the OpenAI provider, just pointing at a different base_url
    and using a dummy API key (required by the openai SDK but not validated).
    """

    def __init__(self, config: dict):
        config = config.copy()
        config.setdefault("base_url", "http://localhost:8080/v1")
        config.setdefault("model", "local")
        config["api_key_env"] = "_BOT_DUMMY"
        os.environ.setdefault("_BOT_DUMMY", "local")
        super().__init__(config)