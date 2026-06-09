# 12 · Build, Deployment & CI/CD

## Run modes (`run.py`)

`run.py` is a thin launcher with two modes, selected by the first CLI arg:

| Command | Mode | What it runs |
|---------|------|--------------|
| `python run.py` (or `uv run start`) | **production** | `gunicorn -w <workers> -k uvicorn.workers.UvicornWorker --timeout <t> --graceful-timeout <gt> -b <host>:<port> src.main:app` |
| `python run.py dev` (or `uv run start dev`) | **development** | `uvicorn src.main:app --host <host> --port <port> --reload --reload-dir src --log-level <level>` |

```python
# run.py (essence)
def main():
    if len(sys.argv) > 1 and sys.argv[1] == "dev":
        main_dev()      # uvicorn --reload
    else:
        main_prod()     # gunicorn + UvicornWorker
```

Both pull values from `get_settings()`, so host/port/workers/timeouts are env-driven (see [Configuration](09-configuration.md)).

- **Dev:** single Uvicorn process, hot-reload watching only `src/` (`--reload-dir src`), log level from `LOG_LEVEL`.
- **Prod:** Gunicorn supervises `WORKERS` Uvicorn worker processes — multi-core utilization, graceful restarts, and worker timeouts.

The `start` console script is declared in `pyproject.toml` (`start = "run:main"`), so `uv run start [dev]` works after `uv sync`.

---

## Local build / install

```bash
uv sync                 # resolve + install into .venv from uv.lock (reproducible)
# or, with pip:
pip install -r requirements.txt   # ⚠ drifted — missing gunicorn & psutil (see ch.04)
```

The project is a proper installable package (`hatchling` build backend, `packages = ["src"]`), so `uv build` produces a wheel if needed.

---

## Docker

### Multi-stage build (`Dockerfile`)

**Stage 1 — builder** (`ghcr.io/astral-sh/uv:python3.13-bookworm-slim`):

1. Sets uv tuning env: `UV_COMPILE_BYTECODE=1` (faster startup), `UV_LINK_MODE=copy`, `UV_PROJECT_ENVIRONMENT=/app/.venv`.
2. **Layer-cached dependency install**: with `uv.lock` + `pyproject.toml` bind-mounted and a uv cache mount, runs `uv sync --frozen --no-install-project --no-dev`. This layer only rebuilds when the lockfile/manifest changes — source edits don't bust it.
3. Copies the source and runs `uv sync --frozen --no-dev` to install the project itself.

**Stage 2 — runtime** (`python:3.13-slim-bookworm`):

1. Creates a **non-root** system user/group `app`.
2. Copies the prepared `/app` (venv + code) from the builder with `--chown=app:app`.
3. Puts the venv on `PATH`; sets `PYTHONUNBUFFERED=1`, `PYTHONDONTWRITEBYTECODE=1`.
4. Creates `/app/logs` owned by `app`.
5. `USER app`, `EXPOSE 8000`, `CMD ["python", "run.py"]` → **production (Gunicorn)** by default.

### Build & run

```bash
docker build -t prompttokenizer:0.2.0 .

docker run --rm -p 8000:8000 \
  -e APP_ENV=production \
  -e WORKERS=4 \
  prompttokenizer:0.2.0

# Override config via env or an env-file:
docker run --rm -p 8000:8000 --env-file .env prompttokenizer:0.2.0

# Run dev mode in the container instead of prod:
docker run --rm -p 8000:8000 prompttokenizer:0.2.0 python run.py dev
```

> `.env` is **not** baked into the image (it's in `.dockerignore`). Provide configuration at runtime via `-e` flags or `--env-file`. The image defaults bind to `0.0.0.0:8000`; if you change `APP_PORT`, update the `-p` mapping.

### What ships in the image

`.dockerignore` excludes `.git`, caches, `.venv`, `logs/`, `tests/`, `notebooks/`, `.env`, `CLAUDE.md`, and OS files. The runtime image therefore contains only the venv + `src/` + project metadata.

---

## Health checks & orchestration

Use `GET /health` as the readiness/liveness probe — it returns `200` once the process is serving (encodings are preloaded during lifespan startup, so a `200` means the service is genuinely ready to tokenize).

```yaml
# Kubernetes example
readinessProbe:
  httpGet: { path: /health, port: 8000 }
  initialDelaySeconds: 5
  periodSeconds: 10
livenessProbe:
  httpGet: { path: /health, port: 8000 }
  periodSeconds: 15
```

```dockerfile
# Optional Dockerfile HEALTHCHECK (not currently in the file)
HEALTHCHECK --interval=30s --timeout=3s \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8000/health').status==200 else 1)"
```

---

## Scaling

The service is **stateless**, so scale horizontally without coordination:

- **Within a host:** raise `WORKERS` (Gunicorn worker processes).
- **Across hosts:** run more containers behind a load balancer.

Each worker/container independently preloads its own copy of the tiktoken encodings (a few hundred MB combined for o200k — see [Performance](16-performance.md)). Size `WORKERS` against available RAM, not just CPU.

---

## CI/CD

> **There is currently no CI/CD configured in the repository** — no `.github/workflows/`, no GitLab CI, no other pipeline files exist.

Recommended minimal pipeline to add:

```yaml
# .github/workflows/ci.yml (suggested)
name: CI
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v5
      - run: uv sync
      - run: uv run ruff check src/
      - run: uv run ruff format --check src/
      - run: uv run pytest tests/ -v
  docker:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: docker build -t prompttokenizer:${{ github.sha }} .
```

This would lint, format-check, test, and build the image on every push/PR. See [Testing](13-testing.md) and [Development Workflow](14-development-workflow.md) for the underlying commands.

Continue to [Testing Strategy & Coverage →](13-testing.md)
