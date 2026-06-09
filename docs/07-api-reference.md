# 07 · API Reference & Contracts

Base URL (default local): `http://localhost:8000`
Versioned prefix: `API_PREFIX` (default `/api/v1`).

All request/response bodies are JSON. All responses are produced from Pydantic models, so field names and types are exact. There is **no authentication** — see [Security](10-security-and-auth.md).

> **Interactive docs:** when `APP_ENV=dev`, Swagger UI is at `/docs`, ReDoc at `/redoc`, and the raw schema at `/openapi.json`. In any other environment these are **disabled** (return 404).

## Endpoint summary

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/health` | Liveness + process memory |
| GET | `/api/v1/models` | List/filter the model catalog |
| GET | `/api/v1/models/{model_id}` | Fetch one catalog entry |
| POST | `/api/v1/tokenize` | Tokenize text for one model |
| POST | `/api/v1/compare` | Token counts across many models |
| GET | `/api/v1/pricing` | Pricing catalog (all or one model) |

---

## Standard error envelope

Every error response (4xx/5xx) has this shape:

```json
{
  "error": {
    "code": "MODEL_NOT_SUPPORTED",
    "message": "Model 'gpt-99' is not supported",
    "details": null
  }
}
```

| Code | HTTP | When |
|------|------|------|
| `VALIDATION_ERROR` | 422 | Request body/params fail Pydantic validation (`details` = field errors) |
| `MODEL_NOT_SUPPORTED` | 404 | Model id not in the catalog (or its adapter is unimplemented) |
| `TOKENIZER_NOT_AVAILABLE` | 503 | Resolved encoding not loaded in memory |
| `INTERNAL_ERROR` | 500 | Any unhandled exception (message is generic) |
| `INVALID_COMPARE_REQUEST` | 400 | Reserved (defined but not currently raised) |

---

## `GET /health`

No prefix, no auth. Used for liveness probes and quick memory inspection.

**Response `200`**
```json
{
  "status": "ok",
  "service": "prompt-tokenizer",
  "version": "0.1.0",
  "memory": { "rss_mb": 45.12, "vms_mb": 312.50 }
}
```

| Field | Meaning |
|-------|---------|
| `status` | Always `"ok"` if the process is serving |
| `service` | `settings.app_name` |
| `version` | `settings.app_version` |
| `memory.rss_mb` | Resident set size (physical RAM), MB, 2 dp |
| `memory.vms_mb` | Virtual memory size, MB, 2 dp |

Memory is read from the **current process only** via `psutil.Process(os.getpid())`. Under Gunicorn with multiple workers, you get the stats of whichever worker served the request.

---

## `GET /api/v1/models`

Lists catalog entries (both raw encodings and model aliases).

**Query parameters** (all optional, combine with AND)

| Param | Type | Behavior |
|-------|------|----------|
| `group` | string | Case-insensitive **exact** match on `group` (e.g. `OpenAI Models`, `OpenAI Encodings`, `OpenAI OpenSource Models`) |
| `provider` | string | Case-insensitive exact match on `provider` (e.g. `openai`) |
| `search` | string | Case-insensitive **substring** over `id`, `label`, `description` |

**Response `200`** — `ModelsListResponse`
```json
{
  "items": [ { /* ModelEntry */ } ],
  "total": 34
}
```

`total` equals `len(items)` for the **filtered** set (it is not the catalog size when filters are applied).

Each item is a `ModelEntry` (see [Data Model](08-data-model-and-catalog.md) for every field):

```json
{
  "id": "gpt-4o",
  "label": "gpt-4o",
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
  "notes": null,
  "description": "OpenAI GPT-4o multimodal model"
}
```

**Examples**
```bash
curl 'localhost:8000/api/v1/models?provider=openai'
curl 'localhost:8000/api/v1/models?group=OpenAI%20Encodings'
curl 'localhost:8000/api/v1/models?search=4o'
```

---

## `GET /api/v1/models/{model_id}`

Returns a single `ModelEntry` by id.

**Response `200`** — a `ModelEntry` object (shape above).

**Response `404`** when the id is unknown:
```json
{ "error": { "code": "MODEL_NOT_SUPPORTED", "message": "Model 'gpt-99' is not supported", "details": null } }
```

```bash
curl localhost:8000/api/v1/models/gpt-4o
```

---

## `POST /api/v1/tokenize`

Tokenize text for one model or raw encoding.

**Request body** — `TokenizeRequest`

| Field | Type | Required | Default | Constraints |
|-------|------|----------|---------|-------------|
| `model` | string | yes | — | A catalog `id` (model alias or encoding name) |
| `text` | string | yes | — | length **1–200,000** chars |
| `include_tokens` | bool | no | **`true`** | include decoded token strings |
| `include_token_ids` | bool | no | **`true`** | include integer token ids |

> ⚠️ Defaults are `true` (the legacy README says `false`).

**Response `200`** — `TokenizeResponse`

```json
{
  "model": "gpt-4o",
  "resolved_tokenizer": "o200k_base",
  "provider": "openai",
  "token_count": 2,
  "tokens": ["Hello", " world"],
  "token_ids": [13225, 2375],
  "word_count": 2,
  "character_count": 11,
  "estimated_input_cost": 0.0000025,
  "cost_currency": "USD",
  "cost_estimation_note": null
}
```

| Field | Meaning |
|-------|---------|
| `model` | Echo of the requested model string |
| `resolved_tokenizer` | The tiktoken encoding actually used (the `tokenizer_ref`) |
| `provider` | From the catalog entry |
| `token_count` | Number of tokens (always present) |
| `tokens` | Per-token strings, or `null` if `include_tokens=false` |
| `token_ids` | Integer ids, or `null` if `include_token_ids=false` |
| `word_count` | `len(text.split())` — whitespace word count |
| `character_count` | `len(text)` |
| `estimated_input_cost` | `token_count / 1e6 * input_price_per_1m`, rounded to 10 dp; `null` if no pricing |
| `cost_currency` | e.g. `"USD"`; `null` if no pricing |
| `cost_estimation_note` | `null` normally; an explanatory string when pricing is missing |

**Errors**

| Case | Status / code |
|------|---------------|
| Empty text / text > 200k / wrong types | 422 `VALIDATION_ERROR` |
| Unknown model | 404 `MODEL_NOT_SUPPORTED` |
| Encoding not loaded | 503 `TOKENIZER_NOT_AVAILABLE` |

```bash
curl -X POST localhost:8000/api/v1/tokenize \
  -H 'Content-Type: application/json' \
  -d '{"model":"gpt-4o","text":"Hello world","include_tokens":true,"include_token_ids":true}'
