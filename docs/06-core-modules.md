# 06 · Core Modules & Components

This chapter is the API-level reference for the **internal** code: every module, the public functions/classes it exports, and how they fit together. Endpoints (the *external* API) are in [API Reference](07-api-reference.md).

---

## `src/main.py` — application factory

Exports the ASGI `app` object that servers import as `src.main:app`.

- `lifespan(app)` — async context manager. On startup: caches settings, logs the banner, calls `preload_encodings()`, logs elapsed startup ms. On shutdown: logs a message.
- `create_app() -> FastAPI` — builds the app: sets `title/version/description` from settings, **gates docs URLs on `app_env == "dev"`**, attaches the lifespan, wires CORS + exception handlers, and includes all five routers (health unprefixed, the rest under `api_prefix`).
- `app = create_app()` — module-level instance.

See [Architecture](02-architecture.md) for the annotated source.

---

## `src/core/config.py` — configuration

```python
class Settings(BaseSettings):
    app_name: str = "prompt-tokenizer"
    app_env: str = "dev"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    allowed_origins: list[str] = ["http://localhost:3000", "http://localhost:5173"]
    log_level: str = "INFO"
    api_prefix: str = "/api/v1"
    app_version: str = "0.1.0"
    workers: int = 4
    timeout: int = 120
    graceful_timeout: int = 30
```

- **`get_settings()`** is wrapped in `@lru_cache`, so the `.env` file and environment are read **once per process**. Every caller shares the same `Settings` instance.
- **`_FlexDotEnvSource`** subclasses `DotEnvSettingsSource` and overrides `decode_complex_value`. Pydantic normally expects JSON for complex fields like `list[str]`; this override lets you write a plain **comma-separated string** in `.env` (e.g. `ALLOWED_ORIGINS=http://a.com,http://b.com`) and it is split on commas into a list. If JSON parsing succeeds first, that wins.
- **`settings_customise_sources`** inserts `_FlexDotEnvSource` into the precedence chain. Final precedence (highest first): **init kwargs → environment variables → `.env` file → secrets**.

See [Configuration](09-configuration.md) for the full variable table.

---

## `src/core/cors.py`

```python
def setup_cors(app: FastAPI) -> None:
    settings = get_settings()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
```

Origins come from config; methods and headers are fully open; credentials are allowed. See [Security](10-security-and-auth.md) for the implications of `allow_credentials=True` with a fixed origin list.

---

## `src/core/exceptions.py`

Defines the domain exception hierarchy and the global handler registration.

| Exception | Constructor arg | Mapped HTTP | Error code |
|-----------|-----------------|-------------|-----------|
| `ModelNotSupportedError` | `model_id` | **404** | `MODEL_NOT_SUPPORTED` |
| `TokenizerNotAvailableError` | `tokenizer_name` | **503** | `TOKENIZER_NOT_AVAILABLE` |
| `InvalidCompareRequestError` | `message` | **400** | `INVALID_COMPARE_REQUEST` |
| `RequestValidationError` (FastAPI built-in) | — | **422** | `VALIDATION_ERROR` |
| `Exception` (catch-all) | — | **500** | `INTERNAL_ERROR` |

All handlers funnel through one envelope builder:

```python
def _error_response(code, message, details=None, status_code=400) -> JSONResponse:
    return JSONResponse(status_code=status_code,
        content={"error": {"code": code, "message": message, "details": details}})
```

So **every** error in the system has the same shape: `{"error": {"code", "message", "details"}}`. The catch-all handler deliberately returns a generic `"An internal error occurred"` message (never leaking internals). See [Error Handling & Logging](11-error-handling-and-logging.md).

> `InvalidCompareRequestError` is defined and wired but **not currently raised** anywhere — compare validation is handled by Pydantic (`min_length=1, max_length=10`) and per-model failures are caught inline. It exists for future use.

---

## `src/core/logger.py`

- **`ExactLevelFilter(level)`** — a `logging.Filter` whose `filter()` returns `True` only when `record.levelno == self.level`. This is what makes each per-level log file contain *only* that level.
- **`configure_logging()`** — ensures `logs/` exists, then loads `src/config/logging.yaml` via `logging.config.dictConfig`. If the YAML is missing, falls back to `basicConfig` and warns.
- **`get_logger(name)`** — thin wrapper over `logging.getLogger(name)`.

Called at **import time** in both `run.py` and `src/main.py` so logging is live before anything else runs.

---

## `src/adapters/base.py` — the tokenizer contract

```python
class BaseTokenizerAdapter(ABC):
    adapter_name: str = "base"

    @abstractmethod
    def encode(self, text: str) -> list[int]: ...
    @abstractmethod
    def decode_tokens(self, token_ids: list[int]) -> list[str]: ...
    @abstractmethod
    def count_tokens(self, text: str) -> int: ...
    @abstractmethod
    def supports_model(self, model_id: str) -> bool: ...
```

Any tokenizer backend must subclass this and implement the four methods. The `adapter_name` string is the value matched against a `ModelEntry.adapter` field in `tokenizer_service`.

