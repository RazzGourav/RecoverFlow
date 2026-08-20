"""
RecoverFlow API — database session dependency.

Why this file exists:
  FastAPI's dependency injection system requires a callable that yields an
  AsyncSession.  Centralising it here means every route that needs DB access
  adds exactly `db: AsyncSession = Depends(get_db)` — no boilerplate, and
  tests can override this single function via `app.dependency_overrides`.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from db.session import AsyncSessionLocal


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Yield a database session for the duration of a single request.

    The session is closed (and the connection returned to the pool) whether
    the request succeeds or raises an exception.
    """
    async with AsyncSessionLocal() as session:
        yield session
