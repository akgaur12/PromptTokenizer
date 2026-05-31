from __future__ import annotations
from src.schemas.tokenize import TokenizeResponse
from src.services.model_registry import get_model_registry
from src.services.openai_tokenizer_adapter import get_openai_adapter
from src.services.pricing_service import get_pricing_service
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

        pricing = get_pricing_service().get_by_model(entry.id)
        if pricing is not None:
            estimated_input_cost = round(len(token_ids) / 1_000_000 * pricing.input_price_per_1m, 10)
            cost_currency = pricing.currency
            cost_estimation_note = None
        else:
            estimated_input_cost = None
            cost_currency = None
            cost_estimation_note = f"Pricing data is not available for model '{entry.id}'."

        return TokenizeResponse(
            model=model_or_encoding,
            resolved_tokenizer=tokenizer_ref,
            provider=entry.provider,
            token_count=len(token_ids),
            tokens=tokens if include_tokens else None,
            token_ids=token_ids if include_token_ids else None,
            word_count=len(text.split()),
            character_count=len(text),
            estimated_input_cost=estimated_input_cost,
            cost_currency=cost_currency,
            cost_estimation_note=cost_estimation_note,
        )

    raise ModelNotSupportedError(model_or_encoding)
