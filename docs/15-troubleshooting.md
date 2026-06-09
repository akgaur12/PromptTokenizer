# 15 · Troubleshooting Guide

Common failure modes, their cause, and the fix. Symptoms are grouped by where you'd notice them.

---

## Startup / install

### `ModuleNotFoundError: No module named 'gunicorn'` (or `psutil`)

**Cause:** you installed via `pip install -r requirements.txt`, which is **drifted** and omits `gunicorn` and `psutil`.
**Fix:** use `uv sync` (authoritative). If you must use pip: `pip install gunicorn psutil`. See [Tech Stack](04-technology-stack-and-dependencies.md).

### `ModuleNotFoundError: No module named 'yaml'`

**Cause:** `PyYAML` is imported by `logger.py` and `config_loader.py` but is **not declared** in `pyproject.toml`; it's currently only present transitively.
**Fix:** `uv add pyyaml` to declare it explicitly. (If it ever disappears from the transitive tree, startup fails because logging configures at import time.)

### App fails immediately with a Pydantic `ValidationError` mentioning `ModelEntry`/`PricingEntry`

**Cause:** a row in `models.json` / `pricing.json` is malformed (missing a required field, wrong type). The catalogs are validated at startup (fail-fast).
**Fix:** check the offending row against the schema in [Data Model](08-data-model-and-catalog.md). Required model fields: `id, label, group, provider, adapter, tokenizer_ref, status`. Required pricing fields: `model_id, input_price_per_1m`.

### `FileNotFoundError: Config file not found: src/config/config.yaml`

**Cause:** the process was started from a directory other than the repo root. Paths like `src/config/config.yaml` and `src/config/logging.yaml` are **relative to the working directory**.
**Fix:** always launch from the repo root (`python run.py` / `uv run start`). In Docker the `WORKDIR /app` handles this.

---

## Configuration

### `/docs`, `/redoc`, `/openapi.json` return 404

**Cause:** docs are gated to `APP_ENV == "dev"` (exact string). `.env.example` ships `APP_ENV=development`, which does **not** match.
**Fix:** set `APP_ENV=dev` in `.env` and restart. See [the gotcha](09-configuration.md#️-the-app_env-docs-gating-gotcha).

### `ALLOWED_ORIGINS` ignored / browser CORS errors

**Cause 1:** wrong format — though the custom dotenv source accepts comma-separated values, a stray space or quote can break parsing.
**Cause 2:** the calling origin isn't in the list (CORS is an explicit allow-list, never `*`).
**Fix:** `ALLOWED_ORIGINS=https://app.example.com,https://www.example.com` (comma-separated, no surrounding brackets needed), restart. Remember CORS only affects browsers — `curl`/server calls aren't blocked.

### Setting `LOG_LEVEL=DEBUG` doesn't produce DEBUG logs

**Cause:** `LOG_LEVEL` only changes the **dev uvicorn** `--log-level`. Application file logging is governed by `src/config/logging.yaml`, whose `root.level` is `INFO`, so DEBUG records are dropped before reaching `debug_file`.
**Fix:** set `root.level: DEBUG` in `logging.yaml` (and restart) to capture DEBUG to file/console.

### Changes to `models.json` / `pricing.json` don't show up

**Cause:** catalogs are loaded once into `@lru_cache` singletons at startup.
**Fix:** restart the process. In dev, editing a non-`.py` file may not always trigger `--reload` (`--reload-dir src` watches `src/`, but reliability varies); restart manually to be sure.

---

## Request-time errors

### `404 MODEL_NOT_SUPPORTED`

The `model` you sent isn't a catalog `id`. List valid ids with `GET /api/v1/models`. Remember ids are exact (e.g. `gpt-3.5-turbo`, not `gpt-3.5_turbo`). Also raised if a catalog entry's `adapter` isn't `openai_tiktoken` (not the case for any shipped entry).

### `503 TOKENIZER_NOT_AVAILABLE`

A model resolved to an encoding that isn't preloaded. This only happens if a catalog `tokenizer_ref` is **not** listed in `src/config/config.yaml`.
**Fix:** add the encoding name to `config.yaml`'s `tokenizer.encoding_names` and restart. See [Extending](17-design-patterns-and-extending.md).

### `422 VALIDATION_ERROR`

Body/params failed validation. Check `details` in the response. Common triggers: empty `text`, `text` > 200,000 chars, `models` empty or > 10 items, wrong types.

### `tokens` array shows `` (replacement chars) or `<12345>`

**Cause:** per-token decoding is best-effort. A character spanning multiple BPE tokens can't be reconstructed from a single token's bytes (→ ``); special/unknown tokens render as `<id>`.
**Not a bug:** `token_count` and `token_ids` are always exact. The `tokens` array is a human-readable approximation. See [Core Modules](06-core-modules.md).

### Cost fields are `null`

**Cause:** no pricing row matches the model id (raw encodings and some models have none).
**Expected:** `estimated_input_cost`/`cost_currency` are `null` and `cost_estimation_note` explains it. See [Data Model](08-data-model-and-catalog.md).

---

## Production / Docker

### `/health` works but reports low memory under multiple workers

**Cause:** `/health` reads `psutil.Process(os.getpid())` — only the **current worker's** memory, not the whole fleet. Each request may hit a different worker.
**Not a bug:** it's a per-worker liveness signal, not an aggregate metric.

### High memory per worker

**Cause:** every Gunicorn worker preloads its own copy of all tiktoken encodings (o200k_base is large).
**Fix:** size `WORKERS` against available RAM; don't over-provision workers. See [Performance](16-performance.md).

### Port already in use

The committed `.env` uses `APP_PORT=8192`; the defaults/Docker use `8000`. Make sure your `-p` mapping and `APP_PORT` agree, and nothing else holds the port.

---

## Diagnostics quick-reference

```bash
# Is it up and which version/worker?
curl -s localhost:8000/health | jq

# What models exist?
curl -s localhost:8000/api/v1/models | jq '.items[].id'

# Reproduce a tokenize precisely
curl -s -X POST localhost:8000/api/v1/tokenize \
  -H 'Content-Type: application/json' \
  -d '{"model":"gpt-4o","text":"test"}' | jq

# Tail the error log
tail -f logs/prompttokenizer_error.log
```

> **Tip:** unhandled 500s return a generic message to the client by design. To see the actual traceback, add `logger.exception(...)` in the catch-all handler in `src/core/exceptions.py`, or inspect server stdout/console logs.

Continue to [Performance & Optimizations →](16-performance.md)
