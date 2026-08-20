"""
RecoverFlow API — health check route.

Why this file exists:
  Docker healthchecks, load balancers, and the smoke-test script all need a
  lightweight endpoint that verifies:
  1. The API process is alive and responding.
  2. The database connection is alive (via a trivial async query).

  A single GET /health endpoint is the conventional way to satisfy this.
"""

from __future__ import annotations

from typing import Any

import structlog
from fastapi import APIRouter, Depends, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from dependencies.db import get_db

logger = structlog.get_logger(__name__)

router = APIRouter(tags=["health"])


@router.get(
    "/health",
    summary="Health check",
    description="Returns 200 when the API is running and Postgres is reachable.",
    status_code=status.HTTP_200_OK,
)
async def health(db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    """
    Perform a liveness + readiness check.

    Returns:
        A JSON object with status, version, and database connectivity info.
    """
    db_ok = False
    try:
        await db.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        logger.exception("health_check.db_error")

    return {
        "status": "ok" if db_ok else "degraded",
        "database": "connected" if db_ok else "unavailable",
        "service": "recoverflow-api",
        "phase": "0-foundation",
    }
