# syntax=docker/dockerfile:1

# ---- Builder: install dependencies into a virtualenv with uv ----
FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim AS builder

# uv tuning: compile bytecode for faster startup, copy (not link) packages,
# and install into the project's own .venv.
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/app/.venv

WORKDIR /app

# Install dependencies first (without the project) so this layer is cached
# across source changes. Only re-runs when the lockfile/manifest changes.
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project --no-dev

# Copy the application source and install the project itself.
COPY . /app
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev


# ---- Runtime: slim image with just the venv and source ----
FROM python:3.13-slim-bookworm AS runtime

# Run as a non-root user.
RUN groupadd --system app && useradd --system --gid app --home-dir /app app

WORKDIR /app

# Bring over the prepared virtualenv and the application code.
COPY --from=builder --chown=app:app /app /app

# Put the venv on PATH so gunicorn/uvicorn resolve without activation.
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# The app writes rotating logs under ./logs (created at startup too).
RUN mkdir -p /app/logs && chown -R app:app /app/logs

USER app

EXPOSE 8000

# Default to production (gunicorn + UvicornWorker via run.py).
CMD ["python", "run.py"]
