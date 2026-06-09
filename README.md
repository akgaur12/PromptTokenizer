# PromptTokenizer

A production-ready FastAPI microservice that tokenizes text using OpenAI encodings (via [`tiktoken`](https://github.com/openai/tiktoken)), resolves model aliases (e.g. `gpt-4o` → `o200k_base`) to their underlying tokenizers, compares token counts across models, and estimates cost from a built-in pricing catalog — all through a clean REST API.

> 📚 **Full documentation** lives in [`docs/`](docs/00-index.md) — architecture, data flow, API contracts, deployment, and more.

## Features

- **Tokenize** text for any catalog model or raw encoding (count, token strings, token IDs).
- **Model-alias resolution** — request friendly names; the service maps them to the correct tiktoken encoding.
- **Compare** token counts across up to 10 models in one call (with per-model soft failures).
- **Cost estimation** — input-cost estimate per request, plus a pricing catalog endpoint.
- **Stateless & fast** — encodings preloaded at startup; settings, catalogs, and adapters cached as singletons.

## Quick start

Requires **Python 3.13+** and [`uv`](https://docs.astral.sh/uv/).

```bash
uv sync                  # install dependencies into .venv
cp .env.example .env     # configure (set APP_ENV=dev to enable /docs)

python run.py dev        # dev server (hot-reload) — http://localhost:8000
# python run.py          # production (gunicorn + UvicornWorker)
```

```bash
curl localhost:8000/health
curl -X POST localhost:8000/api/v1/tokenize \
  -H 'Content-Type: application/json' \
  -d '{"model":"gpt-4o","text":"Hello world"}'
```

Interactive API docs (when `APP_ENV=dev`): `/docs` (Swagger), `/redoc`.

## API

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Liveness + process memory |
| GET | `/api/v1/models` | List/filter the model catalog (`group`, `provider`, `search`) |
| GET | `/api/v1/models/{model_id}` | Fetch a single catalog entry |
| POST | `/api/v1/tokenize` | Tokenize text for one model/encoding |
| POST | `/api/v1/compare` | Token counts across multiple models |
| GET | `/api/v1/pricing` | Pricing catalog (all or `?model_id=`) |

**Tokenize** — `include_tokens` and `include_token_ids` default to `true`; `text` is 1–200,000 chars:

```jsonc
// POST /api/v1/tokenize  {"model":"gpt-4o","text":"Hello world"}
{
  "model": "gpt-4o", "resolved_tokenizer": "o200k_base", "provider": "openai",
  "token_count": 2, "tokens": ["Hello", " world"], "token_ids": [13225, 2375],
  "word_count": 2, "character_count": 11,
  "estimated_input_cost": 0.0000025, "cost_currency": "USD", "cost_estimation_note": null
}
```

**Compare** never fails the whole batch — an unsupported model returns an inline `error` with `resolved_tokenizer:"unknown"`, `token_count:0`, while the request stays `200`.

All errors share one envelope: `{"error": {"code", "message", "details"}}` (e.g. `404 MODEL_NOT_SUPPORTED`, `422 VALIDATION_ERROR`).

See the [API Reference](docs/07-api-reference.md) for full request/response contracts.

## Configuration

Environment-driven via `pydantic-settings` (`.env` + env vars). Key variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `APP_ENV` | `dev` | `/docs`, `/redoc`, `/openapi.json` enabled only when `dev` |
| `APP_HOST` / `APP_PORT` | `0.0.0.0` / `8000` | Bind address/port |
| `API_PREFIX` | `/api/v1` | Versioned route prefix |
| `ALLOWED_ORIGINS` | `localhost:3000,localhost:5173` | Comma-separated CORS origins |
| `WORKERS` / `TIMEOUT` / `GRACEFUL_TIMEOUT` | `4` / `120` / `30` | Gunicorn settings (prod) |

Full list and precedence rules: [Configuration](docs/09-configuration.md).

## Project structure

```
src/
├── main.py            # FastAPI app factory + lifespan (preloads encodings)
├── core/              # config, cors, exceptions, logging
├── routers/           # HTTP handlers (health, models, tokenize, compare, pricing)
├── schemas/           # Pydantic request/response models
├── services/          # model_registry, tokenizer_service, openai adapter, pricing
├── adapters/base.py   # BaseTokenizerAdapter (ABC)
├── config/            # config.yaml (encodings), logging.yaml
└── data/              # models.json (34 entries), pricing.json (29 entries)
tests/                 # pytest suite (HTTP-level, via TestClient)
```

Adding a model that uses an existing encoding is a **JSON edit only** — no code changes. See [Design Patterns & Extending](docs/17-design-patterns-and-extending.md).

## Development

```bash
uv run pytest tests/ -v          # tests
uv run ruff check src/           # lint
uv run ruff format src/          # format
docker build -t prompttokenizer .  # container (multi-stage, non-root)
```

See [Development Workflow](docs/14-development-workflow.md), [Testing](docs/13-testing.md), and [Build & Deployment](docs/12-build-and-deployment.md) for details.
