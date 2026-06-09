# 11 · Error Handling & Logging

## Error-handling model

The service uses **typed domain exceptions** raised deep in the service/adapter layers and translated to HTTP at the edge by **global FastAPI exception handlers** (registered in `register_exception_handlers(app)` during `create_app()`). Routers stay clean — they don't write status codes for errors; they just let exceptions propagate.

### The unified error envelope

Every error response has exactly this shape (built by `_error_response()`):

```json
{ "error": { "code": "<MACHINE_CODE>", "message": "<human readable>", "details": <any|null> } }
```

This mirrors the `ErrorResponse`/`ErrorDetail` schemas in `src/schemas/common.py`, giving clients one stable contract for all failures.

### Exception → HTTP map

| Exception (source) | Raised when | HTTP | `code` | `details` |
|--------------------|-------------|------|--------|-----------|
| `ModelNotSupportedError` (`model_registry`, `tokenizer_service`) | model id not in catalog, or adapter unimplemented | **404** | `MODEL_NOT_SUPPORTED` | `null` |
| `TokenizerNotAvailableError` (`openai_tokenizer_adapter`) | resolved encoding not preloaded | **503** | `TOKENIZER_NOT_AVAILABLE` | `null` |
| `InvalidCompareRequestError` (defined, unused) | reserved | **400** | `INVALID_COMPARE_REQUEST` | `null` |
| `RequestValidationError` (FastAPI) | body/query fails validation | **422** | `VALIDATION_ERROR` | Pydantic field errors |
| `Exception` (catch-all) | anything unhandled | **500** | `INTERNAL_ERROR` | `null` (generic msg) |

### Where each error originates

```
ModelNotSupportedError
   ├─ ModelRegistry.get_by_id()        → unknown model id        (tokenize, compare, GET /models/{id})
   └─ tokenizer_service.tokenize()      → entry.adapter not "openai_tiktoken"

TokenizerNotAvailableError
   └─ OpenAITokenizerAdapter._get_encoding_by_name() → encoding not in ENCODINGS

RequestValidationError
   └─ Pydantic on TokenizeRequest / CompareRequest (length, count, type)
```

### The compare exception: soft failures

`/compare` is the one place that **swallows** exceptions instead of letting them reach a handler. Each per-model `tokenize()` call is wrapped in `try/except Exception`, and a failure becomes an inline `error` string with `resolved_tokenizer:"unknown"`, `token_count:0` — the overall response stays `200`. This is intentional (partial-batch tolerance). See [API Reference](07-api-reference.md#post-apiv1compare).

### Validation errors (422)

FastAPI's `RequestValidationError` is re-handled to fit the common envelope, with the raw Pydantic errors preserved under `details`:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Request validation failed",
    "details": [ { "type": "string_too_short", "loc": ["body","text"], "msg": "..." } ]
  }
}
```

---

## Logging

Logging is configured from **`src/config/logging.yaml`** via `logging.config.dictConfig`, bootstrapped by `configure_logging()` in `src/core/logger.py`. It runs at **import time** (top of both `run.py` and `src/main.py`) so logs are live before the app is built.

### The "one file per level" design

The standout feature is **exact-level file separation**. A custom `ExactLevelFilter` admits a record only if `record.levelno == level`:

```python
class ExactLevelFilter(logging.Filter):
    def __init__(self, level): self.level = level
    def filter(self, record): return record.levelno == self.level
```

Combined with the YAML handlers, this yields:

| Handler | File | Captures | Filter |
|---------|------|----------|--------|
| `debug_file` | `logs/prompttokenizer_debug.log` | **only** DEBUG | `exact_debug` (10) |
| `info_file` | `logs/prompttokenizer_info.log` | **only** INFO | `exact_info` (20) |
| `warning_file` | `logs/prompttokenizer_warning.log` | **only** WARNING | `exact_warning` (30) |
| `error_file` | `logs/prompttokenizer_error.log` | ERROR **and above** | (none — level threshold) |
| `console` | stdout | everything (DEBUG+) | (none) |

So DEBUG messages never pollute the INFO file, INFO never appears in WARNING, etc. — each file is a clean stream of exactly one level (except `error_file`, which uses a normal level threshold so it captures ERROR and CRITICAL together).

### Rotation

Each file handler is a `RotatingFileHandler`:

- `maxBytes: 10485760` (**10 MB**) per file
- `backupCount: 5` (keeps 5 rotated copies)
- `encoding: utf-8`

The `logs/` directory is created by `configure_logging()` (`os.makedirs("logs", exist_ok=True)`) and also by the Docker image at build time.

### Formatters

| Formatter | Used by | Format |
|-----------|---------|--------|
| `file` | all file handlers | `ts,ms - LEVEL - name - message` |
| `console` | console | `ts - LEVEL - name - message` |
| `standard` | (defined, includes `lineno`) | `ts,ms - LEVEL - name,lineno - message` |

### Root logger & levels

```yaml
root:
  level: INFO
  handlers: [debug_file, info_file, warning_file, error_file, console]
```

> **Important nuance:** the root level is `INFO`, so **DEBUG records are filtered out before reaching any handler** by default — the `debug_file` will stay empty unless the root (or a specific logger) level is lowered to `DEBUG`. The `LOG_LEVEL` env var does **not** change this; it only affects the dev uvicorn `--log-level`. To capture DEBUG to file, set `root.level: DEBUG` in `logging.yaml`.

### Noisy third-party loggers

Selected chatty libraries are pinned to `WARNING` via a YAML anchor (`&noisy`):

```yaml
loggers:
  httpx: *noisy
  mcp.client.sse: *noisy
  primp: *noisy
  langchain_aws.chat_models.bedrock_converse: *noisy
```

(`gunicorn`/`uvicorn` overrides are present but commented out.) Note some of these libraries (mcp, langchain_aws) aren't dependencies of this service — the YAML is a reusable template carried across projects; the pins are harmless if the logger never emits.

### What gets logged by the app itself

The application logs sparingly and meaningfully:

- **Startup:** `"Starting <name> v<version>"`, the encoding preload progress, and `"Application started in X.Xms"`.
- **Shutdown:** `"Shutting down <name>"`.
- **run.py:** `"Starting in development/production mode"`.

There is currently **no per-request access logging** in application code (uvicorn/gunicorn provide their own access logs). Unhandled exceptions reach the catch-all handler; to also persist their tracebacks, add a `logger.exception(...)` call there (see [Troubleshooting](15-troubleshooting.md)).

### Using the logger in new code

```python
from src.core.logger import get_logger
logger = get_logger(__name__)

logger.info("Tokenized %d chars with %s", len(text), model)
logger.warning("Deprecated model requested: %s", model_id)
logger.exception("Unexpected failure")   # logs message + traceback at ERROR
```

Use `%`-style lazy formatting (as the codebase does) rather than f-strings, so the string is only built if the level is enabled.

Continue to [Build, Deployment & CI/CD →](12-build-and-deployment.md)
