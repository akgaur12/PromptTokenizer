from __future__ import annotations
from fastapi import APIRouter
from src.schemas.compare import CompareRequest, CompareResponse, CompareResult
from src.services import tokenizer_service

router = APIRouter(prefix="/compare", tags=["Compare"])


@router.post("", response_model=CompareResponse)
def compare_tokenizers(request: CompareRequest):
    results: list[CompareResult] = []
    
    for model_id in request.models:
        try:
            resp = tokenizer_service.tokenize(
                model_or_encoding=model_id,
                text=request.text,
                include_tokens=False,
                include_token_ids=False,
            )
            results.append(
                CompareResult(
                    model=model_id,
                    resolved_tokenizer=resp.resolved_tokenizer,
                    token_count=resp.token_count,
                )
            )
        except Exception as exc:
            results.append(
                CompareResult(
                    model=model_id,
                    resolved_tokenizer="unknown",
                    token_count=0,
                    error=str(exc),
                )
            )
    return CompareResponse(text_length=len(request.text), results=results)
