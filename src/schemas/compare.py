from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Optional


class CompareRequest(BaseModel):
    models: list[str] = Field(..., min_length=1, max_length=10)
    text: str = Field(..., min_length=1, max_length=200_000)


class CompareResult(BaseModel):
    model: str
    resolved_tokenizer: str
    token_count: int
    error: Optional[str] = None


class CompareResponse(BaseModel):
    text_length: int
    results: list[CompareResult]
