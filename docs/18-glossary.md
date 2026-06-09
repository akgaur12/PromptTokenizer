# 18 · Glossary

Concepts and terms used throughout this documentation and codebase.

### Adapter
A class implementing `BaseTokenizerAdapter` that wraps a specific tokenizer library. The only shipped adapter is `OpenAITokenizerAdapter` (`adapter_name = "openai_tiktoken"`). See [Core Modules](06-core-modules.md).

### Alias (model alias)
A catalog entry with `status: "alias"` — a public model name (e.g. `gpt-4o`) that points at an underlying encoding via `tokenizer_ref`. Contrast with a raw **encoding** entry (`status: "stable"`).

### ASGI
Asynchronous Server Gateway Interface — the Python async web-server standard FastAPI speaks. Served by **Uvicorn** (dev) / **Gunicorn + UvicornWorker** (prod).

### BPE (Byte-Pair Encoding)
The tokenization algorithm tiktoken uses. Text is split into subword tokens by iteratively merging frequent byte pairs. Why a single character can span multiple tokens (and why per-token decode is best-effort).

### Catalog
The static data describing models and pricing — `src/data/models.json` and `src/data/pricing.json`. The project's "database." See [Data Model](08-data-model-and-catalog.md).

### Context window
Maximum number of tokens a model can attend to (input + output). Stored as `context_window` metadata; informational only — not enforced by the service.

### CORS (Cross-Origin Resource Sharing)
Browser security mechanism controlling which web origins may call the API. Configured via `ALLOWED_ORIGINS`. See [Security](10-security-and-auth.md).

### Encoding (tiktoken encoding)
A concrete BPE vocabulary/merge table, named e.g. `o200k_base`, `cl100k_base`, `p50k_base`, `r50k_base`, `gpt2`, `p50k_edit`. The actual tokenizer. Models map to one of these via `tokenizer_ref`.

### Error envelope
The uniform JSON error shape `{"error": {"code", "message", "details"}}` returned by every failure. See [Error Handling](11-error-handling-and-logging.md).

### `ExactLevelFilter`
Custom logging filter admitting only records of one exact level, enabling one-file-per-level logs. See [Logging](11-error-handling-and-logging.md).

### Lifespan
FastAPI's async startup/shutdown context manager. Here it preloads tiktoken encodings and logs the startup banner/timing.

### `lru_cache` singleton
The `@functools.lru_cache` decorator used on zero-arg factory functions (`get_settings`, `get_model_registry`, `get_pricing_service`) so the expensive object is built once per process and reused.

### Model id
The primary key of a catalog entry and the value clients send as `model`. Exact-match (case-sensitive) lookup.

### Preload
Loading all configured tiktoken encodings into the `ENCODINGS` dict at startup (`preload_encodings()`), so requests never pay lazy-load latency.

### Provider
The organization behind a model (`openai` for all current entries). A `/models` filter dimension.

### `resolved_tokenizer`
The encoding actually used for a tokenize call (the resolved `tokenizer_ref`), echoed back in responses so clients can see which tokenizer produced the count.

### `status`
Catalog field distinguishing `"alias"` (a model → uses tiktoken-map + ref fallback) from `"stable"` (a raw encoding → used directly). Drives the resolution path in `tokenizer_service`.

### Token
The atomic unit a model reads/produces. Token **count** drives context budgeting and cost. A token is often a word fragment, not a whole word.

### `tokenizer_ref`
The catalog field naming which tiktoken encoding a model uses. The lynchpin of alias resolution — the service always tokenizes via the ref, never the raw model name.

### Twelve-Factor config
The principle of storing config in the environment (env vars / `.env`) rather than code. This project follows it via `pydantic-settings`. See [Configuration](09-configuration.md).

### uv
Astral's fast Python package/_environment_ manager. The authoritative install path (`uv sync` against `uv.lock`).

---

## Acronyms

| Acronym | Meaning |
|---------|---------|
| ABC | Abstract Base Class |
| ADR | Architecture Decision Record |
| API | Application Programming Interface |
| ASGI | Asynchronous Server Gateway Interface |
| BPE | Byte-Pair Encoding |
| CORS | Cross-Origin Resource Sharing |
| LLM | Large Language Model |
| RSS | Resident Set Size (physical memory) |
| VMS | Virtual Memory Size |
| TLS | Transport Layer Security |
| WAF | Web Application Firewall |

---

← Back to [Documentation Index](index.md)
