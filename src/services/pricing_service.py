from __future__ import annotations
import json
from pathlib import Path
from functools import lru_cache
from src.schemas.pricing import PricingEntry


DATA_FILE = Path(__file__).parent.parent / "data" / "pricing.json"


class PricingService:
    def __init__(self, data_file: Path = DATA_FILE) -> None:
        raw = json.loads(data_file.read_text(encoding="utf-8"))
        self._entries: list[PricingEntry] = [PricingEntry(**item) for item in raw]
        self._by_model: dict[str, PricingEntry] = {e.model_id: e for e in self._entries}

    def get_all(self) -> list[PricingEntry]:
        return list(self._entries)

    def get_by_model(self, model_id: str) -> PricingEntry | None:
        return self._by_model.get(model_id)


@lru_cache
def get_pricing_service() -> PricingService:
    return PricingService()
