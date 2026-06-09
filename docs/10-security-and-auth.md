# 10 · Authentication, Authorization & Security

## Authentication & authorization: none (by design)

PromptTokenizer has **no authentication and no authorization layer**. There are no API keys, tokens, sessions, users, roles, or scopes anywhere in the codebase.

This is a deliberate fit for what the service is:

- It is a **read-only, stateless** utility — it tokenizes text and serves static catalogs.
- It holds **no secrets and no user data** — nothing to protect with credentials.
- It performs **no outbound calls** and triggers no side effects.

> **Operational implication:** if you expose this service publicly, *anyone* who can reach it can call every endpoint. Access control, rate limiting, and abuse prevention must be provided by the surrounding infrastructure (API gateway, reverse proxy, WAF, network policy). See "Hardening checklist" below.

There is therefore no auth flow to diagram. The only request-gating that exists is **input validation** (Pydantic) and **CORS** (browser-origin policy).

---

## CORS

Configured in `src/core/cors.py`:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,   # from ALLOWED_ORIGINS
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

| Setting | Value | Note |
|---------|-------|------|
| `allow_origins` | explicit list from config | default: `localhost:3000`, `localhost:5173`; prod adds `prompt-tokenizer.site` etc. |
| `allow_credentials` | `True` | cookies/Authorization allowed cross-origin |
| `allow_methods` | `*` | all HTTP methods |
| `allow_headers` | `*` | all request headers |

**Good:** origins are an explicit allow-list, never the wildcard `*`. This is correct, because the browser spec forbids combining `allow_credentials=True` with `allow_origins=["*"]`. Keeping a finite list is the safe pattern.

**To add a front-end origin:** append it to `ALLOWED_ORIGINS` in `.env` (comma-separated) and restart. CORS only affects **browsers** — server-to-server and `curl` calls ignore it.

---

## API documentation gating

Interactive docs are an information-disclosure surface (they reveal the full schema). They are **gated to dev**:

```python
docs_url="/docs"        if settings.app_env == "dev" else None
redoc_url="/redoc"      if settings.app_env == "dev" else None
openapi_url="/openapi.json" if settings.app_env == "dev" else None
```

In any non-`dev` environment these return 404. (Introduced in commit `f468717`.) See the [APP_ENV gotcha](09-configuration.md#️-the-app_env-docs-gating-gotcha).

---

## Input validation & resource limits

The main defense against abuse of a tokenizer service is bounding work per request:

| Guard | Where | Limit |
|-------|-------|-------|
| Max text length | `TokenizeRequest.text` / `CompareRequest.text` | **200,000** chars |
| Min text length | same | 1 char (rejects empty) |
| Max models per compare | `CompareRequest.models` | **10** |
| Min models per compare | same | 1 |
| Type/shape validation | all schemas | Pydantic, → 422 on violation |

These caps prevent a single request from forcing unbounded CPU/memory work (tokenizing a multi-megabyte string, or fanning out to hundreds of models). They are not a substitute for rate limiting.

---

## Error-message hygiene

The catch-all exception handler returns a **generic** message and never leaks internals:

```python
@app.exception_handler(Exception)
async def generic_handler(request, exc):
    return _error_response("INTERNAL_ERROR", "An internal error occurred", status_code=500)
```

Stack traces and exception details are not sent to clients. (They are still logged server-side — see [Logging](11-error-handling-and-logging.md).) Domain errors (`MODEL_NOT_SUPPORTED`, etc.) return only the safe model id/name in their message.

---

## Container security posture

The `Dockerfile` follows several hardening best practices (see [Build & Deployment](12-build-and-deployment.md)):

- **Non-root runtime user** (`app:app`, created with `--system`).
- **Slim base image** (`python:3.13-slim-bookworm`) — smaller attack surface.
- **Multi-stage build** — build tooling (`uv`, caches) does not ship in the runtime image.
- **Frozen dependencies** (`uv sync --frozen`) — reproducible, no surprise upgrades.
- `.dockerignore` excludes `.env`, `.git`, tests, notebooks from the image.

---

## Known considerations & residual risks

| Area | Status | Recommendation |
|------|--------|----------------|
| No authn/authz | by design | Put behind a gateway if internet-facing |
| No rate limiting | not implemented | Add at proxy/gateway (per-IP/token) |
| No request size limit beyond field caps | partial | The 200k char cap bounds body size for these endpoints; set a proxy body-size limit too |
| `allow_credentials=True` + open methods/headers | acceptable | Fine given the fixed origin list; tighten methods to `["GET","POST","OPTIONS"]` if desired |
| No HTTPS termination in app | expected | Terminate TLS at the proxy/load balancer |
| Undeclared `PyYAML` dep | latent | Declare it explicitly (see ch.04 / ch.15) |
| `psutil` reads only current worker's memory | informational | Fine for liveness; not a fleet-wide metric |

### Hardening checklist for production exposure

1. Run behind a reverse proxy / API gateway (nginx, Traefik, cloud LB).
2. Terminate TLS at the proxy.
3. Add rate limiting and request-body size limits at the proxy.
4. Set `APP_ENV` to something other than `dev` to disable docs (or keep docs internal-only).
5. Restrict `ALLOWED_ORIGINS` to the exact front-end domains.
6. Run the provided non-root container; keep base images patched.
7. Ship logs to a central system; alert on `ERROR`-level volume.

Continue to [Error Handling & Logging →](11-error-handling-and-logging.md)
