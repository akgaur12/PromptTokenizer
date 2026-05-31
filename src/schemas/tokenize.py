from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Optional


class TokenizeRequest(BaseModel):
    model: str
    text: str = Field(..., min_length=1, max_length=200_000)
    include_tokens: bool = True
    include_token_ids: bool = True


class TokenizeResponse(BaseModel):
    model: str
    resolved_tokenizer: str
    provider: str
    token_count: int
    tokens: Optional[list[str]] = None
    token_ids: Optional[list[int]] = None
    word_count: int
    character_count: int
    estimated_input_cost: Optional[float] = None
    cost_currency: Optional[str] = None
    cost_estimation_note: Optional[str] = None
