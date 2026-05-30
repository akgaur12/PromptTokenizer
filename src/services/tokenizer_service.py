from __future__ import annotations
from src.schemas.tokenize import TokenizeResponse
from src.services.model_registry import get_model_registry
from src.services.openai_tokenizer_adapter import get_openai_adapter
from src.core.exceptions import ModelNotSupportedError


def tokenize(
    model_or_encoding: str,
    text: str,
    include_tokens: bool = True,
    include_token_ids: bool = True,
) -> TokenizeResponse:
    
    registry = get_model_registry()    
    entry = registry.get_by_id(model_or_encoding)
    tokenizer_ref = entry.tokenizer_ref

    if entry.adapter == "openai_tiktoken":
        adapter = get_openai_adapter()
        if entry.status == "alias":
            token_ids = adapter.encode_for_model_with_ref(entry.id, tokenizer_ref, text)
        else:
            token_ids = adapter.encode_with_tokenizer(tokenizer_ref, text)

        tokens = None
        if include_tokens:
            tokens = adapter.decode_tokens_with_tokenizer(tokenizer_ref, token_ids)

        return TokenizeResponse(
            model=model_or_encoding,
            resolved_tokenizer=tokenizer_ref,
            provider=entry.provider,
            token_count=len(token_ids),
            tokens=tokens if include_tokens else None,
            token_ids=token_ids if include_token_ids else None,
        )

    raise ModelNotSupportedError(model_or_encoding)
