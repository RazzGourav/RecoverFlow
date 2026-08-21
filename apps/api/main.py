"""
RecoverFlow API — application entry point.

Why this file exists:
  The FastAPI application factory lives here.  Every router, middleware, and
  lifespan hook is registered in one place so that:
  - Tests can import `app` directly without starting a server.
  - The Dockerfile CMD runs `uvicorn main:app` without any path gymnastics.
  - Future phases add new routers by appending to the `include_router` list.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from routes.health import router as health_router
from routes.webhooks import router as webhooks_router

# ---------------------------------------------------------------------------
# Structured logging configuration
# Why: print()-based logging is forbidden by AGENTS.md.  structlog is
# configured once here and imported everywhere else via `structlog.get_logger`.
# ---------------------------------------------------------------------------
structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer()
        if settings.environment == "development"
        else structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(
        getattr(__import__("logging"), settings.log_level)
    ),
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
)

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Lifespan — runs at startup and shutdown.
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """
    Application lifespan manager.

    Startup: verify database connectivity, initialize redis pool, and log readiness.
    Shutdown: dispose engine connections and close redis pool cleanly.
    """
    from arq import create_pool
    from arq.connections import RedisSettings

    from db.session import engine

    logger.info(
        "api.starting",
        environment=settings.environment,
        autonomous_actions_enabled=settings.autonomous_actions_enabled,
    )

    # Verify DB is reachable before accepting traffic
    try:
        async with engine.connect() as conn:
            from sqlalchemy import text

            await conn.execute(text("SELECT 1"))
        logger.info("api.db_connected")
    except Exception as exc:
        logger.error("api.db_connection_failed", error=str(exc))
        # Do not prevent startup — let the health endpoint surface degraded state.

    # Initialize ARQ Redis pool for enqueueing background jobs
    try:
        redis_settings = RedisSettings.from_dsn(settings.redis_url)
        app.state.arq_pool = await create_pool(redis_settings)
        logger.info("api.redis_connected")
    except Exception as exc:
        logger.error("api.redis_connection_failed", error=str(exc))
        app.state.arq_pool = None

    yield  # Application is running

    logger.info("api.shutting_down")
    if getattr(app.state, "arq_pool", None):
        await app.state.arq_pool.close()
    await engine.dispose()
    logger.info("api.shutdown_complete")


# ---------------------------------------------------------------------------
# Application factory
# ---------------------------------------------------------------------------


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.

    Returns:
        A configured FastAPI instance ready to be served.
    """
    app = FastAPI(
        title="RecoverFlow API",
        description=(
            "AI Revenue Recovery Control Plane — "
            "determines which revenue is worth recovering, "
            "selects the safest intervention, executes under merchant-defined limits, "
            "verifies financial outcomes, and measures incremental recovery."
        ),
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # --- CORS ---------------------------------------------------------------
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # --- Routers ------------------------------------------------------------
    app.include_router(health_router)
    app.include_router(webhooks_router)
    from routes.cases import router as cases_router
    app.include_router(cases_router, prefix="/cases", tags=["cases"])

    return app


app = create_app()
