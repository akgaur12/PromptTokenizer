# GPT Tokenizer Backend

A production-ready FastAPI backend for a tokenizer platform supporting OpenAI encodings and model aliases.

## Prerequisites

- Python 3.11+
- pip

## Setup

```bash
# Clone and enter project
cd prompttokenizer

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env as needed
```

## Running

```bash
# Option 1: run.py
python run.py

# Option 2: uvicorn directly
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | /health | Service health check |
| GET | /api/v1/models | List all models and encodings |
| GET | /api/v1/models/{model_id} | Get model/encoding detail |
| POST | /api/v1/tokenize | Tokenize text with a model |
| POST | /api/v1/compare | Compare token counts across models |
| GET | /api/v1/pricing | List pricing metadata |

Interactive docs: http://localhost:8000/docs
ReDoc: http://localhost:8000/redoc

## Running Tests

```bash
pytest tests/ -v
```

## Architecture

- `app/core/` - config, CORS, logging, exception handling
- `app/routers/` - FastAPI route handlers
- `app/schemas/` - Pydantic request/response models
- `app/services/` - business logic (registry, tokenizer, pricing)
- `app/adapters/` - abstract adapter interface for tokenizer backends
- `app/data/` - static JSON data (models, pricing)
- `app/utils/` - shared utilities

## Extending

To add a new tokenizer family (e.g. Hugging Face), implement `BaseTokenizerAdapter` from `app/adapters/base.py` and register it in `tokenizer_service.py`.
