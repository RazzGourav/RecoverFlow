"""
RecoverFlow — pytest configuration and shared fixtures.

Why this file exists:
  Centralises test fixtures so that individual test files don't need to
  duplicate setup/teardown code.  The async client fixture creates an
  in-process test client so tests run without starting a real server.

  The DB dependency is overridden with a no-op so unit tests run without
  a real Postgres connection.  Integration tests (Phase 1+) will use a
  real test database via pytest-asyncio + asyncpg.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from main import app
from dependencies.db import get_db


async def _mock_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Mock database session for unit tests.

    Why: Unit tests must not require a running Postgres instance.
    This mock satisfies the FastAPI dependency without any real DB calls.
    Integration tests override this with a real async session.
    """
    mock = AsyncMock(spec=AsyncSession)
    # Make execute() return a mock result so health checks don't crash
    mock.execute.return_value = AsyncMock()
    yield mock  # type: ignore[misc]


@pytest.fixture()
async def client() -> AsyncGenerator[AsyncClient, None]:
    """
    Provide an async HTTP test client for the FastAPI app.

    Why: httpx.AsyncClient with ASGITransport runs the app in-process,
    which is faster than spinning up a real server and doesn't require
    Docker for unit tests.  The DB dependency is replaced with a mock.
    """
    app.dependency_overrides[get_db] = _mock_db
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as ac:
        yield ac
    app.dependency_overrides.clear()
