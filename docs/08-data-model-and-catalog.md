# 08 · Data Model & Catalog

> **There is no database.** PromptTokenizer is stateless. Its "data model" is two **static JSON files** in `src/data/`, validated into Pydantic objects at startup and held in memory as singletons. This chapter documents those files as if they were tables — they are the closest thing to a schema the project has.

| "Table" | File | Loaded by | In-memory shape | Count |
|---------|------|-----------|-----------------|-------|
| Models | `src/data/models.json` | `ModelRegistry` | `dict[id → ModelEntry]` | 34 |
| Pricing | `src/data/pricing.json` | `PricingService` | `list[PricingEntry]` + `dict[model_id → PricingEntry]` | 29 |

The relationship is a soft join: `TokenizeResponse` cost fields come from matching `ModelEntry.id == PricingEntry.model_id`. Not every model has a pricing row, and pricing has a few rows with no matching model (see below).

---

## Model catalog — `models.json` → `ModelEntry`

Schema (`src/schemas/models.py`):

| Field | Type | Required | Default | Notes |
|-------|------|----------|---------|-------|
| `id` | str | ✅ | — | Primary key. What clients pass as `model`. |
| `label` | str | ✅ | — | Display name (often same as `id`). |
| `group` | str | ✅ | — | Catalog grouping; used by the `group` filter. |
| `provider` | str | ✅ | — | e.g. `openai`; used by the `provider` filter. |
| `family` | str? | — | `null` | e.g. `gpt-4o`, `reasoning`, `embedding`, `tokenizer`. |
| `adapter` | str | ✅ | — | Which backend handles it. **All entries: `openai_tiktoken`.** |
| `tokenizer_ref` | str | ✅ | — | The tiktoken encoding to use (the alias target). |
| `status` | str | ✅ | — | `"alias"` (a model) or `"stable"` (a raw encoding). Drives the resolution path. |
| `context_window` | int? | — | `null` | Max context tokens (informational). |
| `max_output_tokens` | int? | — | `null` | Max output tokens (informational). |
| `knowledge_cutoff` | str? | — | `null` | Free-text date. |
| `supports_token_decode` | bool | — | `true` | Metadata flag (not enforced in code). |
| `supports_browser` | bool | — | `true` | Metadata flag (for UI hints). |
| `deprecated` | bool | — | `false` | Legacy/retired models. |
| `notes` | str? | — | `null` | Free-text. |
| `description` | str? | — | `null` | Searchable description. |

### Groups & what's in them

| `group` | Count | `status` | Examples |
|---------|-------|----------|----------|
| `OpenAI Encodings` | 6 | `stable` | `o200k_base`, `cl100k_base`, `p50k_base`, `p50k_edit`, `r50k_base`, `gpt2` |
| `OpenAI OpenSource Models` | 2 | `alias` | `gpt-oss-20b`, `gpt-oss-120b` |
| `OpenAI Models` | 26 | `alias` | `gpt-5*`, `gpt-4o*`, `gpt-4*`, `gpt-3.5*`, `o1/o3/o4-mini`, embeddings, legacy `davinci`/`curie`/… |

### The six encodings (the actual tokenizers)

These are the only real tokenizers; every model alias points at one of them.

| Encoding | Used by (examples) |
|----------|--------------------|
| `o200k_base` | GPT-5 family, GPT-4o family, o1/o3/o4-mini, gpt-oss-* |
| `cl100k_base` | GPT-4, GPT-4-turbo, GPT-3.5-turbo, text-embedding-3-* / ada-002 |
| `p50k_base` | text-davinci-002/003, code-davinci-002 |
| `p50k_edit` | edit models |
| `r50k_base` | legacy GPT-3: davinci, curie, babbage, ada, text-davinci-001 |
| `gpt2` | GPT-2 |

> Only encodings listed in `src/config/config.yaml` are preloaded — and all six catalog encodings are in that list. If you add a catalog entry whose `tokenizer_ref` is **not** in `config.yaml`, requests for it will fail with `503 TOKENIZER_NOT_AVAILABLE`. See [Extending](17-design-patterns-and-extending.md).

### `status` semantics

- **`alias`** → tokenize uses `encode_for_model_with_ref()`: it first asks tiktoken's own model→encoding map, falling back to `tokenizer_ref`.
- **`stable`** (the raw encodings) → tokenize uses `encode_with_tokenizer()`: the `tokenizer_ref` (which equals `id`) is looked up directly.

---

## Pricing catalog — `pricing.json` → `PricingEntry`

Schema (`src/schemas/pricing.py`):

| Field | Type | Required | Default | Notes |
|-------|------|----------|---------|-------|
| `model_id` | str | ✅ | — | Join key to `ModelEntry.id`. |
| `input_price_per_1m` | float | ✅ | — | USD per 1M input tokens. Drives cost estimation. |
| `output_price_per_1m` | float? | — | `null` | USD per 1M output tokens; `null` for embeddings/legacy completion models. |
| `currency` | str | — | `"USD"` | |
| `last_updated` | str? | — | `null` | ISO date. |

The 29 pricing rows cover GPT-5 family, GPT-4 family, GPT-3.5, the o-series (incl. `o1-pro`, `o3-mini`), realtime models, embeddings, legacy completion models, and gpt-oss-*.

### Join coverage notes (important for accurate cost output)

- **Models with no pricing row** (e.g. raw encodings, `gpt-5`-vs-… check, `text-davinci-001`, `code-davinci-002`) → tokenize returns `estimated_input_cost: null` and a `cost_estimation_note`.
- **Pricing rows with no matching model entry** exist in the data: `o1-pro`, `o3-mini`, `gpt-realtime`, `gpt-realtime-mini`. These appear in `GET /api/v1/pricing` but are not tokenizable (no catalog entry), so they can never drive a cost estimate. This is harmless but worth knowing.
- Cost estimation **always** uses `input_price_per_1m`; output pricing is reference-only.

---

## Data lifecycle

```
Process start
   │
   ├─ get_model_registry()  →  read models.json  →  validate each row into ModelEntry  →  cache (lru_cache)
   ├─ get_pricing_service() →  read pricing.json →  validate each row into PricingEntry →  cache (lru_cache)
   │
Request time
   └─ pure in-memory dict/list lookups; files are never re-read
```

Because the singletons are `@lru_cache`, **editing the JSON requires a process restart** to take effect. There is no hot-reload of catalogs in production (dev `--reload` restarts the process on source changes, but JSON files under `src/data/` are watched only if changed and `--reload-dir src` includes them — a manual restart is the reliable path).

### Validation guarantees

Because every row is constructed as `ModelEntry(**row)` / `PricingEntry(**row)`, a malformed catalog file (missing a required field, wrong type) raises a Pydantic `ValidationError` **at startup**, not at request time — the app will fail fast rather than serve corrupt data. This is a deliberate fail-fast property.

Continue to [Configuration & Environment Variables →](09-configuration.md)
