# 16 · Performance & Optimizations

PromptTokenizer is CPU-light per request (a tokenize is a BPE encode over bounded text) but pays a real **one-time cost** to load tiktoken encodings. The design pushes that cost to startup and shares everything thereafter.

## The hot path

```
POST /tokenize
  → registry.get_by_id()        # O(1) dict lookup, in-memory
  → adapter.encode_*()          # tiktoken BPE encode — the actual CPU work
  → adapter.decode_*() (opt)    # per-token byte decode, only if include_tokens
  → pricing.get_by_model()      # O(1) dict lookup, in-memory
  → assemble TokenizeResponse   # Pydantic serialization
```

Everything except the encode (and optional decode) is O(1) in-memory work. No disk I/O, no network, no locks.

## Optimization 1 — preload encodings at startup

`preload_encodings()` runs in the **lifespan**, loading all six encodings from `config.yaml` into the module-level `ENCODINGS` dict before the first request. tiktoken encoding construction (building the BPE merge table) is the expensive part; doing it once at boot means **no request ever pays lazy-load latency**.

- Startup time is measured and logged: `"Application started in X.Xms"`.
- `preload_encodings()` is **idempotent** — it skips already-loaded encodings, so calling it from both the lifespan and lazily from `get_openai_adapter()` is safe.

## Optimization 2 — singletons for all expensive objects

| Object | Cached via | Built once because |
|--------|-----------|--------------------|
| `Settings` | `@lru_cache get_settings()` | `.env`/env parsing |
| `ModelRegistry` | `@lru_cache get_model_registry()` | reads + validates `models.json` (34 rows) |
| `PricingService` | `@lru_cache get_pricing_service()` | reads + validates `pricing.json` (29 rows) |
| `OpenAITokenizerAdapter` | module-level `_adapter_instance` | trivial object, but avoids re-preload |
| `ENCODINGS[name]` | module-level dict | tiktoken BPE tables (the big cost) |

No request re-reads JSON, re-parses `.env`, or re-instantiates an encoding. The catalogs become plain dict lookups.

## Optimization 3 — indexed lookups

- `ModelRegistry` keys entries by `id` in a dict → `get_by_id` is O(1).
- `PricingService` keeps both a list (`get_all`) and a `_by_model` dict (`get_by_model`) → O(1) price lookup.
- Filtered `get_all(group, provider, search)` is O(n) over 34 entries — negligible.

## Optimization 4 — bounded work per request

Input caps (`text` ≤ 200,000 chars, `compare.models` ≤ 10) put a hard ceiling on the CPU any single request can consume. A compare request is at most 10 sequential encodes of ≤200k chars. See [Security](10-security-and-auth.md).

## Optimization 5 — skip work the caller doesn't want

- `include_token_ids=False` → the `token_ids` array is omitted from the response (smaller payload). The encode still runs (needed for `token_count`).
- `include_tokens=False` → the **per-token decode loop is skipped entirely** (real CPU savings). `/compare` always uses `include_tokens=False, include_token_ids=False`, so it only does the minimal encode-and-count per model.

## Optimization 6 — concurrency model

- **Dev:** single Uvicorn process.
- **Prod:** Gunicorn runs `WORKERS` Uvicorn worker processes, using multiple cores. The endpoints are defined as **sync** `def` handlers, so FastAPI runs them in a threadpool — appropriate for CPU-bound tokenization (they don't block the event loop).

The service holds **no shared mutable state** after startup (`ENCODINGS` is populated once and only read), so workers/threads need no locking.

## Memory considerations

The dominant memory cost is the tiktoken encodings, especially `o200k_base` and `cl100k_base` (large merge tables). Two consequences:

1. **Per-worker, not shared.** Each Gunicorn worker is a separate process and loads its own copy. Total RAM ≈ `WORKERS × per-worker footprint`. Size `WORKERS` against RAM, not just CPU count. (The committed `.env` uses `WORKERS=2`.)
2. **`/health` exposes it.** `rss_mb`/`vms_mb` from `psutil` let you watch a worker's footprint.

## Docker startup speed

The image sets `UV_COMPILE_BYTECODE=1` (precompiled `.pyc`) and `PYTHONDONTWRITEBYTECODE=1`, trimming import time. The layered dependency install keeps rebuilds fast during development.

## Potential future optimizations (not implemented)

| Idea | Benefit | Trade-off |
|------|---------|-----------|
| Lazy-load only encodings actually requested | lower memory if few models used | first-use latency spike |
| Batch encode in `/compare` by grouping models that share an encoding | dedupe identical encodes | minor complexity; today each model encodes independently even if refs match |
| Cache results by `(model, text-hash)` | repeat-request speed | memory; only helps with repeated identical inputs |
| Async/streaming for very large inputs | smoother large-text handling | tiktoken is sync; limited upside |

The single highest-value cheap win available: in `/compare`, multiple models often share the same `tokenizer_ref` (e.g. `gpt-4` and `gpt-3.5-turbo` both → `cl100k_base`) — encoding once per distinct ref instead of once per model would cut redundant work. Today the code encodes per model.

Continue to [Design Patterns & Extending →](17-design-patterns-and-extending.md)