> The concrete OpenAI adapter implements these four *plus* richer ref-aware variants (below). The base `encode`/`decode_tokens`/`count_tokens` are implemented to raise `NotImplementedError`, because the real call sites always use the ref-aware methods. This is a known wrinkle of the abstraction — see [Design Patterns & Extending](17-design-patterns-and-extending.md).

---

## `src/services/openai_tokenizer_adapter.py` — tiktoken backend

### Module-level state

```python
_ENCODING_NAMES = tuple(load_config("src/config/config.yaml")["tokenizer"]["encoding_names"])
ENCODINGS: dict[str, tiktoken.Encoding] = {}   # name → loaded encoding
```

### `preload_encodings()`

Idempotent. Loads any encoding from `_ENCODING_NAMES` not already in `ENCODINGS` via `tiktoken.get_encoding(name)`. Called from the app lifespan and lazily from `get_openai_adapter()`. Logs how many were loaded.

### `class OpenAITokenizerAdapter(BaseTokenizerAdapter)` — `adapter_name = "openai_tiktoken"`

| Method | Behavior |
|--------|----------|
| `_get_encoding_by_name(name)` | Returns `ENCODINGS[name]`; raises `TokenizerNotAvailableError` if absent. |
| `get_encoding_for_model(model, ref)` | Tries tiktoken's `encoding_name_for_model(model)`; if found & preloaded, uses it; else falls back to `ref`. |
| `encode_with_tokenizer(name, text)` | Encode using a named encoding directly (raw-encoding path). |
| `encode_for_model_with_ref(model, ref, text)` | Encode via model→encoding resolution (alias path). |
| `decode_tokens_with_tokenizer(name, ids)` | Decodes each id individually; un-decodable/special tokens become `"<{id}>"`. |
| `count_with_tokenizer` / `count_for_model_with_ref` | `len()` of the respective encode. |
| `supports_model(id)` | `True` iff tiktoken's model map recognizes the id. |
| `encode` / `decode_tokens` / `count_tokens` | Raise `NotImplementedError` (use ref-aware variants). |

### `get_openai_adapter()`

Module-level singleton (`_adapter_instance`). On first call it ensures encodings are preloaded, then constructs and caches the adapter.

> **Per-token decode detail:** `decode_tokens_with_tokenizer` calls `decode_single_token_bytes(tid)` per id and `.decode("utf-8", errors="replace")`. This means a multi-byte UTF-8 character that spans several tokens may render as replacement characters (``) on the individual token strings — `token_count` and `token_ids` are always exact, but the human-readable `tokens` array is a best-effort per-token view.

---

## `src/services/model_registry.py`

```python
class ModelRegistry:
    def __init__(self, data_file=DATA_FILE):
        raw = json.loads(data_file.read_text("utf-8"))
        self._entries = {e["id"]: ModelEntry(**e) for e in raw}   # id → ModelEntry
```

| Method | Behavior |
|--------|----------|
| `get_all(group, provider, search)` | Returns all entries, optionally filtered. `group`/`provider` are **case-insensitive exact** matches; `search` is a case-insensitive substring over `id`, `label`, and `description`. Filters compose (AND). |
| `get_by_id(model_id)` | Dict lookup; raises `ModelNotSupportedError` if missing. |
| `resolve_tokenizer_ref(model_id)` | Convenience: `get_by_id(id).tokenizer_ref`. |

`get_model_registry()` is `@lru_cache` — the JSON is parsed and validated **once**.

---

## `src/services/pricing_service.py`

```python
class PricingService:
    def __init__(self, data_file=DATA_FILE):
        raw = json.loads(data_file.read_text("utf-8"))
        self._entries = [PricingEntry(**i) for i in raw]
        self._by_model = {e.model_id: e for e in self._entries}   # model_id → PricingEntry
```

| Method | Behavior |
|--------|----------|
| `get_all()` | Copy of all pricing entries (list). |
| `get_by_model(model_id)` | `PricingEntry` or `None`. |

`get_pricing_service()` is `@lru_cache`.

---

## `src/services/tokenizer_service.py`

The orchestrator. One function — `tokenize(model_or_encoding, text, include_tokens=True, include_token_ids=True) -> TokenizeResponse`. It is fully traced in [System Design & Data Flow](03-system-design-and-data-flow.md). In short: resolve via registry → dispatch on `entry.adapter` → encode (alias vs raw path on `entry.status`) → optional decode → pricing lookup → assemble `TokenizeResponse`.

---

## `src/utils/`

### `config_loader.py`

`load_config(path) -> dict` — generic loader that validates the path exists and is a file, dispatches on suffix (`.yaml`/`.yml` → `yaml.safe_load`, `.json` → `json.load`), and asserts the result is a mapping. Used to read `config.yaml` for the encoding list. Raises `FileNotFoundError` / `ValueError` on bad input.

### `text.py`

`truncate_text(text, max_length) -> str` — returns `text` unchanged if within `max_length`, else slices to `max_length`. A standalone helper; **not currently called** by the request path (length limits are enforced by Pydantic `Field(max_length=...)`).

Continue to [API Reference & Contracts →](07-api-reference.md)
