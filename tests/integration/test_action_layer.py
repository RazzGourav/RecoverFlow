import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from apps.api.db.models import (
    Action,
    ActionType,
    AuthorizationStatus,
    ExecutionStatus,
)
from workers.recovery_worker.worker import dispatch_action_job, poll_pending_actions


@pytest.mark.asyncio
async def test_recovery_worker_poll_pending_actions(db_session, setup_test_case, monkeypatch):
    """
    Integration test: Creates an old PENDING action, runs the poll function,
    and verifies it gets executed.
    """
    case, customer, merchant = setup_test_case
    
    # Mock execute_action so we don't actually trigger the provider here,
    # but verify the worker queries correctly.
    executed_actions = []
    async def mock_execute_action(session, action_id):
        executed_actions.append(action_id)
        # Update status so it's visible in DB
        stmt = select(Action).where(Action.id == action_id)
        action = (await session.execute(stmt)).scalar_one()
        action.execution_status = ExecutionStatus.SUCCESS
        await session.commit()

    monkeypatch.setattr("workers.recovery_worker.worker.execute_action", mock_execute_action)
    
    # Create action older than 1 minute
    old_time = datetime.now(timezone.utc) - timedelta(minutes=2)
    action = Action(
        case_id=case.id,
        action_type=ActionType.PAYMENT_LINK,
        authorization_status=AuthorizationStatus.AUTONOMOUS,
        execution_status=ExecutionStatus.PENDING,
        idempotency_key=f"idem_{uuid.uuid4()}",
        created_at=old_time
    )
    db_session.add(action)
    await db_session.commit()
    
    # Run the cron function
    await poll_pending_actions({})
    
    assert len(executed_actions) == 1
    assert executed_actions[0] == action.id


@pytest.mark.asyncio
async def test_recovery_worker_dispatch_action(db_session, setup_test_case, monkeypatch):
    """
    Integration test: Verifies direct dispatch successfully calls execute_action.
    """
    case, _, _ = setup_test_case
    
    executed_actions = []
    async def mock_execute_action(session, action_id):
        executed_actions.append(action_id)

    monkeypatch.setattr("workers.recovery_worker.worker.execute_action", mock_execute_action)
    
    action = Action(
        case_id=case.id,
        action_type=ActionType.PAYMENT_LINK,
        authorization_status=AuthorizationStatus.AUTONOMOUS,
        execution_status=ExecutionStatus.PENDING,
        idempotency_key=f"idem_{uuid.uuid4()}",
    )
    db_session.add(action)
    await db_session.commit()
    
    await dispatch_action_job({}, str(action.id))
    
    assert len(executed_actions) == 1
    assert executed_actions[0] == action.id
