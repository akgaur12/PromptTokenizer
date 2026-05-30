from __future__ import annotations
import tiktoken
from tiktoken.model import encoding_name_for_model
from src.adapters.base import BaseTokenizerAdapter
from src.core.exceptions import TokenizerNotAvailableError
from src.core.logger import get_logger
from src.utils.config_loader import load_config

logger = get_logger(__name__)

_ENCODING_NAMES: tuple[str, ...] = tuple(load_config("src/config/config.yaml")["tokenizer"]["encoding_names"])

# Populated by preload_encodings() during lifespan startup; never mutated after.
ENCODINGS: dict[str, tiktoken.Encoding] = {}


def preload_encodings() -> None:
    pending = [name for name in _ENCODING_NAMES if name not in ENCODINGS]
    if not pending:
        logger.debug("Tokenizer encodings already loaded, skipping preload")
        return
    logger.info("Preloading %d tokenizer encoding(s): %s", len(pending), ", ".join(pending))
    for name in pending:
        logger.debug("Loading encoding: %s", name)
        ENCODINGS[name] = tiktoken.get_encoding(name)
    logger.info("Tokenizer preload complete (%d encoding(s) ready)", len(ENCODINGS))


class OpenAITokenizerAdapter(BaseTokenizerAdapter):
    adapter_name = "openai_tiktoken"

    def _get_encoding_by_name(self, tokenizer_name: str) -> tiktoken.Encoding:
        enc = ENCODINGS.get(tokenizer_name)
        if enc is None:
            raise TokenizerNotAvailableError(tokenizer_name)
        return enc

    def get_encoding_for_model(self, model_name: str, tokenizer_ref: str) -> tiktoken.Encoding:
        try:
            enc_name = encoding_name_for_model(model_name)
            enc = ENCODINGS.get(enc_name)
            if enc is not None:
                return enc
        except KeyError:
            pass
        # model not in tiktoken's built-in map (or its encoding isn't pre-loaded) — fall back to tokenizer_ref
        return self._get_encoding_by_name(tokenizer_ref)

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
            encoding_name_for_model(model_id)
            return True
        except KeyError:
            return False


_adapter_instance: OpenAITokenizerAdapter | None = None


def get_openai_adapter() -> OpenAITokenizerAdapter:
    global _adapter_instance
    if _adapter_instance is None:
        preload_encodings()
        _adapter_instance = OpenAITokenizerAdapter()
    return _adapter_instance
