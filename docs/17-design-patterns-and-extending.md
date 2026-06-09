# 17 · Design Patterns & Extending

This chapter names the patterns the codebase uses (with ADR-style rationale) and gives copy-paste recipes for the three common extensions.

---

## Design patterns in use

### 1. Layered architecture (Router → Service → Adapter → Data)

Each layer depends only downward. HTTP concerns never leak into services; tokenizer-library specifics never leak past the adapter. See [Architecture](02-architecture.md).

### 2. Application factory

`create_app()` builds and returns the FastAPI instance; `app = create_app()` is the import target. This makes it easy to build alternate app instances (e.g. in tests) and keeps wiring in one place.

### 3. Adapter pattern (Strategy for tokenizers)

`BaseTokenizerAdapter` (ABC) defines the contract; `OpenAITokenizerAdapter` implements it. `tokenizer_service` dispatches on the `ModelEntry.adapter` string. New backends are additive.

### 4. Registry / repository

`ModelRegistry` and `PricingService` are repositories over the JSON "data store" — they encapsulate loading, validation, indexing, and lookups, hiding the file format from callers.

### 5. Singleton via `@lru_cache` / module cache

All expensive, process-wide objects are created once and reused. See [Performance](16-performance.md).

### 6. Data-driven configuration

The catalog (models, pricing) and the preload list live in data files, not code. Behavior changes via data edits + restart.

### 7. Centralized error translation

Domain exceptions + global handlers + one error envelope. Routers never format errors. See [Error Handling](11-error-handling-and-logging.md).

### 8. Customization hook (settings sources)

`_FlexDotEnvSource` extends pydantic-settings to accept comma-separated lists — a focused override rather than a fork.

---

## Architectural decisions (ADR-style notes)

| Decision | Why | Consequence |
|----------|-----|-------------|
| Resolve via `tokenizer_ref`, not model name | Model names churn; encodings are stable | Robust to new/renamed models; the alias fallback handles models tiktoken doesn't know |
| Static JSON catalogs, no DB | Data is small, read-only, rarely changes | Zero infra; edits need a restart |
| Env-driven config (no app YAML) | Twelve-Factor; trivially containerizable | All knobs are env vars |
| Soft failures in `/compare` | Clients compare mixed valid/invalid ids | Per-model `error` field instead of whole-request failure |
| Docs gated to `APP_ENV=dev` | Reduce info disclosure in prod | Must set env correctly to see `/docs` |
| Preload encodings at startup | Predictable request latency | Higher startup time + per-worker memory |
| Sync handlers in threadpool | Tokenization is CPU-bound | No event-loop blocking; scales by workers |

### A known abstraction wrinkle

`BaseTokenizerAdapter` declares `encode(text)`, `decode_tokens(ids)`, `count_tokens(text)`, `supports_model(id)`. But the real call path needs the **encoding name / tokenizer_ref** too, so `OpenAITokenizerAdapter` adds richer variants (`encode_with_tokenizer`, `encode_for_model_with_ref`, `decode_tokens_with_tokenizer`, …) and makes the base methods raise `NotImplementedError`. The ABC therefore documents intent more than it constrains the real interface. If you add a backend, implement the **ref-aware** methods that `tokenizer_service` actually calls — or refactor the service to use the base signatures. Keep this in mind; it's the main place the abstraction is leaky.

---

## Recipe A — add a model that uses an existing encoding (no code)

The most common change. Example: add `gpt-4o-2024-11-20`.

1. Add an entry to `src/data/models.json`:

```json
{
  "id": "gpt-4o-2024-11-20",
  "label": "gpt-4o-2024-11-20",
  "group": "OpenAI Models",
  "provider": "openai",
  "family": "gpt-4o",
  "adapter": "openai_tiktoken",
  "tokenizer_ref": "o200k_base",
  "status": "alias",
  "context_window": 128000,
  "max_output_tokens": 16384,
  "knowledge_cutoff": "Oct 01, 2023",
  "supports_token_decode": true,
  "supports_browser": true,
  "deprecated": false,
  "description": "GPT-4o snapshot 2024-11-20"
}
```

