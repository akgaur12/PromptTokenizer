from __future__ import annotations
import tiktoken
from src.adapters.base import BaseTokenizerAdapter
from src.core.exceptions import TokenizerNotAvailableError
from src.core.logger import get_logger

logger = get_logger(__name__)


class OpenAITokenizerAdapter(BaseTokenizerAdapter):
    adapter_name = "openai_tiktoken"

    def __init__(self) -> None:
        self._cache: dict[str, tiktoken.Encoding] = {}

    def _get_encoding_by_name(self, tokenizer_name: str) -> tiktoken.Encoding:
        if tokenizer_name not in self._cache:
            try:
                self._cache[tokenizer_name] = tiktoken.get_encoding(tokenizer_name)
            except Exception as exc:
                raise TokenizerNotAvailableError(tokenizer_name) from exc
        return self._cache[tokenizer_name]

    def get_encoding_for_model(self, model_name: str, tokenizer_ref: str) -> tiktoken.Encoding:
        cache_key = f"model:{model_name}"
        if cache_key not in self._cache:
            try:
                self._cache[cache_key] = tiktoken.encoding_for_model(model_name)
            except KeyError:
                # model not in tiktoken's built-in map — fall back to tokenizer_ref
                self._cache[cache_key] = self._get_encoding_by_name(tokenizer_ref)
            except Exception as exc:
                raise TokenizerNotAvailableError(tokenizer_ref) from exc
        return self._cache[cache_key]

    def encode(self, text: str) -> list[int]:
        raise NotImplementedError("Use encode_with_tokenizer or encode_for_model_with_ref")

    def encode_with_tokenizer(self, tokenizer_name: str, text: str) -> list[int]:
        enc = self._get_encoding_by_name(tokenizer_name)
        return enc.encode(text)

    def encode_for_model_with_ref(self, model_name: str, tokenizer_ref: str, text: str) -> list[int]:
        enc = self.get_encoding_for_model(model_name, tokenizer_ref)
        return enc.encode(text)

    def decode_tokens(self, token_ids: list[int]) -> list[str]:
        raise NotImplementedError("Use decode_tokens_with_tokenizer")

    def decode_tokens_with_tokenizer(self, tokenizer_name: str, token_ids: list[int]) -> list[str]:
        enc = self._get_encoding_by_name(tokenizer_name)
        result = []
        for tid in token_ids:
            try:
                token_bytes = enc.decode_single_token_bytes(tid)
                result.append(token_bytes.decode("utf-8", errors="replace"))
            except Exception:
                result.append(f"<{tid}>")
        return result

    def count_tokens(self, text: str) -> int:
        raise NotImplementedError("Use count_with_tokenizer")

    def count_with_tokenizer(self, tokenizer_name: str, text: str) -> int:
        return len(self.encode_with_tokenizer(tokenizer_name, text))

    def count_for_model_with_ref(self, model_name: str, tokenizer_ref: str, text: str) -> int:
        return len(self.encode_for_model_with_ref(model_name, tokenizer_ref, text))

    def supports_model(self, model_id: str) -> bool:
        try:
            tiktoken.encoding_for_model(model_id)
            return True
        except KeyError:
            return False


_adapter_instance: OpenAITokenizerAdapter | None = None


def get_openai_adapter() -> OpenAITokenizerAdapter:
    global _adapter_instance
    if _adapter_instance is None:
        _adapter_instance = OpenAITokenizerAdapter()
    return _adapter_instance
