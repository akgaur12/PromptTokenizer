# 13 · Testing Strategy & Coverage

## Approach

Tests are **HTTP-level integration tests**: they exercise the real FastAPI app end-to-end through Starlette's `TestClient`, hitting actual routes, real Pydantic validation, the real model/pricing catalogs, and real `tiktoken` encodings. There is no mocking of the tokenizer — assertions check genuine token counts. This gives high confidence per test at the cost of being coarser-grained than unit tests.

## Layout

```
tests/
├── __init__.py
├── conftest.py        # shared session-scoped TestClient fixture
├── test_health.py     # /health
├── test_models.py     # /models, /models/{id}, alias resolution
├── test_tokenize.py   # /tokenize
└── test_compare.py    # /compare (and a /pricing smoke check)
```

## The fixture (`conftest.py`)

```python
@pytest.fixture(scope="session")
def client() -> TestClient:
    with TestClient(app) as c:
        yield c
```

- **Session-scoped** so the app's **lifespan runs once** for the whole suite — encodings are preloaded a single time, keeping the suite fast.
- Using `TestClient` as a context manager (`with`) is what triggers the lifespan (startup/shutdown), so tests run against a fully-initialized app.

> Note: `pytest-asyncio` is a declared dev dependency, but the current tests are **synchronous** and use the sync `TestClient`. The legacy README's async `AsyncClient` fixture is not what's in the repo.

## What's covered

| File | Tests | Key assertions |
|------|-------|----------------|
| `test_health.py` | liveness shape | `status=="ok"`, has `service`/`version` |
| `test_models.py` | list, filter by group, filter by provider, get-by-id, 404, **alias resolution** | `gpt-4→cl100k_base`, `gpt-3.5-turbo→cl100k_base`, `gpt-4o→o200k_base`; `total==len(items)` |
| `test_tokenize.py` | counts, token strings, token ids, omit-tokens flag, empty-text 422, unknown-model 404, raw-encoding path | `"Hello world"` with `gpt-4` → `token_count==2`, `tokens==["Hello"," world"]`, `resolved_tokenizer=="cl100k_base"` |
| `test_compare.py` | multi-model compare, >10 models 422, empty-models 422, inline error for bad model, pricing route smoke | shared-encoding models give equal counts; bad model returns non-null `error`; `text_length==11` |

### Notable behavior locked in by tests

- **Alias correctness** is the most important guarantee — several tests assert exact `tokenizer_ref` mappings (the core feature).
- **Validation contract** — empty text and oversized/empty model lists must return `422` with `code=="VALIDATION_ERROR"`.
- **Soft-failure compare** — a bad model id yields an inline `error` (non-null) while valid models in the same request still succeed, all under a `200`.
- **Exact token output** — `["Hello"," world"]` proves both the encode and the per-token decode path work, including the leading-space token convention of BPE.

## Running tests

```bash
uv run pytest tests/ -v                          # all, verbose
uv run pytest tests/test_tokenize.py -v          # one file
uv run pytest tests/ -k alias                     # by keyword
uv run pytest tests/ --cov=src --cov-report=term-missing   # with coverage
```

> Coverage needs `pytest-cov`, which is **not** currently a declared dev dependency. Add it (`uv add --dev pytest-cov`) before using `--cov`.

## Gaps & suggested additions

The suite is solid for the happy paths and core contracts but does not yet cover:

| Untested area | Suggested test |
|---------------|----------------|
| Cost estimation fields | tokenize `gpt-4o` → assert `estimated_input_cost`, `cost_currency=="USD"` |
| Missing-pricing note | tokenize `r50k_base` → assert `cost_estimation_note` populated, cost `null` |
| `word_count`/`character_count` | assert against known text |
| `/pricing?model_id=` filter | filter to one model, assert `total==1`; unknown id → `total==0` |
| `/models?search=` | substring filter behavior |
| `include_token_ids=false` | assert `token_ids is None` |
| `TokenizerNotAvailableError` (503) | requires a catalog entry whose ref isn't preloaded |
| Text at the 200k boundary | exactly 200,000 chars passes; 200,001 → 422 |
| Docs gating | `APP_ENV != dev` → `/docs` returns 404 |

## Testing philosophy for contributors

When you change behavior, prefer adding an HTTP-level test that asserts the **observable contract** (status code, error code, JSON fields) rather than internal calls — that's the style the suite already follows and it keeps tests resilient to refactors. See [Development Workflow](14-development-workflow.md).

Continue to [Development Workflow →](14-development-workflow.md)
