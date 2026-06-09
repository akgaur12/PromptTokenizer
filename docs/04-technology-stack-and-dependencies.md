# 04 · Technology Stack & Dependencies

## Language & runtime

| Item | Value | Source |
|------|-------|--------|
| Language | Python | `pyproject.toml` |
| Minimum version | **3.13** | `requires-python = ">=3.13"` |
| Pinned local version | `3.13` | `.python-version` |
| Build backend | `hatchling` | `[build-system]` |
| Package manager | `uv` (Astral) | `uv.lock`, docs, Dockerfile |

Python 3.13 is required — the code uses modern typing (`list[int]`, `str | None`, `from __future__ import annotations`) and the project targets `py313` in Ruff.

## Runtime dependencies

From `[project.dependencies]` in `pyproject.toml`:

| Package | Version constraint | Role in this project |
|---------|-------------------|----------------------|
| **fastapi** | `>=0.111.0` | Web framework — routing, dependency injection, OpenAPI docs, Pydantic integration |
| **uvicorn[standard]** | `>=0.29.0` | ASGI server — used directly in dev (`--reload`) and as the Gunicorn worker class in prod |
| **gunicorn** | `>=22.0.0` | Production process manager — runs N `UvicornWorker` processes |
| **pydantic** | `>=2.7.0` | Data validation & serialization for all request/response schemas and catalog entries |
| **pydantic-settings** | `>=2.2.0` | Environment/.env-driven configuration (`Settings` class) |
| **tiktoken** | `>=0.7.0` | The actual tokenizer — BPE encodings for OpenAI models |
| **python-dotenv** | `>=1.0.0` | `.env` file parsing (used via pydantic-settings) |
| **psutil** | `>=7.2.2` | Process memory stats for the `/health` endpoint |

### Why each one is here

- **FastAPI + Uvicorn + Gunicorn** is the standard "ASGI in production" trio: Uvicorn is the high-performance ASGI server, Gunicorn supervises multiple Uvicorn workers for multi-core utilization and graceful restarts.
- **Pydantic v2** is doing double duty: it validates inbound HTTP payloads *and* validates the JSON catalog files when they are loaded into `ModelEntry` / `PricingEntry` objects.
- **tiktoken** is the single reason the service exists — everything else is plumbing around it.
- **psutil** powers the `rss_mb` / `vms_mb` fields in `/health`, useful for liveness/memory monitoring.

## Development dependencies

From `[dependency-groups].dev`:

| Package | Version | Role |
|---------|---------|------|
| **pytest** | `>=8.2.0` | Test runner |
| **pytest-asyncio** | `>=0.23.0` | Async test support (declared; current tests use the sync `TestClient`) |
| **httpx** | `>=0.27.0` | HTTP client used by Starlette's `TestClient` |
| **ruff** | `>=0.4.0` | Linter **and** formatter |

## `requirements.txt` vs `uv.lock`

The repo ships **two** dependency declarations:

- **`pyproject.toml` + `uv.lock`** — the authoritative, fully-resolved, reproducible set used by `uv sync` and the Docker build (`uv sync --frozen`).
- **`requirements.txt`** — a hand-maintained convenience list for `pip install -r requirements.txt`.

> ⚠️ **Drift warning.** `requirements.txt` is **not** auto-generated from the lockfile and is currently out of sync: it omits `gunicorn` and `psutil` (both runtime deps) and lists the dev/test deps as if they were runtime deps. Prefer `uv sync` for any real environment. If you must use pip, install `gunicorn` and `psutil` manually, or the production server and `/health` will fail. See [Troubleshooting](15-troubleshooting.md).

## Tooling

| Tool | Config location | Purpose |
|------|-----------------|---------|
| **Ruff** | `[tool.ruff]` in `pyproject.toml` | Lint (`E,F,B,I,UP,C4,SIM`) + format (double quotes, spaces). Line length **200**, target `py313`. |
| **pytest** | `tests/`, `conftest.py` | Tests (see [Testing](13-testing.md)) |
| **uv** | `pyproject.toml`, `uv.lock`, `.python-version` | Env & dependency management |
| **Docker** | `Dockerfile`, `.dockerignore` | Containerized build/deploy (see [Build & Deployment](12-build-and-deployment.md)) |
| **PyYAML** | (transitive) | Parses `logging.yaml` and `config.yaml` |

> **PyYAML note:** `src/core/logger.py` and `src/utils/config_loader.py` both `import yaml`, but PyYAML is **not** a declared dependency in `pyproject.toml`. It is currently present transitively (e.g. via uvicorn/other tooling). This is a latent dependency that should ideally be declared explicitly — see [Troubleshooting](15-troubleshooting.md).

## External services & integrations

**None at runtime.** The service makes no outbound network calls in normal operation:

- tiktoken encodings are loaded from the locally-installed `tiktoken` package data (no download at request time once cached).
- There are no databases, message queues, caches (Redis), or third-party APIs.

The only "integrations" are inbound: the CORS allow-list names front-end origins (`localhost:3000`, `localhost:5173`, and the hosted UI `prompt-tokenizer.site` / Vercel preview). See [Security](10-security-and-auth.md).

Continue to [Directory & File Structure →](05-directory-and-file-structure.md)
