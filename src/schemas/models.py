from __future__ import annotations
from pydantic import BaseModel
from typing import Optional


class ModelEntry(BaseModel):
    id: str
    label: str
    group: str
    provider: str
    adapter: str
    tokenizer_ref: str
    status: str
    description: Optional[str] = None
    context_window: Optional[int] = None
    notes: Optional[str] = None
    supports_token_decode: bool = True
    supports_browser: bool = True
    deprecated: bool = False


class ModelsListResponse(BaseModel):
    items: list[ModelEntry]
    total: int
