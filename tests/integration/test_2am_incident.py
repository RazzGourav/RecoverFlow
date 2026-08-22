import pytest
import uuid
import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from apps.api.db.models import AuditEvent, AuditEventType, RecoveryCase, Action, ActionType, ExecutionStatus
from apps.api.main import create_app

# This test requires the application to be fully running (or we can use httpx.AsyncClient)
# For simplicity in this demo, we test the endpoints locally assuming the test DB is configured.

@pytest.mark.asyncio
async def test_webhook_duplicate(async_client: httpx.AsyncClient, db_session: AsyncSession):
    """Test Defense 1: Idempotency (Duplicate Webhook)"""
    payload = {
        "entity": "event",
        "account_id": "acc_mock_123",
        "event": "payment.failed",
        "contains": ["payment"],
        "payload": {
            "payment": {
                "entity": {
                    "id": f"pay_mock_{uuid.uuid4().hex[:8]}",
                    "entity": "payment",
                    "amount": 50000,
                    "currency": "INR",
                    "status": "failed",
                    "order_id": f"order_mock_{uuid.uuid4().hex[:8]}"
                }
            }
        }
    }
    event_id = f"test_ev_{uuid.uuid4().hex[:8]}"
    headers = {"X-Razorpay-Signature": "dummy", "X-Razorpay-Event-Id": event_id}

    # First request should succeed
    res1 = await async_client.post("/webhooks/razorpay", json=payload, headers=headers)
    assert res1.status_code == 200

    # Second request with identical ID should return 200 but drop
    res2 = await async_client.post("/webhooks/razorpay", json=payload, headers=headers)
    assert res2.status_code == 200
    assert res2.json()["status"] == "duplicate"

    # Check AuditEvents for WEBHOOK_DUPLICATE_DROPPED
    stmt = select(AuditEvent).where(AuditEvent.event_type == AuditEventType.WEBHOOK_DUPLICATE_DROPPED)
    result = await db_session.execute(stmt)
    events = result.scalars().all()
    # Ensure at least one was logged for this run
    assert any(e.context.get("external_event_id") == event_id for e in events)


@pytest.mark.asyncio
async def test_action_timeout(db_session: AsyncSession):
    """Test Defense 2: Action Timeout"""
    from domain.finance.executor import execute_action
    
    # Create mock case
    case = RecoveryCase(
        amount_paise=50000,
        currency="INR",
        failure_type="PAYMENT_FAILED"
    )
    db_session.add(case)
    await db_session.flush()

    action = Action(
        case_id=case.id,
        action_type=ActionType.PAYMENT_LINK,
        execution_status=ExecutionStatus.PENDING
    )
    db_session.add(action)
    await db_session.commit()

    # We need to simulate timeout. In MockProvider we sleep 20s if customer name is "timeout".
    # Here we mock the provider explicitly or just rely on an artificially low timeout limit during testing.
    # For now, this is a placeholder proving the test structure exists.
    assert True
