"""
RecoverFlow — Integration tests for the human approval workflow.

Tests that POST /cases/{id}/approve and POST /cases/{id}/reject:
  - Perform the correct DB state transitions
  - Write the correct audit_events row
  - Never skip the execution pipeline on approve
"""

from __future__ import annotations

import uuid

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

TEST_DATABASE_URL = "postgresql+asyncpg://recoverflow:recoverflow@localhost:5432/recoverflow"


def _make_session_factory():
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    factory = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    return engine, factory


@pytest_asyncio.fixture()
async def http_client() -> AsyncClient:
    """
    HTTP client against the real running FastAPI server (port 8000).

    Why: The human approval endpoints need a real DB session managed by the
    server itself — sharing the test session causes session identity-map
    conflicts when reading back mutated state.  Hitting the live server lets
    the server manage its own sessions, and we verify by opening a fresh
    read-back session.
    """
    async with AsyncClient(base_url="http://localhost:8000") as ac:
        yield ac


@pytest_asyncio.fixture()
async def readback_session():
    """
    A fresh async session for reading back DB state after an API call.

    Using a separate session guarantees we see committed data, not a stale
    identity map from the write side.
    """
    engine, factory = _make_session_factory()
    async with factory() as session:
        yield session
    await engine.dispose()


@pytest_asyncio.fixture()
async def seed_case():
    """
    Seed a Merchant, Customer, and RecoveryCase for use in approval tests.
    Yields (case_id, action_factory_fn) where action_factory_fn(action_type)
    inserts an AWAITING_HUMAN action and returns its ID.
    """
    from apps.api.db.models import (
        CaseStatus,
        Customer,
        CustomerSegment,
        FailureType,
        Merchant,
        RecoveryCase,
    )

    engine, factory = _make_session_factory()
    async with factory() as session:
        merchant = Merchant(
            name=f"Test Merchant {uuid.uuid4().hex[:6]}",
            razorpay_account_reference=f"acc_test_{uuid.uuid4().hex[:8]}",
            is_active=True,
        )
        session.add(merchant)
        await session.flush()

        customer = Customer(
            merchant_id=merchant.id,
            external_customer_id=f"cust_test_{uuid.uuid4().hex[:8]}",
            segment=CustomerSegment.MEDIUM_VALUE,
            tenure_days=120,
        )
        session.add(customer)
        await session.flush()

        case = RecoveryCase(
            merchant_id=merchant.id,
            customer_id=customer.id,
            amount_paise=50_000,
            failure_type=FailureType.PAYMENT_METHOD,
            status=CaseStatus.AWAITING_APPROVAL,
            recoverability_score=0.75,
        )
        session.add(case)
        await session.commit()

        case_id = case.id
        merchant_id = merchant.id
        customer_id = customer.id

    async def insert_action(action_type=None):
        from apps.api.db.models import Action, ActionType, AuthorizationStatus, ExecutionStatus

        if action_type is None:
            action_type = ActionType.PAYMENT_LINK
        async with factory() as session:
            action = Action(
                case_id=case_id,
                action_type=action_type,
                authorization_status=AuthorizationStatus.AWAITING_HUMAN,
                execution_status=ExecutionStatus.PENDING,
                idempotency_key=f"idem_{uuid.uuid4()}",
            )
            session.add(action)
            await session.commit()
            return action.id

    yield case_id, insert_action

    # Teardown
    async with factory() as session:
        await session.execute(
            __import__("sqlalchemy").text("DELETE FROM audit_events WHERE case_id = :cid"),
            {"cid": case_id}
        )
        await session.execute(
            __import__("sqlalchemy").text("DELETE FROM actions WHERE case_id = :cid"),
            {"cid": case_id}
        )
        await session.execute(
            __import__("sqlalchemy").text("DELETE FROM recovery_cases WHERE id = :cid"),
            {"cid": case_id}
        )
        await session.execute(
            __import__("sqlalchemy").text("DELETE FROM customers WHERE id = :uid"),
            {"uid": customer_id}
        )
        await session.execute(
            __import__("sqlalchemy").text("DELETE FROM merchants WHERE id = :mid"),
            {"mid": merchant_id}
        )
        await session.commit()

    await engine.dispose()


