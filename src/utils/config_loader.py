from __future__ import annotations
import json
import yaml
from pathlib import Path


def load_config(path: str) -> dict:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Config file not found: {path}")
    if not p.is_file():
        raise ValueError(f"Path is not a file: {path}")

    suffix = p.suffix.lower()
    with p.open() as f:
        if suffix in (".yaml", ".yml"):
            data = yaml.safe_load(f)
        elif suffix == ".json":
            data = json.load(f)
        else:
            raise ValueError(f"Unsupported config format '{suffix}' for file: {path}")

    if not isinstance(data, dict):
        raise ValueError(f"Config file must contain a mapping, got {type(data).__name__}: {path}")

    return data
