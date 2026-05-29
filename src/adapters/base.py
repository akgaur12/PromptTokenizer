from __future__ import annotations
from abc import ABC, abstractmethod


class BaseTokenizerAdapter(ABC):
    adapter_name: str = "base"

    @abstractmethod
    def encode(self, text: str) -> list[int]:
        """Encode text into token IDs."""

    @abstractmethod
    def decode_tokens(self, token_ids: list[int]) -> list[str]:
        """Decode each token ID to its string representation."""

    @abstractmethod
    def count_tokens(self, text: str) -> int:
        """Count tokens in text."""

    @abstractmethod
    def supports_model(self, model_id: str) -> bool:
        """Return True if this adapter supports the given model."""