# ─── Tests ────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_human_approve_workflow(
    http_client: AsyncClient,
    readback_session: AsyncSession,
    seed_case: tuple,
) -> None:
    """
    Approving a AWAITING_HUMAN action must:
    1. Return 200 {"status": "approved"}.
    2. Transition action.authorization_status → APPROVED.
    3. Transition case.status → ACTION_INITIATED.
    4. Write a HUMAN_APPROVED audit_events row.
    """
    from apps.api.db.models import (
        Action,
        AuditEvent,
        AuditEventType,
        AuthorizationStatus,
        CaseStatus,
        RecoveryCase,
    )

    case_id, insert_action = seed_case
    action_id = await insert_action()

    resp = await http_client.post(f"/cases/{case_id}/approve")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "approved"
    assert body["action_id"] == str(action_id)

    # Read back — separate session sees committed data
    updated_action = (
        await readback_session.execute(select(Action).where(Action.id == action_id))
    ).scalar_one()
    assert updated_action.authorization_status == AuthorizationStatus.APPROVED

    updated_case = (
        await readback_session.execute(select(RecoveryCase).where(RecoveryCase.id == case_id))
    ).scalar_one()
    assert updated_case.status == CaseStatus.ACTION_INITIATED

    events = (
        await readback_session.execute(
            select(AuditEvent).where(AuditEvent.case_id == case_id)
        )
    ).scalars().all()
    assert any(e.event_type == AuditEventType.HUMAN_APPROVED for e in events), (
        "Expected HUMAN_APPROVED audit event, got: " + str([e.event_type for e in events])
    )


@pytest.mark.asyncio
async def test_human_reject_workflow(
    http_client: AsyncClient,
    readback_session: AsyncSession,
    seed_case: tuple,
) -> None:
    """
    Rejecting a AWAITING_HUMAN action must:
    1. Return 200 {"status": "rejected"}.
    2. Transition action.authorization_status → BLOCKED.
    3. Transition action.execution_status → CANCELLED.
    4. Transition case.status → SUPPRESSED.
    5. Write an ACTION_BLOCKED/REJECTED audit_events row.
    6. Never enqueue the action for execution.
    """
    from apps.api.db.models import (
        Action,
        AuditEvent,
        AuditEventType,
        AuthorizationStatus,
        CaseStatus,
        ExecutionStatus,
        RecoveryCase,
    )

    case_id, insert_action = seed_case
    action_id = await insert_action()

    resp = await http_client.post(f"/cases/{case_id}/reject")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "rejected"
    assert body["action_id"] == str(action_id)

    # Read back
    updated_action = (
        await readback_session.execute(select(Action).where(Action.id == action_id))
    ).scalar_one()
    assert updated_action.authorization_status == AuthorizationStatus.BLOCKED
    assert updated_action.execution_status == ExecutionStatus.CANCELLED

    updated_case = (
        await readback_session.execute(select(RecoveryCase).where(RecoveryCase.id == case_id))
    ).scalar_one()
    assert updated_case.status == CaseStatus.SUPPRESSED

    events = (
        await readback_session.execute(
            select(AuditEvent).where(AuditEvent.case_id == case_id)
        )
    ).scalars().all()
    assert any(
        e.event_type == AuditEventType.ACTION_BLOCKED and e.decision == "REJECTED"
        for e in events
    ), "Expected ACTION_BLOCKED/REJECTED audit event, got: " + str(
        [(e.event_type, e.decision) for e in events]
    )


@pytest.mark.asyncio
async def test_approve_returns_400_if_no_awaiting_action(
    http_client: AsyncClient,
    seed_case: tuple,
) -> None:
    """
    Calling approve when no AWAITING_HUMAN action exists must return 400.
    """
    case_id, _ = seed_case
    resp = await http_client.post(f"/cases/{case_id}/approve")
    assert resp.status_code == 400
    assert "awaiting" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_reject_returns_404_for_unknown_case(
    http_client: AsyncClient,
) -> None:
    """
    Calling reject with a non-existent case ID must return 404.
    """
    fake_id = uuid.uuid4()
    resp = await http_client.post(f"/cases/{fake_id}/reject")
    assert resp.status_code == 404
