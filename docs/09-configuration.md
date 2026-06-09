# 09 · Configuration & Environment Variables

All runtime configuration is **environment-driven** (the [Twelve-Factor](https://12factor.net/config) approach). There is no YAML *application* config — the only YAML files are for logging (`logging.yaml`) and the tokenizer preload list (`config.yaml`), neither of which holds runtime settings.

Configuration is defined once in `src/core/config.py` as a `pydantic-settings` `Settings` class and accessed everywhere via the cached `get_settings()`.

---

## Environment variables

| Variable | Type | Default (code) | `.env.example` | Used by |
|----------|------|----------------|----------------|---------|
| `APP_NAME` | str | `prompt-tokenizer` | `prompt-tokenizer` | `/health`, OpenAPI title, logs |
| `APP_ENV` | str | `dev` | `development` | **Docs gating** (`/docs`,`/redoc`,`/openapi.json` only when `== "dev"`) |
| `APP_HOST` | str | `0.0.0.0` | `0.0.0.0` | bind address (`run.py`) |
| `APP_PORT` | int | `8000` | `8000` | bind port (`run.py`) |
| `APP_VERSION` | str | `0.1.0` | `0.1.0` | `/health`, OpenAPI version |
| `ALLOWED_ORIGINS` | list[str] | `["http://localhost:3000","http://localhost:5173"]` | `http://localhost:3000,http://localhost:5173` | CORS allow-list |
| `LOG_LEVEL` | str | `INFO` | `INFO` | dev uvicorn `--log-level` |
| `API_PREFIX` | str | `/api/v1` | `/api/v1` | router mount prefix |
| `WORKERS` | int | `4` | `4` | Gunicorn worker count (prod) |
| `TIMEOUT` | int | `120` | `120` | Gunicorn worker timeout (s) |
| `GRACEFUL_TIMEOUT` | int | `30` | `30` | Gunicorn graceful shutdown (s) |

Variable names are **case-insensitive** (`case_sensitive=False`), so `APP_PORT` and `app_port` both work.

---

## ⚠️ The `APP_ENV` docs-gating gotcha

The app enables interactive docs **only** when `app_env == "dev"` (exact string):

```python
docs_url="/docs" if settings.app_env == "dev" else None
```

- **No `.env` file present** → default is `app_env = "dev"` → docs **enabled**.
- **Using `.env.example` as-is** → it sets `APP_ENV=development` → `"development" != "dev"` → docs **disabled**.
- The committed local `.env` uses `APP_ENV=dev` → docs **enabled**.

So if `/docs` returns 404 when you expected it, check that `APP_ENV` is exactly `dev`, not `development`. See [Troubleshooting](15-troubleshooting.md).

---

## Configuration precedence

`Settings.settings_customise_sources` defines the order (highest priority first):

```
1. init kwargs            (Settings(app_port=9000))      — rarely used
2. environment variables  (export APP_PORT=9000)
3. .env file              (via _FlexDotEnvSource)
4. file secrets           (unused)
```

So an exported env var overrides `.env`, which overrides the code defaults.

### Custom list parsing (`_FlexDotEnvSource`)

Pydantic normally requires JSON for a `list[str]` field. This project subclasses the dotenv source so you can write a **plain comma-separated** value:

```dotenv
# Both of these work for ALLOWED_ORIGINS:
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173        # comma form (custom)
ALLOWED_ORIGINS=["http://localhost:3000","http://localhost:5173"]  # JSON form (standard)
```

The override tries JSON first; on failure it splits on commas, trims whitespace, and drops empties.

---

## Example `.env`

`.env.example` (the documented template):

```dotenv
APP_NAME=prompt-tokenizer
APP_ENV=development
APP_HOST=0.0.0.0
APP_PORT=8000
APP_VERSION=0.1.0
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173
LOG_LEVEL=INFO
API_PREFIX=/api/v1
WORKERS=4
TIMEOUT=120
GRACEFUL_TIMEOUT=30
```

The committed local `.env` differs in a few values (illustrating real deployment use):

```dotenv
APP_ENV=dev               # docs enabled
APP_PORT=8192             # non-default port
WORKERS=2                 # fewer workers
ALLOWED_ORIGINS=...,https://prompt-tokenizer.site,https://www.prompt-tokenizer.site,<vercel-preview>
```

> `.env` is **gitignored**; `.env.example` is committed. Never put secrets in either — this service has none, but the convention matters if you add any.

---

## Where settings are consumed

| Setting | Consumer | Effect |
|---------|----------|--------|
| `app_name`,`app_version` | `main.create_app`, `routers/health` | OpenAPI metadata, health payload |
| `app_env` | `main.create_app` | docs/redoc/openapi gating |
| `app_host`,`app_port` | `run.py` | server bind |
| `allowed_origins` | `core/cors` | CORS middleware |
| `log_level` | `run.py` (dev) | uvicorn log level (note: file logging is governed by `logging.yaml`, not this) |
| `api_prefix` | `main.create_app` | router prefixes |
| `workers`,`timeout`,`graceful_timeout` | `run.py` (prod) | Gunicorn flags |

> **Subtlety:** `LOG_LEVEL` only changes the dev uvicorn `--log-level`. The application's own loggers and file handlers are controlled by `src/config/logging.yaml` (root level `INFO`), independent of `LOG_LEVEL`. See [Error Handling & Logging](11-error-handling-and-logging.md).

---

## Non-runtime config files

| File | Purpose | Editable without code change? |
|------|---------|-------------------------------|
| `src/config/config.yaml` | List of tiktoken encodings to preload | Yes — restart to apply |
| `src/config/logging.yaml` | Logging handlers/filters/formatters | Yes — restart to apply |
| `src/data/models.json` | Model catalog | Yes — restart to apply |
| `src/data/pricing.json` | Pricing catalog | Yes — restart to apply |

Continue to [Authentication, Authorization & Security →](10-security-and-auth.md)
