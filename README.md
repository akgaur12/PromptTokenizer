# PromptTokenizer

A production-ready FastAPI backend that tokenizes text using OpenAI encodings (via `tiktoken`), resolves model aliases to their underlying tokenizers, compares token counts across models, and exposes pricing metadata — all through a clean REST API.

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Project Structure](#project-structure)
3. [Setup & Installation](#setup--installation)
4. [Configuration](#configuration)
5. [Running the Application](#running-the-application)
6. [API Reference](#api-reference)
7. [Data Flow](#data-flow)
8. [Key Modules](#key-modules)
9. [Design Decisions](#design-decisions)
10. [Logging](#logging)
11. [Testing](#testing)
12. [Extending the Project](#extending-the-project)

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         HTTP Client                             │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    FastAPI Application                          │
│                                                                 │
│   ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐   │
│   │  /health │   │ /models  │   │/tokenize │   │/compare  │   │
│   └──────────┘   └──────────┘   └────┬─────┘   └────┬─────┘   │
│                                       │               │         │
│   ┌───────────────────────────────────▼───────────────▼──────┐ │
│   │                    Service Layer                          │ │
│   │  ┌────────────────┐  ┌──────────────┐  ┌─────────────┐  │ │
│   │  │ ModelRegistry  │  │TokenizerSvc  │  │PricingService│  │ │
│   │  └───────┬────────┘  └──────┬───────┘  └──────┬──────┘  │ │
│   └──────────┼───────────────── │ ─────────────── │ ────────┘ │
│              │                  │                  │            │
│   ┌──────────▼──────────────────▼──────┐  ┌───────▼─────────┐ │
│   │         Adapter Layer              │  │   Data Layer     │ │
│   │  ┌─────────────────────────────┐   │  │  models.json     │ │
│   │  │  OpenAITokenizerAdapter     │   │  │  pricing.json    │ │
│   │  │  (tiktoken)                 │   │  └─────────────────┘ │
│   │  └─────────────────────────────┘   │                       │
│   └────────────────────────────────────┘                       │
└─────────────────────────────────────────────────────────────────┘
```

The application is organized into four horizontal layers:

| Layer | Responsibility |
|-------|---------------|
| **Router** | HTTP request/response handling, input validation via Pydantic |
| **Service** | Business logic — model resolution, tokenization, pricing lookup |
| **Adapter** | Tokenizer backend abstraction (`tiktoken` today, extensible) |
| **Data** | Static JSON files for model catalog and pricing |

---

## Project Structure

```
PromptTokenizer/
├── run.py                        # Entry point (dev / prod modes)
├── pyproject.toml                # Project metadata, deps, ruff config
├── .env.example                  # Environment variable template
├── .python-version               # Pinned Python version (3.13)
│
├── src/
│   ├── main.py                   # FastAPI app factory + lifespan
│   │
│   ├── core/                     # Cross-cutting infrastructure
│   │   ├── config.py             # Pydantic Settings (env vars + .env)
│   │   ├── cors.py               # CORS middleware setup
│   │   ├── exceptions.py         # Custom exceptions + global handlers
│   │   └── logger.py             # YAML-based logging bootstrap
│   │
│   ├── adapters/                 # Tokenizer backend abstraction
│   │   └── base.py               # BaseTokenizerAdapter (ABC)
│   │
│   ├── routers/                  # FastAPI route handlers
│   │   ├── health.py             # GET /health
│   │   ├── models.py             # GET /api/v1/models[/{id}]
│   │   ├── tokenize.py           # POST /api/v1/tokenize
│   │   ├── compare.py            # POST /api/v1/compare
│   │   └── pricing.py            # GET /api/v1/pricing
│   │
│   ├── schemas/                  # Pydantic request/response models
│   │   ├── common.py             # ErrorDetail, ErrorResponse
│   │   ├── tokenize.py           # TokenizeRequest/Response
│   │   ├── compare.py            # CompareRequest/Response
│   │   ├── models.py             # ModelEntry, ModelsListResponse
│   │   └── pricing.py            # PricingEntry, PricingListResponse
│   │
│   ├── services/                 # Business logic
│   │   ├── model_registry.py     # Model catalog (loads models.json)
│   │   ├── tokenizer_service.py  # Tokenization orchestration
│   │   ├── openai_tokenizer_adapter.py  # tiktoken implementation
│   │   └── pricing_service.py    # Pricing lookup (loads pricing.json)
│   │
│   ├── utils/
│   │   └── text.py               # truncate_text()
│   │
│   ├── config/
│   │   └── logging.yaml          # Rotating file + console handlers
│   │
│   └── data/
│       ├── models.json           # 32 model / encoding definitions
│       └── pricing.json          # 9 pricing entries (USD per 1M tokens)
│
└── tests/
    ├── conftest.py               # Shared AsyncClient fixture
    ├── test_health.py
    ├── test_models.py
    ├── test_tokenize.py
    └── test_compare.py
```

---

## Setup & Installation

### Prerequisites

- Python 3.13+
- [uv](https://docs.astral.sh/uv/) (recommended) or pip

### With uv (recommended)

```bash
# Clone the repository
git clone <repo-url>
cd PromptTokenizer

# Install all dependencies and create .venv
uv sync

# Copy and configure environment
cp .env.example .env
```

### With pip (alternative)

```bash
python -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

---

## Configuration

All configuration is driven by environment variables. Copy `.env.example` to `.env` and edit as needed.

| Variable | Default | Description |
|----------|---------|-------------|
| `APP_NAME` | `prompt-tokenizer` | Application name shown in logs and API metadata |
| `APP_ENV` | `development` | Environment tag (`development` / `production`) |
| `APP_HOST` | `0.0.0.0` | Bind address |
| `APP_PORT` | `8000` | Bind port |
| `APP_VERSION` | `0.1.0` | Version string shown in API metadata |
| `ALLOWED_ORIGINS` | `http://localhost:3000,...` | Comma-separated CORS allowed origins |
| `LOG_LEVEL` | `INFO` | Root log level (`DEBUG` / `INFO` / `WARNING` / `ERROR`) |
| `API_PREFIX` | `/api/v1` | URL prefix for versioned routes |
| `WORKERS` | `4` | Gunicorn worker count (production only) |
| `TIMEOUT` | `120` | Gunicorn worker timeout in seconds |
| `GRACEFUL_TIMEOUT` | `30` | Gunicorn graceful shutdown timeout in seconds |

Settings are loaded by `src/core/config.py` via `pydantic-settings`. Values in `.env` override defaults; environment variables override `.env`.

---

## Running the Application

### Development (hot-reload, watches `src/` only)

```bash
uv run start dev
# or
python run.py dev
```

### Production (gunicorn + UvicornWorker)

```bash
uv run start
# or
python run.py
```

### Uvicorn directly

```bash
uv run uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
```

Interactive API docs are available at:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

---

## API Reference

### `GET /health`

Returns service liveness status and process memory usage. No authentication required.

**Response `200`**
```json
{
  "status": "ok",
  "service": "prompt-tokenizer",
  "version": "0.1.0",
  "memory": {
    "rss_mb": 45.12,
    "vms_mb": 312.50
  }
}
```

| Field | Description |
|-------|-------------|
| `memory.rss_mb` | Resident Set Size — actual physical RAM currently in use by the process (MB) |
| `memory.vms_mb` | Virtual Memory Size — total virtual address space allocated to the process (MB) |

---

### `GET /api/v1/models`

Lists all models and raw encodings in the catalog.

**Query Parameters**

| Parameter | Type | Description |
|-----------|------|-------------|
| `group` | string | Filter by group: `encoding`, `chat`, `embedding`, `legacy` |
| `provider` | string | Filter by provider (e.g. `openai`) |
| `search` | string | Substring match on model id, label, or description |

**Response `200`**
```json
{
  "items": [
    {
      "id": "gpt-4o",
      "label": "GPT-4o",
      "group": "chat",
      "provider": "openai",
      "adapter": "openai",
      "tokenizer_ref": "o200k_base",
      "status": "stable",
      "description": "Latest GPT-4o model",
      "context_window": 128000,
      "supports_token_decode": true,
      "supports_browser": true,
      "deprecated": false
    }
  ],
  "total": 32
}
```

---

### `GET /api/v1/models/{model_id}`

Returns a single model by its catalog ID.

**Response `404`** when model is not in the registry:
```json
{
  "error": {
    "code": "MODEL_NOT_SUPPORTED",
    "message": "Model 'gpt-99' is not supported.",
    "details": null
  }
}
```

---

### `POST /api/v1/tokenize`

Tokenizes text using the specified model or encoding.

**Request Body**
```json
{
  "model": "gpt-4o",
  "text": "Hello, world!",
  "include_tokens": true,
  "include_token_ids": true
}
```

| Field | Required | Constraints | Description |
|-------|----------|-------------|-------------|
| `model` | yes | — | Model ID or encoding name from catalog |
| `text` | yes | 1–200,000 chars | Text to tokenize |
| `include_tokens` | no | default `false` | Include decoded token strings |
| `include_token_ids` | no | default `false` | Include raw token integer IDs |

**Response `200`**
```json
{
  "model": "gpt-4o",
  "resolved_tokenizer": "o200k_base",
  "provider": "openai",
  "token_count": 4,
  "tokens": ["Hello", ",", " world", "!"],
  "token_ids": [9906, 11, 1917, 0]
}
```

---

### `POST /api/v1/compare`

Tokenizes the same text with multiple models and returns counts side by side.

**Request Body**
```json
{
  "models": ["gpt-4o", "gpt-3.5-turbo", "gpt-4"],
  "text": "Hello, world!"
}
```

| Field | Constraints | Description |
|-------|-------------|-------------|
| `models` | 1–10 items | List of model IDs to compare |
| `text` | 1–200,000 chars | Text to tokenize |

**Response `200`**
```json
{
  "text_length": 13,
  "results": [
    { "model": "gpt-4o",        "resolved_tokenizer": "o200k_base",  "token_count": 4, "error": null },
    { "model": "gpt-3.5-turbo", "resolved_tokenizer": "cl100k_base", "token_count": 4, "error": null },
    { "model": "gpt-4",         "resolved_tokenizer": "cl100k_base", "token_count": 4, "error": null }
  ]
}
```

Unsupported models return an inline error instead of failing the whole request:
```json
{ "model": "unknown-model", "resolved_tokenizer": null, "token_count": null, "error": "Model 'unknown-model' is not supported." }
```

---

### `GET /api/v1/pricing`

Returns pricing metadata for all models, or a single model.

**Query Parameters**

| Parameter | Type | Description |
|-----------|------|-------------|
| `model_id` | string | Filter to a specific model |

**Response `200`**
```json
{
  "items": [
    {
      "model_id": "gpt-4o",
      "input_price_per_1m": 5.0,
      "output_price_per_1m": 15.0,
      "currency": "USD",
      "last_updated": "2024-05-13"
    }
  ],
  "total": 1
}
```

---

## Data Flow

### Tokenize request end-to-end

```
POST /api/v1/tokenize
        │
        ▼
TokenizeRequest validated by Pydantic
  - model: str
  - text: str (1–200k chars)
  - include_tokens: bool
  - include_token_ids: bool
        │
        ▼
tokenize_router calls tokenizer_service.tokenize()
        │
        ▼
tokenizer_service:
  1. ModelRegistry.get_by_id(model)      → ModelEntry (or raises 404)
  2. entry.tokenizer_ref                  → e.g. "o200k_base" for "gpt-4o"
  3. OpenAITokenizerAdapter.encode()     → List[int] token IDs
  4. Optionally decode token IDs         → List[str] token strings
        │
        ▼
TokenizeResponse assembled and returned
  - model, resolved_tokenizer, provider
  - token_count, tokens?, token_ids?
```

### Model alias resolution

Models in `models.json` have a `tokenizer_ref` field that maps the public model name to the underlying tiktoken encoding:

```
"gpt-4o"         → tokenizer_ref: "o200k_base"
"gpt-4"          → tokenizer_ref: "cl100k_base"
"gpt-3.5-turbo"  → tokenizer_ref: "cl100k_base"
"text-davinci-003" → tokenizer_ref: "p50k_base"
```

The service layer always uses `tokenizer_ref` to call tiktoken, never the raw model name, which makes the system robust to model name changes.

---

## Key Modules

### `src/core/config.py`

Central settings object using `pydantic-settings`. The `@lru_cache` on `get_settings()` means the `.env` file is read exactly once per process.

```python
from src.core.config import get_settings
settings = get_settings()
print(settings.app_port)  # 8000
```

### `src/core/exceptions.py`

Defines domain exceptions and maps them to HTTP status codes via FastAPI exception handlers registered in `create_app()`.

| Exception | HTTP Status | Error Code |
|-----------|-------------|------------|
| `ModelNotSupportedError` | 404 | `MODEL_NOT_SUPPORTED` |
| `TokenizerNotAvailableError` | 503 | `TOKENIZER_NOT_AVAILABLE` |
| `InvalidCompareRequestError` | 400 | `INVALID_COMPARE_REQUEST` |
| `RequestValidationError` | 422 | `VALIDATION_ERROR` |
| Any other exception | 500 | `INTERNAL_ERROR` |

### `src/adapters/base.py`

Abstract base class that all tokenizer backends must implement:

```python
class BaseTokenizerAdapter(ABC):
    @abstractmethod
    def encode(self, text: str, model: str) -> list[int]: ...

    @abstractmethod
    def decode_tokens(self, token_ids: list[int], model: str) -> list[str]: ...

    @abstractmethod
    def count_tokens(self, text: str, model: str) -> int: ...

    @abstractmethod
    def supports_model(self, model: str) -> bool: ...
```

### `src/services/model_registry.py`

Loads `src/data/models.json` at startup and provides indexed lookups. The registry is a singleton (`@lru_cache`) so the JSON file is read once.

```python
registry = get_model_registry()
entry = registry.get_by_id("gpt-4o")      # raises ModelNotSupportedError if missing
ref   = registry.resolve_tokenizer_ref("gpt-4o")  # "o200k_base"
```

### `src/services/openai_tokenizer_adapter.py`

Wraps `tiktoken`. Encoding objects are cached in a dict keyed by encoding name so they are not re-instantiated on every request.

```python
adapter = get_openai_adapter()
ids     = adapter.encode_with_tokenizer("Hello world", "cl100k_base")  # [9906, 1917]
tokens  = adapter.decode_tokens_with_tokenizer(ids, "cl100k_base")     # ["Hello", " world"]
```

Special tokens that cannot be decoded are returned as `"<{id}>"` strings (e.g. `"<100264>"`).

### `src/data/models.json`

The single source of truth for the model catalog. Each entry shape:

```json
{
  "id": "gpt-4o",
  "label": "GPT-4o",
  "group": "chat",
  "provider": "openai",
  "adapter": "openai",
  "tokenizer_ref": "o200k_base",
  "status": "stable",
  "description": "...",
  "context_window": 128000,
  "notes": null,
  "supports_token_decode": true,
  "supports_browser": true,
  "deprecated": false
}
```

Adding a new model requires only a new JSON entry — no code changes.

---

## Design Decisions

### Adapter pattern for tokenizers

The `BaseTokenizerAdapter` ABC decouples the service layer from any specific tokenizer library. Today the only implementation is `OpenAITokenizerAdapter` (tiktoken). Adding a Hugging Face tokenizer means implementing the four abstract methods and registering it in `tokenizer_service.py` — nothing else changes.

### Data-driven model catalog

Models and pricing are defined in JSON, not in code. This means adding a new model, updating a context window, or deprecating an alias requires only a data file edit with no re-deploy for the logic layer (a restart is sufficient).

### Singletons via `@lru_cache`

`get_settings()`, `get_model_registry()`, `get_pricing_service()`, and `get_openai_adapter()` all use `@lru_cache`. This ensures expensive operations (disk I/O, tiktoken instantiation) happen once at startup and are shared across all requests.

### Inline errors in compare

`POST /api/v1/compare` never returns a `4xx` for an individual unsupported model. Instead it returns an `error` string in that model's result object. This lets clients compare a mix of valid and invalid model IDs in a single call and handle partial failures gracefully.

### Pydantic BaseSettings for configuration

Rather than a YAML application config file, runtime settings come from environment variables (with `.env` fallback). This is the [Twelve-Factor App](https://12factor.net/config) approach and makes the service trivially configurable in Docker or any CI/CD system.

---

## Logging

Logging is configured from `src/config/logging.yaml` via Python's `logging.config.dictConfig`. The setup runs at process startup before the FastAPI app is created.

### Handlers

| Handler | File | Captures |
|---------|------|---------|
| `debug_file` | `logs/prompttokenizer_debug.log` | `DEBUG` only |
| `info_file` | `logs/prompttokenizer_info.log` | `INFO` only |
| `warning_file` | `logs/prompttokenizer_warning.log` | `WARNING` only |
| `error_file` | `logs/prompttokenizer_error.log` | `ERROR` and above |
| `console` | stdout | All levels |

Each rotating file handler caps at **10 MB** with **5 backups**.

The `ExactLevelFilter` class (in `src/core/logger.py`) ensures each file contains only its designated level — `DEBUG` messages do not appear in the `INFO` log, and so on.

### Noisy third-party loggers

`httpx`, `mcp.client.sse`, and `primp` are pinned to `WARNING` in the YAML config to prevent their verbose output from flooding application logs.

### Adding structured logging

To use the logger in any module:

```python
import logging
logger = logging.getLogger(__name__)

logger.info("Tokenizing %d chars with %s", len(text), model)
logger.warning("Deprecated model requested: %s", model_id)
```

---

## Testing

Tests use `pytest` with `pytest-asyncio` and an `httpx.AsyncClient` pointed at the FastAPI app.

```bash
# Run all tests
uv run pytest tests/ -v

# Run a specific file
uv run pytest tests/test_tokenize.py -v

# Run with coverage
uv run pytest tests/ --cov=src --cov-report=term-missing
```

### Test fixtures (`tests/conftest.py`)

A session-scoped `AsyncClient` wraps the app so the FastAPI lifespan runs once for the entire test session:

```python
@pytest.fixture(scope="session")
async def client():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac
```

### Coverage areas

| Test file | What it covers |
|-----------|---------------|
| `test_health.py` | Liveness endpoint shape |
| `test_models.py` | List/filter/lookup, alias resolution, 404 handling |
| `test_tokenize.py` | Token counts, token strings, token IDs, validation errors |
| `test_compare.py` | Multi-model comparison, partial errors, count limits |

---

## Extending the Project

### Adding a new model or encoding

Edit `src/data/models.json` and add a new entry. No code changes required. If the new model uses an existing tiktoken encoding (e.g. `cl100k_base`), it will work immediately.

### Adding a new tokenizer backend (e.g. Hugging Face)

1. Create `src/adapters/huggingface_adapter.py`:

```python
from src.adapters.base import BaseTokenizerAdapter

class HuggingFaceTokenizerAdapter(BaseTokenizerAdapter):
    def encode(self, text: str, model: str) -> list[int]: ...
    def decode_tokens(self, token_ids: list[int], model: str) -> list[str]: ...
    def count_tokens(self, text: str, model: str) -> int: ...
    def supports_model(self, model: str) -> bool: ...
```

2. Register it in `src/services/tokenizer_service.py` alongside the existing OpenAI adapter.

3. Set `"adapter": "huggingface"` in the relevant `models.json` entries.

### Adding a new API endpoint

1. Add a Pydantic schema in `src/schemas/`.
2. Add business logic in `src/services/`.
3. Create a router in `src/routers/` and register it in `src/main.py`.

### Changing the API prefix

Set `API_PREFIX=/api/v2` in `.env`. All versioned routes update automatically.
