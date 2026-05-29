from __future__ import annotations
from contextlib import asynccontextmanager
from fastapi import FastAPI
from src.core.config import get_settings
from src.core.cors import setup_cors
from src.core.logger import configure_logging, get_logger
from src.core.exceptions import register_exception_handlers
from src.routers import health, models, tokenize, compare, pricing

configure_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    logger.info("Starting %s v%s", settings.app_name, settings.app_version)
    yield
    logger.info("Shutting down %s", settings.app_name)


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="Production-ready tokenizer platform API supporting OpenAI encodings and model aliases.",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    setup_cors(app)
    register_exception_handlers(app)

    app.include_router(health.router)
    app.include_router(models.router, prefix=settings.api_prefix)
    app.include_router(tokenize.router, prefix=settings.api_prefix)
    app.include_router(compare.router, prefix=settings.api_prefix)
    app.include_router(pricing.router, prefix=settings.api_prefix)

    return app


app = create_app()
