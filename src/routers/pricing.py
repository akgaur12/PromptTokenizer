from __future__ import annotations
from fastapi import APIRouter, Query
from typing import Optional
from src.schemas.pricing import PricingListResponse, PricingEntry
from src.services.pricing_service import get_pricing_service

router = APIRouter(prefix="/pricing", tags=["Pricing"])


@router.get("", response_model=PricingListResponse)
def list_pricing(model_id: Optional[str] = Query(None)):
    service = get_pricing_service()
    if model_id:
        entry = service.get_by_model(model_id)
        items = [entry] if entry else []
    else:
        items = service.get_all()
    return PricingListResponse(items=items, total=len(items))
