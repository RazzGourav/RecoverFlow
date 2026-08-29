"""
RecoverFlow — Integration test fixtures.

Why: Integration tests need a real database session and pre-seeded test
data (merchant, customer, recovery case).  These fixtures create minimal
rows needed to satisfy FK constraints and are shared across all integration
test files via conftest.py auto-discovery.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

import os

# ─── Connection ──────────────────────────────────────────────────────────────
# Connects to the real Postgres instance started by docker-compose.
# When running tests locally (outside Docker), the host-mapped port 5432 is used.
TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL", "postgresql+asyncpg://recoverflow:recoverflow@localhost:5432/recoverflow")

# ─── Session fixture ─────────────────────────────────────────────────────────


@pytest_asyncio.fixture()
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Provide an async SQLAlchemy session against the real test database.

    Why: Integration tests must validate actual DB round-trips.
    Each test gets a fresh session; rows committed in a test persist for
    the duration of that test and are cleaned up manually in teardown.
    """
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    TestingSessionLocal = sessionmaker(
        bind=engine, class_=AsyncSession, expire_on_commit=False
    )
    async with TestingSessionLocal() as session:
        yield session
    await engine.dispose()


# ─── Seed-data fixture ───────────────────────────────────────────────────────


@pytest_asyncio.fixture()
async def setup_test_case(db_session: AsyncSession):
    """
    Seed one Merchant, one Customer, and one RecoveryCase for use in tests.

    Why: Most integration tests need a parent RecoveryCase to attach actions
    or audit events to.  Creating these inline in every test duplicates code
    and risks FK failures if the order changes.

    Returns a (case, customer, merchant) tuple so tests can reference any object.
    """
    from apps.api.db.models import (
        CaseStatus,
        Customer,
        CustomerSegment,
        FailureType,
        Merchant,
        RecoveryCase,
    )

    merchant = Merchant(
        name=f"Test Merchant {uuid.uuid4().hex[:6]}",
        razorpay_account_reference=f"acc_test_{uuid.uuid4().hex[:8]}",
        is_active=True,
    )
    db_session.add(merchant)
    await db_session.flush()

    customer = Customer(
        merchant_id=merchant.id,
        external_customer_id=f"cust_test_{uuid.uuid4().hex[:8]}",
        segment=CustomerSegment.MEDIUM_VALUE,
        tenure_days=120,
    )
    db_session.add(customer)
    await db_session.flush()

    case = RecoveryCase(
        merchant_id=merchant.id,
        customer_id=customer.id,
        amount_paise=50_000,
        failure_type=FailureType.PAYMENT_METHOD,
        status=CaseStatus.AWAITING_APPROVAL,
        recoverability_score=0.75,
    )
    db_session.add(case)
    await db_session.commit()

    yield case, customer, merchant

    # Teardown — delete the created rows so tests are idempotent.
    await db_session.execute(
        text("DELETE FROM audit_events WHERE case_id = :cid"), {"cid": case.id}
    )
    await db_session.execute(
        text("DELETE FROM actions WHERE case_id = :cid"), {"cid": case.id}
    )
    await db_session.execute(
        text("DELETE FROM recovery_cases WHERE id = :cid"), {"cid": case.id}
    )
    await db_session.execute(
        text("DELETE FROM customers WHERE id = :uid"), {"uid": customer.id}
    )
    await db_session.execute(
        text("DELETE FROM merchants WHERE id = :mid"), {"mid": merchant.id}
    )
    await db_session.commit()
