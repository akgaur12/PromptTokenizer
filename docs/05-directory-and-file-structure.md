# 05 · Directory & File Structure

A guided tour of every meaningful file in the repository. Generated artifacts and caches (`.venv/`, `__pycache__/`, `.pytest_cache/`, `.ruff_cache/`, `logs/`) are omitted.

```
PromptTokenizer/
├── run.py                     # CLI entry point — dev/prod launcher
├── pyproject.toml             # Project metadata, deps, scripts, Ruff config
├── uv.lock                    # Fully-resolved dependency lock (authoritative)
├── requirements.txt           # pip convenience list (drifted — see ch.04)
├── .python-version            # "3.13"
├── .env                       # Local environment overrides (gitignored)
├── .env.example               # Template / documented defaults
├── Dockerfile                 # Multi-stage container build
├── .dockerignore              # Build-context excludes
├── .gitignore                 # VCS excludes
├── README.md                  # Legacy top-level readme (partly stale — see note)
├── CLAUDE.md                  # Guidance for Claude Code (partly stale — see note)
│
├── docs/                      # ← this documentation book
│
├── src/                       # Application package
│   ├── __init__.py
│   ├── main.py                # FastAPI app factory + lifespan (export: app)
│   │
│   ├── core/                  # Cross-cutting infrastructure
│   │   ├── __init__.py
│   │   ├── config.py          # Settings (pydantic-settings) + custom dotenv source
│   │   ├── cors.py            # CORS middleware setup
│   │   ├── exceptions.py      # Domain exceptions + global HTTP handlers
│   │   └── logger.py          # YAML logging bootstrap + ExactLevelFilter
│   │
│   ├── adapters/              # Tokenizer backend abstraction
│   │   ├── __init__.py
│   │   └── base.py            # BaseTokenizerAdapter (ABC)
│   │
│   ├── routers/              # HTTP route handlers (one file per resource)
│   │   ├── __init__.py
│   │   ├── health.py          # GET /health
│   │   ├── models.py          # GET /models, GET /models/{id}
│   │   ├── tokenize.py        # POST /tokenize
│   │   ├── compare.py         # POST /compare
│   │   └── pricing.py         # GET /pricing
│   │
│   ├── schemas/               # Pydantic request/response contracts
│   │   ├── __init__.py
│   │   ├── common.py          # ErrorDetail, ErrorResponse
│   │   ├── tokenize.py        # TokenizeRequest, TokenizeResponse
│   │   ├── compare.py         # CompareRequest, CompareResult, CompareResponse
│   │   ├── models.py          # ModelEntry, ModelsListResponse
│   │   └── pricing.py         # PricingEntry, PricingListResponse
│   │
│   ├── services/              # Business logic
│   │   ├── __init__.py
│   │   ├── model_registry.py        # Loads models.json; lookups & filters
│   │   ├── tokenizer_service.py     # Orchestrates tokenize() — the brain
│   │   ├── openai_tokenizer_adapter.py  # tiktoken implementation + preload
│   │   └── pricing_service.py       # Loads pricing.json; lookups
│   │
│   ├── utils/                 # Small helpers
│   │   ├── __init__.py
│   │   ├── config_loader.py   # Generic YAML/JSON → dict loader
│   │   └── text.py            # truncate_text() helper
│   │
│   ├── config/                # Static, non-secret config files
│   │   ├── config.yaml        # Tokenizer encoding-names preload list
│   │   └── logging.yaml       # dictConfig: handlers, filters, formatters
│   │
│   └── data/                  # Static JSON catalogs (the "database")
│       ├── models.json        # 34 model/encoding entries
│       └── pricing.json       # 29 pricing entries
│
├── tests/                     # pytest suite
│   ├── __init__.py
│   ├── conftest.py            # Shared TestClient fixture (session-scoped)
│   ├── test_health.py
│   ├── test_models.py
│   ├── test_tokenize.py
│   └── test_compare.py
│
└── notebooks/                 # Exploratory Jupyter notebooks + Postman data
    ├── tiktoken.ipynb
    ├── transformers_tk.ipynb
    ├── test.json
    └── postman/
        ├── tokenize_bulk_data.csv
        ├── tokenize_bulk_data_500.csv
        └── tokenize_bulk_data.json
```

## File-by-file reference

### Root

| File | Purpose |
|------|---------|
| `run.py` | The launcher. `python run.py` → prod (Gunicorn); `python run.py dev` → dev (Uvicorn `--reload`). Also exposed as the `start` console script. |
| `pyproject.toml` | Single source for metadata, dependencies, the `start` script entry point, and all Ruff config. |
| `uv.lock` | Pinned, hashed dependency graph for reproducible installs. |
| `requirements.txt` | Manual pip list — **drifted**, prefer `uv sync`. |
| `Dockerfile` | Two-stage build (uv builder → slim runtime, non-root). |
| `.env` / `.env.example` | Runtime config. `.env` is gitignored; `.env.example` documents the variables. |
| `README.md` | Original readme. **Partly stale**: shows `include_tokens` default `false` (code: `true`), compare error fields as `null` (code: `"unknown"`/`0`), and an older model count. Trust this `docs/` book over it. |
| `CLAUDE.md` | Instructions for the Claude Code agent. **Partly stale**: references a DeepSeek adapter and `deepseek-tokenizer` package that **do not exist** in the code, and model/pricing counts that no longer match. |

### `src/core/` — infrastructure

| File | Key contents |
|------|-------------|
| `config.py` | `Settings` (BaseSettings), `_FlexDotEnvSource` (comma-separated list parsing), `get_settings()` (`@lru_cache`). |
| `cors.py` | `setup_cors(app)` — adds `CORSMiddleware` from `allowed_origins`. |
| `exceptions.py` | `ModelNotSupportedError`, `TokenizerNotAvailableError`, `InvalidCompareRequestError`, the `_error_response()` envelope builder, and `register_exception_handlers(app)`. |
| `logger.py` | `ExactLevelFilter`, `configure_logging()` (loads `logging.yaml`), `get_logger()`. |

### `src/services/` — business logic

| File | Key contents |
|------|-------------|
| `model_registry.py` | `ModelRegistry` (loads `models.json`), `get_all/get_by_id/resolve_tokenizer_ref`, `get_model_registry()` singleton. |
| `tokenizer_service.py` | `tokenize()` — the orchestration function tying registry + adapter + pricing together. |
| `openai_tokenizer_adapter.py` | `OpenAITokenizerAdapter`, the `ENCODINGS` cache, `preload_encodings()`, `get_openai_adapter()`. |
| `pricing_service.py` | `PricingService` (loads `pricing.json`), `get_all/get_by_model`, `get_pricing_service()` singleton. |

### `src/config/` & `src/data/`

| File | Purpose |
|------|---------|
| `config/config.yaml` | Lists the six tiktoken encodings to preload (`cl100k_base`, `gpt2`, `o200k_base`, `p50k_base`, `p50k_edit`, `r50k_base`). |
| `config/logging.yaml` | Full `dictConfig`: 4 per-level rotating file handlers + console, exact-level filters, noisy-logger pins. |
| `data/models.json` | Model & encoding catalog (see [Data Model](08-data-model-and-catalog.md)). |
| `data/pricing.json` | Pricing catalog. |

### `notebooks/` — not part of the service

Exploratory notebooks (`tiktoken.ipynb`, `transformers_tk.ipynb`) and Postman/bulk test data. These are **excluded** from both the Docker image (`.dockerignore`) and git (`.gitignore`) and are for local experimentation only.

Continue to [Core Modules & Components →](06-core-modules.md)
