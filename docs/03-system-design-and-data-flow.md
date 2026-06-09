# 03 · System Design & Data Flow

This chapter traces requests end-to-end with sequence diagrams, then explains the two most important pieces of business logic: **model-alias resolution** and **cost estimation**.

---

## 1. `POST /api/v1/tokenize` — the primary flow

```
Client            tokenize router        tokenizer_service        model_registry      openai_adapter        pricing_service
  │                     │                       │                       │                  │                    │
  │ POST /tokenize ────▶│                       │                       │                  │                    │
  │ {model,text,...}    │                       │                       │                  │                    │
  │            (Pydantic validates body)        │                       │                  │                    │
  │                     │── tokenize(...) ──────▶│                       │                  │                    │
  │                     │                       │── get_by_id(model) ───▶│                  │                    │
  │                     │                       │◀── ModelEntry ─────────│  (or 404)        │                    │
  │                     │                       │   entry.adapter == "openai_tiktoken"?     │                    │
  │                     │                       │── encode_* ───────────────────────────────▶│                    │
  │                     │                       │◀── token_ids: list[int] ───────────────────│                    │
  │                     │                       │   include_tokens? ── decode_tokens_* ──────▶│                    │
  │                     │                       │◀── tokens: list[str] ──────────────────────│                    │
  │                     │                       │── get_by_model(id) ───────────────────────────────────────────▶│
  │                     │                       │◀── PricingEntry | None ────────────────────────────────────────│
  │                     │                       │   compute estimated_input_cost            │                    │
  │                     │◀── TokenizeResponse ──│                       │                  │                    │
  │◀── 200 JSON ────────│                       │                       │                  │                    │
```

### Step-by-step (`src/services/tokenizer_service.py`)

```python
def tokenize(model_or_encoding, text, include_tokens=True, include_token_ids=True) -> TokenizeResponse:
    registry = get_model_registry()
    entry = registry.get_by_id(model_or_encoding)        # 1. resolve (raises ModelNotSupportedError → 404)
    tokenizer_ref = entry.tokenizer_ref                  # 2. e.g. "o200k_base"

    if entry.adapter == "openai_tiktoken":               # 3. dispatch on adapter field
        adapter = get_openai_adapter()
        if entry.status == "alias":                      # 4a. model alias → try tiktoken model map, fall back to ref
            token_ids = adapter.encode_for_model_with_ref(entry.id, tokenizer_ref, text)
        else:                                            # 4b. raw encoding → use the encoding directly
            token_ids = adapter.encode_with_tokenizer(tokenizer_ref, text)

        tokens = adapter.decode_tokens_with_tokenizer(tokenizer_ref, token_ids) if include_tokens else None

        pricing = get_pricing_service().get_by_model(entry.id)   # 5. cost estimation
        if pricing is not None:
            estimated_input_cost = round(len(token_ids) / 1_000_000 * pricing.input_price_per_1m, 10)
            cost_currency = pricing.currency
            cost_estimation_note = None
        else:
            estimated_input_cost = cost_currency = None
            cost_estimation_note = f"Pricing data is not available for model '{entry.id}'."

        return TokenizeResponse(...)                       # 6. assemble response

    raise ModelNotSupportedError(model_or_encoding)        # 7. unknown adapter → 404
```

Key behaviors:

- **`include_tokens` / `include_token_ids` default to `True`** in `TokenizeRequest` (this differs from the legacy README, which says `false`).
- `token_count` is always `len(token_ids)` even when `include_token_ids=False` — the count is computed from the encode, then the array is conditionally omitted from the response.
- If `entry.adapter` is anything other than `"openai_tiktoken"`, the service raises `ModelNotSupportedError`. Since **all** catalog entries currently use `openai_tiktoken`, this branch is only reachable if a future entry uses an unimplemented adapter.

---

## 2. Model-alias resolution (the core idea)

Every catalog entry has a `tokenizer_ref` field. The service **never** passes a model name to tiktoken's encoding cache directly — it always goes through the entry.

```
"gpt-4o"            status=alias  → tokenizer_ref "o200k_base"
"gpt-4"             status=alias  → tokenizer_ref "cl100k_base"
"gpt-3.5-turbo"     status=alias  → tokenizer_ref "cl100k_base"
"text-davinci-003"  status=alias  → tokenizer_ref "p50k_base"
"davinci"           status=alias  → tokenizer_ref "r50k_base"
"o200k_base"        status=stable → tokenizer_ref "o200k_base"  (a raw encoding asks for itself)
```

### Two resolution paths

The `status` field decides how the adapter is called:

**Path A — `status == "alias"` (a model name):** `encode_for_model_with_ref(model_id, tokenizer_ref, text)`

