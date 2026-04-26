"""Base class for all providers."""

from abc import ABC, abstractmethod
from collections.abc import Iterator


class BaseProvider(ABC):
    last_usage: dict | None = None

    @abstractmethod
    def stream_chat(
        self,
        messages: list[dict],
        system: str,
    ) -> Iterator[str]:
        """Yield response text chunks for streaming output.
        After the iterator is exhausted, self.last_usage is set to
        {"input_tokens": int, "output_tokens": int} if the provider
        supports it, otherwise remains None.
        """
