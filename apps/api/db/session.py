"""
RecoverFlow API — database session management.

Why this file exists:
  Provides a single, centralised async SQLAlchemy engine and session factory.
  All route handlers receive a session via FastAPI dependency injection
  (see dependencies/db.py), so connection lifecycle is managed consistently
  and tests can override the fixture without patching internals.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from config import settings

# ---------------------------------------------------------------------------
# Async engine — used by the API at runtime.
# ---------------------------------------------------------------------------
engine = create_async_engine(
    settings.database_url,
    echo=settings.environment == "development",
    pool_pre_ping=True,  # detect stale connections before handing them out
    pool_size=5,
    max_overflow=10,
)

# ---------------------------------------------------------------------------
# Session factory — used by the dependency (dependencies/db.py).
# ---------------------------------------------------------------------------
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)
