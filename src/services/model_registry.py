from __future__ import annotations
import json
from pathlib import Path
from functools import lru_cache
from src.schemas.models import ModelEntry
from src.core.exceptions import ModelNotSupportedError


DATA_FILE = Path(__file__).parent.parent / "data" / "models.json"


class ModelRegistry:
    def __init__(self, data_file: Path = DATA_FILE) -> None:
        raw = json.loads(data_file.read_text(encoding="utf-8"))
        self._entries: dict[str, ModelEntry] = {
            entry["id"]: ModelEntry(**entry) for entry in raw
        }

    def get_all(
        self,
        group: str | None = None,
        provider: str | None = None,
        search: str | None = None,
    ) -> list[ModelEntry]:
        entries = list(self._entries.values())
        if group:
            entries = [e for e in entries if e.group.lower() == group.lower()]
        if provider:
            entries = [e for e in entries if e.provider.lower() == provider.lower()]
        if search:
            term = search.lower()
            entries = [
                e for e in entries
                if term in e.id.lower() or term in e.label.lower() or (e.description and term in e.description.lower())
            ]
        return entries

    def get_by_id(self, model_id: str) -> ModelEntry:
        entry = self._entries.get(model_id)
        if entry is None:
            raise ModelNotSupportedError(model_id)
        return entry

    def resolve_tokenizer_ref(self, model_id: str) -> str:
        return self.get_by_id(model_id).tokenizer_ref


@lru_cache
def get_model_registry() -> ModelRegistry:
    return ModelRegistry()
