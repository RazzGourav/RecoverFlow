import uuid
import asyncio
import pytest
from unittest.mock import AsyncMock

from integrations.integrations.mock.provider import MockProvider
from sqlalchemy import select

from apps.api.db.models import (
    Action,
    ActionType,
    AuditEvent,
    AuditEventType,
    AuthorizationStatus,
    ExecutionStatus,
)
from domain.finance.executor import execute_action


# Patch get_provider to always return MockProvider for tests
@pytest.fixture(autouse=True)
def patch_provider(monkeypatch):
    monkeypatch.setattr("domain.finance.executor.get_provider", lambda: MockProvider())


@pytest.mark.asyncio
async def test_execute_payment_link_success(db_session, setup_test_case):
    """
    Tests that a PENDING/AUTONOMOUS action successfully generates a Payment Link
    and transitions to EXECUTED.
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
    assert updated_action.execution_status == ExecutionStatus.EXECUTED
    assert updated_action.provider_reference.startswith("plink_mock_")
    
    # Assert Audit Log
    stmt = select(AuditEvent).where(AuditEvent.case_id == case.id, AuditEvent.event_type == AuditEventType.ACTION_EXECUTED)
    result = await db_session.execute(stmt)
    audit_events = result.scalars().all()
    assert len(audit_events) > 0
    
    audit_event = audit_events[-1]
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


@pytest.mark.asyncio
async def test_execute_action_idempotency(db_session, setup_test_case, monkeypatch):
    """
    Tests that re-executing an already EXECUTED action does not call the provider again.
    """
    case, _, _ = setup_test_case
    
    mock_provider = MockProvider()
    mock_provider.create_payment_link = AsyncMock(return_value="plink_mock_123")
    monkeypatch.setattr("domain.finance.executor.get_provider", lambda: mock_provider)
    
    action = Action(
        case_id=case.id,
        action_type=ActionType.PAYMENT_LINK,
        authorization_status=AuthorizationStatus.AUTONOMOUS,
        execution_status=ExecutionStatus.PENDING,
        idempotency_key=f"idem_{uuid.uuid4()}"
    )
    db_session.add(action)
    await db_session.commit()
    
    # First execution
    await execute_action(db_session, action.id)
    assert mock_provider.create_payment_link.call_count == 1
    
    # Second execution (should be a no-op due to idempotency)
    await execute_action(db_session, action.id)
    
    # Still 1 provider call
    assert mock_provider.create_payment_link.call_count == 1


@pytest.mark.asyncio
async def test_execute_action_timeout(db_session, setup_test_case, monkeypatch):
    """
    Tests that a provider timeout transitions the action to TIMED_OUT.
    """
    case, _, _ = setup_test_case
    
    mock_provider = MockProvider()
    mock_provider.create_payment_link = AsyncMock(side_effect=asyncio.TimeoutError)
    monkeypatch.setattr("domain.finance.executor.get_provider", lambda: mock_provider)
    
    action = Action(
        case_id=case.id,
        action_type=ActionType.PAYMENT_LINK,
        authorization_status=AuthorizationStatus.AUTONOMOUS,
        execution_status=ExecutionStatus.PENDING,
        idempotency_key=f"idem_{uuid.uuid4()}"
    )
    db_session.add(action)
    await db_session.commit()
    
    updated_action = await execute_action(db_session, action.id)
    assert updated_action.execution_status == ExecutionStatus.TIMED_OUT


@pytest.mark.asyncio
async def test_validation_layer_race_condition(db_session, setup_test_case, monkeypatch):
    """
    Simulates a race condition where DB state indicates a failed payment, but the live 
    state fetch indicates it is already paid. The action should be VALIDATION_BLOCKED.
    """
    case, _, _ = setup_test_case
    
    mock_provider = MockProvider()
    # Mock live state saying it's captured
    mock_provider.fetch_payment = AsyncMock(return_value={"status": "captured"})
    # create_payment_link should never be called
    mock_provider.create_payment_link = AsyncMock(return_value="should_not_call")
    
    monkeypatch.setattr("domain.finance.executor.get_provider", lambda: mock_provider)
    
    action = Action(
        case_id=case.id,
        action_type=ActionType.PAYMENT_LINK,
        authorization_status=AuthorizationStatus.AUTONOMOUS,
        execution_status=ExecutionStatus.PENDING,
        idempotency_key=f"idem_{uuid.uuid4()}"
    )
    db_session.add(action)
    await db_session.commit()
    
    updated_action = await execute_action(db_session, action.id)
    
    assert updated_action.execution_status == ExecutionStatus.VALIDATION_BLOCKED
    assert mock_provider.create_payment_link.call_count == 0


@pytest.mark.asyncio
async def test_validation_layer_unsupported(db_session, setup_test_case, monkeypatch):
    """
    Tests that an unsupported live state correctly routes to VALIDATION_BLOCKED.
    """
    case, _, _ = setup_test_case
    
    mock_provider = MockProvider()
    # Force UNSUPPORTED validation
    mock_provider.fetch_payment = AsyncMock(return_value={"_mock_validation_override": "UNSUPPORTED"})
    
    monkeypatch.setattr("domain.finance.executor.get_provider", lambda: mock_provider)
    
    action = Action(
        case_id=case.id,
        action_type=ActionType.PAYMENT_LINK,
        authorization_status=AuthorizationStatus.AUTONOMOUS,
        execution_status=ExecutionStatus.PENDING,
        idempotency_key=f"idem_{uuid.uuid4()}"
    )
    db_session.add(action)
    await db_session.commit()
    
    updated_action = await execute_action(db_session, action.id)
    
    assert updated_action.execution_status == ExecutionStatus.VALIDATION_BLOCKED