2. (Optional) add a pricing row to `src/data/pricing.json` so cost estimation works:

```json
{ "model_id": "gpt-4o-2024-11-20", "input_price_per_1m": 2.5, "output_price_per_1m": 10.0, "currency": "USD", "last_updated": "2024-11-20" }
```

3. Confirm the `tokenizer_ref` is already preloaded (it is — `o200k_base` is in `config.yaml`).
4. Restart. Add a test asserting resolution. Done — **no code changes**.

> Checklist: `adapter` must be `openai_tiktoken`; `status` `"alias"` for a model (uses tiktoken-map+fallback) or `"stable"` for a raw encoding; `tokenizer_ref` must be in `config.yaml`.

---

## Recipe B — add a new tiktoken encoding

If you need an encoding not yet preloaded (e.g. a hypothetical `o300k_base`):

1. Add its name to `src/config/config.yaml`:

```yaml
tokenizer:
  encoding_names:
    - cl100k_base
    - o200k_base
    - o300k_base   # ← new
    # …
```

2. Add a catalog entry whose `tokenizer_ref` is `o300k_base` (and `status: stable` if you want to expose the raw encoding itself).
3. Restart — `preload_encodings()` will load it.

If you skip step 1, requests resolving to that ref fail with `503 TOKENIZER_NOT_AVAILABLE`.

---

## Recipe C — add a new tokenizer backend (code required)

Example: a HuggingFace / SentencePiece backend.

**1. Implement the adapter** (`src/services/hf_tokenizer_adapter.py`):

```python
from src.adapters.base import BaseTokenizerAdapter

class HFTokenizerAdapter(BaseTokenizerAdapter):
    adapter_name = "huggingface"          # ← matches ModelEntry.adapter

    def __init__(self):
        self._tokenizers = {}             # cache like ENCODINGS

    def encode_with_tokenizer(self, ref, text): ...        # the methods the service calls
    def decode_tokens_with_tokenizer(self, ref, ids): ...
    # implement the ABC methods too (encode/decode_tokens/count_tokens/supports_model)

_instance = None
def get_hf_adapter():
    global _instance
    if _instance is None:
        _instance = HFTokenizerAdapter()
    return _instance
```

**2. Branch in `tokenizer_service.tokenize()`** alongside the existing `openai_tiktoken` block:

```python
if entry.adapter == "openai_tiktoken":
    ...
elif entry.adapter == "huggingface":
    adapter = get_hf_adapter()
    token_ids = adapter.encode_with_tokenizer(tokenizer_ref, text)
    tokens = adapter.decode_tokens_with_tokenizer(tokenizer_ref, token_ids) if include_tokens else None
    # …same pricing + TokenizeResponse assembly…
raise ModelNotSupportedError(model_or_encoding)
```

> Consider refactoring the shared tail (pricing lookup + `TokenizeResponse` assembly) into a helper so both branches reuse it.

**3. Preload at startup** — add a preload call in `src/main.py`'s `lifespan` (mirroring `preload_encodings()`), and/or lazy-init in `get_hf_adapter()`.

**4. Point catalog entries at it** — set `"adapter": "huggingface"` and an appropriate `tokenizer_ref` in `models.json`.

**5. Declare new dependencies** in `pyproject.toml` (`uv add transformers` etc.).

---

## Recipe D — add a new API endpoint

1. **Schema** — add request/response models in `src/schemas/<resource>.py`.
2. **Logic** — add a function/service in `src/services/`.
3. **Router** — create `src/routers/<resource>.py` with an `APIRouter(prefix="/<resource>", tags=[...])`.
4. **Wire it** — `app.include_router(<resource>.router, prefix=settings.api_prefix)` in `create_app()`.
5. **Errors** — raise existing domain exceptions or add a new one + handler in `src/core/exceptions.py`.
6. **Test** — add an HTTP-level test in `tests/`.

---

## Recipe E — change the API version prefix

Set `API_PREFIX=/api/v2` in `.env` and restart. Every router except `/health` re-mounts automatically (it's applied at `include_router` time).

Continue to [Glossary →](18-glossary.md)
