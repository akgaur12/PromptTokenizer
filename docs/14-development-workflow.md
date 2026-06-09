# 14 · Development Workflow & Coding Standards

## First-time setup

```bash
git clone <repo-url>
cd PromptTokenizer

uv sync                  # creates .venv, installs runtime + dev deps from uv.lock
cp .env.example .env     # then set APP_ENV=dev to enable /docs locally
```

Requirements: Python 3.13+ and [`uv`](https://docs.astral.sh/uv/). (Pip is possible via `requirements.txt` but it's drifted — see [Tech Stack](04-technology-stack-and-dependencies.md).)

## The day-to-day loop

```bash
python run.py dev        # or: uv run start dev  → hot-reload on src/ changes
# edit code…             (uvicorn restarts automatically)
uv run ruff check src/   # lint
uv run ruff format src/  # format
uv run pytest tests/ -v  # test
```

Open `http://localhost:8000/docs` (when `APP_ENV=dev`) for interactive Swagger UI to poke endpoints by hand.

## Command reference

| Task | Command |
|------|---------|
| Install deps | `uv sync` |
| Add a runtime dep | `uv add <pkg>` |
| Add a dev dep | `uv add --dev <pkg>` |
| Dev server (reload) | `python run.py dev` / `uv run start dev` |
| Prod server (gunicorn) | `python run.py` / `uv run start` |
| Uvicorn directly | `uv run uvicorn src.main:app --reload` |
| Lint | `uv run ruff check src/` |
| Auto-fix lint | `uv run ruff check --fix src/` |
| Format | `uv run ruff format src/` |
| Check formatting only | `uv run ruff format --check src/` |
| Run tests | `uv run pytest tests/ -v` |
| Single test file | `uv run pytest tests/test_tokenize.py -v` |
| Coverage | `uv run pytest tests/ --cov=src --cov-report=term-missing` |
| Build image | `docker build -t prompttokenizer .` |

## Coding standards & conventions

Enforced and conventional rules observed across the codebase:

### Ruff (enforced — `pyproject.toml`)

- **Line length: 200.** Long signatures/dicts stay on one line.
- **Quotes: double.** Indent: spaces.
- **Target: py313.**
- **Lint rule sets:** `E` (pycodestyle), `F` (pyflakes/real bugs), `B` (bugbear), `I` (import sorting), `UP` (pyupgrade/modern syntax), `C4` (comprehensions), `SIM` (simplifications). All are `fixable`.

Run `ruff check --fix` + `ruff format` before committing; CI (once added) should `--check` both.

### Conventions observed in the code (follow these)

- **`from __future__ import annotations`** at the top of most modules — enables lazy annotation evaluation and clean `X | None` typing.
- **Modern typing**: `list[int]`, `dict[str, X]`, `str | None` — no `typing.List`/`Optional` in new code where avoidable (a few `Optional`/`Tuple` remain in `config.py`/routers).
- **Singletons via `@lru_cache`** for any expensive, process-wide object (settings, registries, services). Keep new shared resources to this pattern.
- **Lazy `%`-style logging**: `logger.info("x=%s", x)` not f-strings.
- **Pydantic for all I/O contracts** — request, response, *and* data-file rows. Don't return raw dicts from routers; return the typed schema (FastAPI serializes it).
- **Thin routers, logic in services** — routers validate + delegate; business logic lives in `src/services/`.
- **Data over code** — prefer a JSON catalog edit to new code when adding a model. See [Extending](17-design-patterns-and-extending.md).
- **Exceptions are typed and central** — raise a domain exception from `src/core/exceptions.py`; let the global handler map it. Don't build `JSONResponse` errors in routers.

### File/module naming

- One resource per router file (`tokenize.py`, `compare.py`, …) and a matching schema file.
- Services are `<thing>_service.py` or `<thing>_registry.py`; adapters are `<backend>_tokenizer_adapter.py`.

## Git workflow

- **Main branch:** `main` (used for PRs).
- Commit history uses **Conventional Commits** (`feat:`, `chore:`) — match that style.
- `.env`, `logs/`, caches, and `notebooks/` are gitignored; don't commit them.
- Keep `CLAUDE.md`/`README.md` in sync with reality when you change behavior (both are currently partly stale — see notes throughout this book).

### A typical change: adding a model

1. Add the entry to `src/data/models.json` (and a pricing row to `pricing.json` if applicable).
2. Ensure its `tokenizer_ref` is in `src/config/config.yaml` (it will be, for existing OpenAI encodings).
3. Add/extend a test asserting its resolution.
4. `ruff check --fix && ruff format && pytest`.
5. Commit with `feat: add <model> to catalog`.

No application code changes are needed for the above — see [Extending](17-design-patterns-and-extending.md) for adding a *new tokenizer backend* (which does require code).

Continue to [Troubleshooting Guide →](15-troubleshooting.md)
