from __future__ import annotations
from pydantic import BaseModel
from typing import Optional


class PricingEntry(BaseModel):
    model_id: str
    input_price_per_1m: float
    output_price_per_1m: Optional[float] = None
    currency: str = "USD"
    last_updated: Optional[str] = None


class PricingListResponse(BaseModel):
    items: list[PricingEntry]
    total: int
