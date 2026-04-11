"""Base class for all providers."""

from abc import ABC, abstractmethod
from collections.abc import Iterator


class BaseProvider(ABC):
    @abstractmethod
    def stream_chat(
        self,
        messages: list[dict],
        system: str,
    ) -> Iterator[str]:
        """Yield response text chunks for streaming output."""
