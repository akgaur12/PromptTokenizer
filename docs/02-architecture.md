# 02 · High-Level Architecture

PromptTokenizer follows a strict, **four-layer horizontal architecture**. Each layer depends only on the layer beneath it, which keeps HTTP concerns, business logic, tokenizer backends, and data cleanly separated.

## The four layers

| Layer | Package | Responsibility | Knows about |
|-------|---------|----------------|-------------|
| **Routers** | `src/routers/` | HTTP request/response, status codes, Pydantic validation | Schemas, Services |
| **Services** | `src/services/` | Business logic: model resolution, tokenization orchestration, pricing lookup | Adapters, Data, Schemas |
| **Adapters** | `src/adapters/` + `src/services/openai_tokenizer_adapter.py` | Tokenizer backend abstraction (`tiktoken` today) | `tiktoken`, config |
| **Data** | `src/data/` | Static JSON catalogs (`models.json`, `pricing.json`) | Nothing |

Supporting these is a **core / cross-cutting** package (`src/core/`) for configuration, CORS, logging, and exception handling, plus `src/schemas/` (Pydantic contracts) and `src/utils/` (helpers).

## Component map

```
                          HTTP client (browser / backend / curl)
                                        │
                                        ▼
┌───────────────────────────────────────────────────────────────────────┐
│ FastAPI application  (src/main.py :: create_app)                        │
│   • CORS middleware            (src/core/cors.py)                       │
│   • Exception handlers         (src/core/exceptions.py)                 │
│   • Lifespan: preload encodings(src/main.py :: lifespan)               │
│                                                                         │
│  ROUTERS (src/routers/)                                                 │
│   health.py   models.py   tokenize.py   compare.py   pricing.py         │
│      │            │            │             │            │             │
│      │            │            ▼             ▼            │             │
│      │            │     ┌──────────────────────────┐     │             │
│      │            │     │  tokenizer_service.py     │     │             │
│      │            │     │  (orchestrator)           │     │             │
│      │            │     └───────┬───────────┬──────┘     │             │
│      ▼            ▼             ▼           ▼             ▼             │
│  SERVICES (src/services/)                                               │
│   model_registry.py   openai_tokenizer_adapter.py   pricing_service.py  │
│        │                       │                          │             │
│        ▼                       ▼                          ▼             │
│   DATA (src/data/)        tiktoken (PyPI)            DATA (src/data/)    │
│   models.json             encodings cache           pricing.json        │
└───────────────────────────────────────────────────────────────────────┘
```

> **Note on packaging:** the `BaseTokenizerAdapter` abstract base class lives in `src/adapters/base.py`, but the concrete `OpenAITokenizerAdapter` lives in `src/services/openai_tokenizer_adapter.py`. The "adapter layer" is therefore split across two packages by file location, but conceptually it is one layer. See [Core Modules](06-core-modules.md).

## Application bootstrap & lifespan

The app is built by an **application factory** (`create_app()` in `src/main.py`) and exported as the module-level `app`, which is what Gunicorn/Uvicorn import (`src.main:app`).

```python
# src/main.py (abridged)
configure_logging()                  # 1. logging from YAML, at import time
logger = get_logger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()        # 2a. read & cache settings
    preload_encodings()              # 2b. load all tiktoken encodings into memory
    yield                            #     -- app serves requests --
    logger.info("Shutting down ...")

def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        docs_url="/docs" if settings.app_env == "dev" else None,   # 3. gate docs
        redoc_url="/redoc" if settings.app_env == "dev" else None,
        openapi_url="/openapi.json" if settings.app_env == "dev" else None,
        lifespan=lifespan,
    )
    setup_cors(app)                  # 4. CORS middleware
    register_exception_handlers(app) # 5. domain-exception → HTTP mapping
    app.include_router(health.router)                       # /health (no prefix)
    app.include_router(models.router,   prefix=settings.api_prefix)
    app.include_router(tokenize.router, prefix=settings.api_prefix)
    app.include_router(compare.router,  prefix=settings.api_prefix)
    app.include_router(pricing.router,  prefix=settings.api_prefix)
    return app

app = create_app()
```

Startup order matters:

1. **Logging is configured at import time** (top of `main.py` *and* `run.py`) so even bootstrap messages are captured.
2. The **lifespan** runs once when the ASGI server starts: it logs the app banner and **preloads every tiktoken encoding** so the first real request is not penalized by lazy loading. Startup time is measured and logged in milliseconds.
3. **Interactive docs are gated**: `/docs`, `/redoc`, and `/openapi.json` are only mounted when `APP_ENV == "dev"`. In any other environment they are `None` (disabled). This was an intentional change (commit `f468717`).
4. The `/health` route is registered with **no prefix**; all other routers are mounted under `settings.api_prefix` (default `/api/v1`).

## Request lifecycle (generic)

```
1. Client sends HTTP request
2. CORS middleware evaluates Origin (adds CORS headers / handles preflight)
3. FastAPI routes to the matching path operation
4. Pydantic validates the request body / query params
       └─ on failure → RequestValidationError → 422 error envelope
5. Router calls into the service layer
6. Service resolves model, calls adapter / pricing, assembles a Pydantic response
       └─ domain error (e.g. ModelNotSupportedError) → mapped to HTTP via handler
7. FastAPI serializes the Pydantic response model → JSON
8. CORS headers attached → response returned
```

## Architectural principles

- **Data-driven over code-driven.** Adding a model = editing JSON. The logic layer is generic; the catalog is data. See [Data Model & Catalog](08-data-model-and-catalog.md).
- **Singletons for expensive objects.** Settings, registries, the pricing service, the adapter instance, and tiktoken encodings are all created once and reused (via `@lru_cache` or module-level caches). See [Performance](16-performance.md).
- **Pluggable backends.** The tokenizer is hidden behind an ABC so a new backend (HuggingFace, SentencePiece, …) is additive, not invasive.
- **Stateless & horizontally scalable.** No shared mutable state, no database — run N Gunicorn workers or N containers freely.
- **Fail soft where it helps callers.** `/compare` returns per-model inline errors instead of failing the whole batch.

Continue to [System Design & Data Flow →](03-system-design-and-data-flow.md)
