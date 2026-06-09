# 01 · Project Overview & Objectives

## What is PromptTokenizer?

PromptTokenizer is a stateless **FastAPI microservice** that answers a deceptively simple question for LLM developers:

> *"How many tokens is this text for model X, and what will it cost?"*

It wraps OpenAI's [`tiktoken`](https://github.com/openai/tiktoken) tokenizer behind a clean, versioned REST API and layers three things on top of raw tokenization:

1. **Model-alias resolution** — callers ask for friendly names like `gpt-4o`, `gpt-3.5-turbo`, or `o3`, and the service resolves each to the correct underlying tiktoken *encoding* (`o200k_base`, `cl100k_base`, …). Callers never have to know which encoding a model uses.
2. **Cross-model comparison** — tokenize one piece of text against up to 10 models in a single request and get token counts side by side.
3. **Cost estimation & pricing metadata** — every tokenize response includes an estimated input cost (when pricing is known), and a dedicated endpoint serves the full pricing catalog.

## Why it exists (the problem)

Token counting is everywhere in LLM applications — for prompt budgeting, context-window planning, cost forecasting, truncation, and billing. But:

- `tiktoken` works with **encoding names**, not model names. Developers constantly look up "which encoding does `gpt-4o` use?"
- Loading a tiktoken encoding is **non-trivial** (it downloads/initializes a BPE merge table). Doing this per-request is wasteful.
- Pricing data is scattered and changes often.
- Front-end / multi-language clients shouldn't bundle a Python tokenizer just to count tokens.

PromptTokenizer centralizes all of this behind one HTTP service that any client — browser, backend, CLI — can call.

## Primary objectives

| Objective | How it's met |
|-----------|--------------|
| **Accurate token counts** | Delegates to `tiktoken`, the canonical OpenAI tokenizer |
| **Model-name ergonomics** | Data-driven alias → encoding resolution via `models.json` |
| **Fast responses** | All encodings preloaded at startup; everything cached as singletons |
| **Easy to extend** | Add a model with a JSON edit; add a backend by subclassing one ABC |
| **Operable** | Env-driven config, structured rotating logs, health endpoint with memory stats |
| **Safe to expose** | Read-only, input-size limits, generic error envelope, API docs gated to dev |

## Who is this for?

- **Application developers** integrating LLMs who need token/cost math without embedding a tokenizer.
- **Front-end teams** building token-counter UIs (a hosted UI is referenced in the CORS allow-list: `prompt-tokenizer.site`).
- **Platform/infra teams** who want a small, well-behaved internal microservice.

## Scope & non-goals

**In scope**

- Tokenizing text for OpenAI-family models and raw OpenAI encodings.
- Listing/filtering the model catalog and pricing catalog.
- Estimating **input** cost from token count and per-million pricing.

**Explicitly out of scope (today)**

- **No actual LLM calls.** The service never sends text to any model provider; it only tokenizes locally.
- **No non-OpenAI tokenizers shipped.** The architecture supports pluggable adapters (`BaseTokenizerAdapter`), and the legacy docs mention DeepSeek, but **the only implemented adapter is `openai_tiktoken`**. See [Design Patterns & Extending](17-design-patterns-and-extending.md).
- **No persistence / database.** Catalogs are static JSON read once at startup.
- **No authentication / user accounts.** See [Security](10-security-and-auth.md).
- **No output-cost estimation.** Pricing data carries output prices, but tokenize only estimates input cost (it has no generated output to measure).

## Key capabilities at a glance

| Capability | Endpoint |
|------------|----------|
| Liveness + memory probe | `GET /health` |
| Browse / filter model catalog | `GET /api/v1/models` |
| Look up one model | `GET /api/v1/models/{model_id}` |
| Tokenize text (count, tokens, ids, cost) | `POST /api/v1/tokenize` |
| Compare token counts across models | `POST /api/v1/compare` |
| Browse pricing catalog | `GET /api/v1/pricing` |

Continue to [High-Level Architecture →](02-architecture.md)
