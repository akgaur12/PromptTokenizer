# PromptTokenizer — Documentation

Welcome to the complete technical documentation for **PromptTokenizer**, a production-ready FastAPI microservice that tokenizes text for LLM models, resolves model aliases to their underlying tokenizers, compares token counts across models, and exposes pricing metadata — all through a clean REST API.

This documentation is written to take a developer with **no prior knowledge** of the project from zero to productive, and to serve experienced contributors as a long-term reference.

> **Accuracy note.** This documentation reflects the **actual implementation** in `src/` as of version `0.2.0`. Where the legacy `README.md` or `CLAUDE.md` describe features that are not in the code (e.g. a DeepSeek adapter, different request defaults), this book documents the code as it really runs and flags the discrepancies explicitly.

---

## How to read this book

If you are **new**, read in order: [Overview](01-overview.md) → [Architecture](02-architecture.md) → [System Design & Data Flow](03-system-design-and-data-flow.md) → [API Reference](07-api-reference.md). That gives you the mental model and lets you call the service.

If you are **extending** the service, jump to [Core Modules](06-core-modules.md), [Data Model & Catalog](08-data-model-and-catalog.md), and [Design Patterns & Extending](17-design-patterns-and-extending.md).

If you are **operating** the service, see [Configuration](09-configuration.md), [Build & Deployment](12-build-and-deployment.md), [Error Handling & Logging](11-error-handling-and-logging.md), and [Troubleshooting](15-troubleshooting.md).

---

## Table of Contents

| # | Document | What it covers |
|---|----------|----------------|
| 01 | [Project Overview & Objectives](01-overview.md) | What the service does, who it's for, goals & non-goals |
| 02 | [High-Level Architecture](02-architecture.md) | The four-layer design, component map, request lifecycle |
| 03 | [System Design & Data Flow](03-system-design-and-data-flow.md) | Sequence diagrams, alias resolution, cost estimation flow |
| 04 | [Technology Stack & Dependencies](04-technology-stack-and-dependencies.md) | Every runtime/dev dependency and why it's here |
| 05 | [Directory & File Structure](05-directory-and-file-structure.md) | Every file in the repo explained |
| 06 | [Core Modules & Components](06-core-modules.md) | Deep dive into each module, class, and function |
| 07 | [API Reference & Contracts](07-api-reference.md) | All 6 endpoints, request/response schemas, examples |
| 08 | [Data Model & Catalog](08-data-model-and-catalog.md) | JSON "schema", model & pricing catalogs (the data layer) |
| 09 | [Configuration & Environment Variables](09-configuration.md) | Every setting, precedence rules, the custom dotenv source |
| 10 | [Authentication, Authorization & Security](10-security-and-auth.md) | Auth posture, CORS, docs gating, security considerations |
| 11 | [Error Handling & Logging](11-error-handling-and-logging.md) | Exception model, error envelope, log handlers & filters |
| 12 | [Build, Deployment & CI/CD](12-build-and-deployment.md) | Docker multi-stage build, run modes, deployment, CI status |
| 13 | [Testing Strategy & Coverage](13-testing.md) | Test layout, fixtures, what's covered and what's not |
| 14 | [Development Workflow](14-development-workflow.md) | Local setup, day-to-day loop, common commands |
| 15 | [Troubleshooting Guide](15-troubleshooting.md) | Common failures and fixes |
| 16 | [Performance & Optimizations](16-performance.md) | Singletons, preloading, hot-path analysis |
| 17 | [Design Patterns & Extending](17-design-patterns-and-extending.md) | Patterns used, ADR-style notes, how to add models/adapters/endpoints |
| 18 | [Glossary](18-glossary.md) | Terminology and concepts |

---

## Quick facts

| Property | Value |
|----------|-------|
| Name | `prompttokenizer` |
| Version | `0.2.0` (`pyproject.toml`) |
| Language | Python `>=3.13` |
| Framework | FastAPI |
| Tokenizer backend | `tiktoken` (OpenAI encodings) |
| Endpoints | 6 (`/health`, `/api/v1/models`, `/api/v1/models/{id}`, `/api/v1/tokenize`, `/api/v1/compare`, `/api/v1/pricing`) |
| Model catalog | 34 entries (6 raw encodings + 28 model aliases) in `src/data/models.json` |
| Pricing catalog | 29 entries in `src/data/pricing.json` |
| Persistence | None — static JSON files, loaded once at startup |
| Authentication | None (public read-only API) |
| Package manager | `uv` (with `requirements.txt` fallback) |

---

## 30-second quick start

```bash
uv sync                 # install dependencies into .venv
cp .env.example .env    # configure (optional; sensible defaults exist)
python run.py dev       # start dev server with hot-reload

# In another terminal:
curl -s localhost:8000/health
curl -s -X POST localhost:8000/api/v1/tokenize \
  -H 'Content-Type: application/json' \
  -d '{"model":"gpt-4o","text":"Hello world"}'
```

See [Development Workflow](14-development-workflow.md) for the full setup.
