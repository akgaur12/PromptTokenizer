from __future__ import annotations
from pydantic import BaseModel
from typing import Optional


class ModelEntry(BaseModel):
    id: str
    label: str
    group: str
    provider: str
    family: Optional[str] = None
    adapter: str
    tokenizer_ref: str
    status: str
    context_window: Optional[int] = None
    max_output_tokens: Optional[int] = None
    knowledge_cutoff: Optional[str] = None
    supports_token_decode: bool = True
    supports_browser: bool = True
    deprecated: bool = False
    notes: Optional[str] = None
    description: Optional[str] = None


class ModelsListResponse(BaseModel):
    items: list[ModelEntry]
    total: int
