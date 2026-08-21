import uuid
import pytest
from httpx import AsyncClient

from apps.api.db.models import Action, ActionType, AuthorizationStatus, ExecutionStatus


@pytest.mark.asyncio
async def test_human_approval_flow(test_app, db_session, setup_test_case):
    """
    Tests the POST /cases/{id}/approve endpoint for human-in-the-loop actions.
    """
    case, _, _ = setup_test_case
    
    # Create action awaiting human approval
    action = Action(
        case_id=case.id,
        action_type=ActionType.PAYMENT_LINK,
        authorization_status=AuthorizationStatus.AWAITING_HUMAN,
        execution_status=ExecutionStatus.PENDING,
        idempotency_key=f"idem_{uuid.uuid4()}"
    )
    db_session.add(action)
    await db_session.commit()
    
    async with AsyncClient(app=test_app, base_url="http://test") as client:
        # Approve it
        response = await client.post(f"/cases/{action.id}/approve")
        
    assert response.status_code == 200
    assert response.json() == {"status": "approved", "action_id": str(action.id)}
    
    # Refresh action
    await db_session.refresh(action)
    assert action.authorization_status == AuthorizationStatus.APPROVED
    
    # The actual execution job will have been enqueued, but we won't execute it
    # here since we are just testing the endpoint


@pytest.mark.asyncio
async def test_human_rejection_flow(test_app, db_session, setup_test_case):
    """
    Tests the POST /cases/{id}/reject endpoint.
    """
    case, _, _ = setup_test_case
    
    action = Action(
        case_id=case.id,
        action_type=ActionType.PAYMENT_LINK,
        authorization_status=AuthorizationStatus.AWAITING_HUMAN,
        execution_status=ExecutionStatus.PENDING,
        idempotency_key=f"idem_{uuid.uuid4()}"
    )
    db_session.add(action)
    await db_session.commit()
    
    async with AsyncClient(app=test_app, base_url="http://test") as client:
        response = await client.post(f"/cases/{action.id}/reject")
        
    assert response.status_code == 200
    assert response.json() == {"status": "rejected", "action_id": str(action.id)}
    
    await db_session.refresh(action)
    assert action.authorization_status == AuthorizationStatus.BLOCKED
    assert action.execution_status == ExecutionStatus.CANCELLED
