import uuid

import pytest
from integrations.mock.provider import MockProvider
from sqlalchemy import select

from apps.api.db.models import (
    Action,
    ActionType,
    AuditEvent,
    AuditEventType,
    AuthorizationStatus,
    ExecutionStatus,
)
from domain.recovery.executor import execute_action


# Patch get_provider to always return MockProvider for tests
@pytest.fixture(autouse=True)
def patch_provider(monkeypatch):
    monkeypatch.setattr("domain.recovery.executor.get_provider", lambda: MockProvider())


@pytest.mark.asyncio
async def test_execute_payment_link_success(db_session, setup_test_case):
    """
    Tests that a PENDING/AUTONOMOUS action successfully generates a Payment Link
    and transitions to SUCCESS.
    """
    case, customer, merchant = setup_test_case
    
    action = Action(
        case_id=case.id,
        action_type=ActionType.PAYMENT_LINK,
        authorization_status=AuthorizationStatus.AUTONOMOUS,
        execution_status=ExecutionStatus.PENDING,
        idempotency_key=f"idem_{uuid.uuid4()}"
    )
    db_session.add(action)
    await db_session.commit()
    
    # Execute
    updated_action = await execute_action(db_session, action.id)
    
    # Assert Action State
    assert updated_action.execution_status == ExecutionStatus.SUCCESS
    assert updated_action.provider_reference.startswith("plink_mock_")
    
    # Assert Audit Log
    stmt = select(AuditEvent).where(AuditEvent.case_id == case.id, AuditEvent.event_type == AuditEventType.ACTION_EXECUTED)
    result = await db_session.execute(stmt)
    audit_event = result.scalar_one()
    
    assert audit_event.reason == "Successfully generated payment link."
    assert audit_event.metadata_payload["provider_reference"] == updated_action.provider_reference


@pytest.mark.asyncio
async def test_execute_action_invalid_state(db_session, setup_test_case):
    """
    Tests that a blocked or non-pending action raises an error and is not executed.
    """
    case, _, _ = setup_test_case
    
    action = Action(
        case_id=case.id,
        action_type=ActionType.PAYMENT_LINK,
        authorization_status=AuthorizationStatus.BLOCKED,
        execution_status=ExecutionStatus.PENDING,
        idempotency_key=f"idem_{uuid.uuid4()}"
    )
    db_session.add(action)
    await db_session.commit()
    
    with pytest.raises(ValueError, match="is not authorized for execution"):
        await execute_action(db_session, action.id)