```python
# openai_tokenizer_adapter.py :: get_encoding_for_model
def get_encoding_for_model(self, model_name, tokenizer_ref):
    try:
        enc_name = encoding_name_for_model(model_name)   # ask tiktoken's built-in model→encoding map
        enc = ENCODINGS.get(enc_name)
        if enc is not None:
            return enc                                   # use tiktoken's authoritative mapping if preloaded
    except KeyError:
        pass
    return self._get_encoding_by_name(tokenizer_ref)     # else fall back to our catalog's tokenizer_ref
```

This is a **defense-in-depth** design: tiktoken's own `encoding_name_for_model()` is treated as the source of truth *when it knows the model and the encoding is preloaded*; otherwise the catalog's `tokenizer_ref` is the fallback. For most catalog entries both agree, but the fallback makes the service robust to models tiktoken doesn't recognize (e.g. `gpt-5`, `gpt-oss-*`, which tiktoken's map may not contain).

**Path B — `status != "alias"` (a raw encoding like `cl100k_base`):** `encode_with_tokenizer(tokenizer_ref, text)` — looks the encoding up directly by name in the preloaded `ENCODINGS` dict, raising `TokenizerNotAvailableError` (→ 503) if absent.

```
                       ┌─ status == "alias" ──▶ encode_for_model_with_ref
get_by_id(model) ──────┤                          └─ tiktoken map? ──yes──▶ that encoding
   (ModelEntry)        │                             └─ no/KeyError ──────▶ ENCODINGS[tokenizer_ref]
                       └─ status != "alias" ─▶ encode_with_tokenizer ────▶ ENCODINGS[tokenizer_ref]
```

---

## 3. Cost estimation flow

Cost is **input-only** and computed from the encoded token count:

```
estimated_input_cost = round( token_count / 1_000_000 * input_price_per_1m, 10 )
```

- Pricing is looked up by **model id** (`entry.id`), not by tokenizer ref. So raw encodings (`cl100k_base`) and models without a pricing row get no cost.
- When no pricing row exists, the response sets `estimated_input_cost = null`, `cost_currency = null`, and a human-readable `cost_estimation_note` such as `"Pricing data is not available for model 'cl100k_base'."`
- Output cost is **never** estimated here — tokenize has no generated output. Output prices live in the pricing catalog for reference only (see `GET /api/v1/pricing`).

---

## 4. `POST /api/v1/compare` — fan-out with soft failures

```
Client          compare router            tokenizer_service
  │  POST /compare  │                            │
  │ {models[],text} │                            │
  │ (Pydantic: 1..10 models, text 1..200k)       │
  │────────────────▶│  for model_id in models:   │
  │                 │── tokenize(model_id, ...) ─▶│   include_tokens=False
  │                 │                            │   include_token_ids=False
  │                 │◀── TokenizeResponse ───────│   (success)
  │                 │   OR catch Exception ──────│   (failure → inline error)
  │                 │  append CompareResult       │
  │◀── 200 JSON ────│  {text_length, results[]}   │
```

The compare router loops over the model list and calls the **same** `tokenizer_service.tokenize()` per model, but with `include_tokens=False, include_token_ids=False` (only the count matters). Crucially it wraps each call in `try/except`:

```python
# src/routers/compare.py (abridged)
for model_id in request.models:
    try:
        resp = tokenizer_service.tokenize(model_id, request.text, include_tokens=False, include_token_ids=False)
        results.append(CompareResult(model=model_id, resolved_tokenizer=resp.resolved_tokenizer, token_count=resp.token_count))
    except Exception as exc:
        results.append(CompareResult(model=model_id, resolved_tokenizer="unknown", token_count=0, error=str(exc)))
```

So an unsupported model yields `{resolved_tokenizer: "unknown", token_count: 0, error: "Model '...' is not supported"}` **inside a 200 response**, rather than failing the whole batch. (Note: the legacy README shows `null` for these fields; the code uses `"unknown"` and `0`.)

---

## 5. Catalog read flows (`/models`, `/pricing`)

These are pure in-memory lookups against singletons loaded at startup — no tokenizer involvement.

```
GET /api/v1/models?provider=openai&search=4o
   → ModelRegistry.get_all(group, provider, search)   # case-insensitive filters over in-memory dict
   → ModelsListResponse(items, total)

GET /api/v1/models/{id}
   → ModelRegistry.get_by_id(id)                       # dict lookup, 404 if missing

GET /api/v1/pricing?model_id=gpt-4o
   → PricingService.get_by_model(id)  (or get_all())   # dict / list over in-memory entries
   → PricingListResponse(items, total)
```

See [Core Modules](06-core-modules.md) for the registry/service internals and [API Reference](07-api-reference.md) for exact request/response shapes.

Continue to [Technology Stack & Dependencies →](04-technology-stack-and-dependencies.md)