```

**Tokenizing a raw encoding** (no pricing → note populated):
```json
// POST {"model":"r50k_base","text":"Hello world"}
{
  "model": "r50k_base", "resolved_tokenizer": "r50k_base", "provider": "openai",
  "token_count": 2, "tokens": ["Hello"," world"], "token_ids": [...],
  "word_count": 2, "character_count": 11,
  "estimated_input_cost": null, "cost_currency": null,
  "cost_estimation_note": "Pricing data is not available for model 'r50k_base'."
}
```

---

## `POST /api/v1/compare`

Tokenize the same text against multiple models; counts only.

**Request body** — `CompareRequest`

| Field | Type | Constraints |
|-------|------|-------------|
| `models` | string[] | **1–10** items |
| `text` | string | length **1–200,000** |

**Response `200`** — `CompareResponse`

```json
{
  "text_length": 11,
  "results": [
    { "model": "gpt-4o",        "resolved_tokenizer": "o200k_base",  "token_count": 2, "error": null },
    { "model": "gpt-3.5-turbo", "resolved_tokenizer": "cl100k_base", "token_count": 2, "error": null },
    { "model": "bogus",         "resolved_tokenizer": "unknown",     "token_count": 0, "error": "Model 'bogus' is not supported" }
  ]
}
```

| Field | Meaning |
|-------|---------|
| `text_length` | `len(text)` |
| `results[].model` | Echo of the requested model |
| `results[].resolved_tokenizer` | Encoding used, or `"unknown"` on failure |
| `results[].token_count` | Count, or `0` on failure |
| `results[].error` | `null` on success, or the error message string on failure |

**Soft-failure design:** an unsupported model does **not** fail the request — it returns an inline `error` with `resolved_tokenizer:"unknown"`, `token_count:0`. The whole call is still `200`. (Legacy README shows `null` for these — the code uses `"unknown"`/`0`.)

**Hard errors** (whole request 422): empty `models`, more than 10 models, or invalid `text`.

```bash
curl -X POST localhost:8000/api/v1/compare \
  -H 'Content-Type: application/json' \
  -d '{"models":["gpt-4o","gpt-4","r50k_base"],"text":"Hello world"}'
```

---

## `GET /api/v1/pricing`

Returns the pricing catalog, or a single entry.

**Query parameter**

| Param | Type | Behavior |
|-------|------|----------|
| `model_id` | string | If given, returns just that entry (or empty list if unknown) |

**Response `200`** — `PricingListResponse`
```json
{
  "items": [
    { "model_id": "gpt-4o", "input_price_per_1m": 2.5, "output_price_per_1m": 10.0, "currency": "USD", "last_updated": "2024-05-13" }
  ],
  "total": 1
}
```

| Field | Meaning |
|-------|---------|
| `model_id` | Model the price applies to |
| `input_price_per_1m` | USD per 1,000,000 input tokens |
| `output_price_per_1m` | USD per 1,000,000 output tokens, or `null` (e.g. embeddings) |
| `currency` | Default `"USD"` |
| `last_updated` | ISO date string or `null` |

Unknown `model_id` returns `200` with `{"items": [], "total": 0}` (not a 404).

```bash
curl localhost:8000/api/v1/pricing
curl 'localhost:8000/api/v1/pricing?model_id=gpt-4o'
```

Continue to [Data Model & Catalog →](08-data-model-and-catalog.md)
