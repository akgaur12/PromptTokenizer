from __future__ import annotations
from fastapi import APIRouter, Query
from typing import Optional
from src.schemas.models import ModelsListResponse, ModelEntry
from src.services.model_registry import get_model_registry

router = APIRouter(prefix="/models", tags=["Models"])


@router.get("", response_model=ModelsListResponse)
def list_models(
    group: Optional[str] = Query(None),
    provider: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
):
    registry = get_model_registry()
    items = registry.get_all(group=group, provider=provider, search=search)
    return ModelsListResponse(items=items, total=len(items))


@router.get("/{model_id}", response_model=ModelEntry)
def get_model(model_id: str):
    registry = get_model_registry()
    return registry.get_by_id(model_id)
