import uuid
import pytest
from unittest.mock import AsyncMock

from apps.api.db.models import Action, ActionType, AuthorizationStatus, ExecutionStatus, ReconciliationStatus, ReconciliationRecord
from domain.finance.reconciliation import reconcile_action
from integrations.integrations.mock.provider import MockProvider


@pytest.fixture
async def executed_action(db_session, setup_test_case):
    case, _, _ = setup_test_case
    action = Action(
        case_id=case.id,
        action_type=ActionType.PAYMENT_LINK,
        authorization_status=AuthorizationStatus.AUTONOMOUS,
        execution_status=ExecutionStatus.EXECUTED,
        provider_reference="plink_mock_123",
        idempotency_key=f"idem_{uuid.uuid4()}"
    )
    db_session.add(action)
    await db_session.commit()
    return action


@pytest.mark.asyncio
async def test_reconcile_matched(db_session, executed_action, monkeypatch):
    case = executed_action.case
    
    mock_provider = MockProvider()
    mock_provider.fetch_payment_link = AsyncMock(return_value={
        "status": "paid",
        "amount_paid": case.amount_paise
    })
    mock_provider.fetch_payment = AsyncMock(return_value={"status": "failed"})
    monkeypatch.setattr("domain.finance.reconciliation.get_provider", lambda: mock_provider)
    
    record = await reconcile_action(db_session, executed_action.id)
    
    assert record.status == ReconciliationStatus.MATCHED
    assert record.expected_amount_paise == case.amount_paise
    assert record.actual_amount_paise == case.amount_paise


@pytest.mark.asyncio
async def test_reconcile_partial(db_session, executed_action, monkeypatch):
    case = executed_action.case
    
    mock_provider = MockProvider()
    mock_provider.fetch_payment_link = AsyncMock(return_value={
        "status": "paid",
        "amount_paid": case.amount_paise - 100
    })
    mock_provider.fetch_payment = AsyncMock(return_value={"status": "failed"})
    monkeypatch.setattr("domain.finance.reconciliation.get_provider", lambda: mock_provider)
    
    record = await reconcile_action(db_session, executed_action.id)
    
    assert record.status == ReconciliationStatus.PARTIAL
    assert record.actual_amount_paise == case.amount_paise - 100
    assert "Expected" in record.exception_reason


@pytest.mark.asyncio
async def test_reconcile_exception_stale_webhook(db_session, executed_action, monkeypatch):
    case = executed_action.case
    
    mock_provider = MockProvider()
    # The action was "successful"
    mock_provider.fetch_payment_link = AsyncMock(return_value={
        "status": "paid",
        "amount_paid": case.amount_paise
    })
    # But the original payment was already captured (stale webhook defense)
    mock_provider.fetch_payment = AsyncMock(return_value={"status": "captured"})
    monkeypatch.setattr("domain.finance.reconciliation.get_provider", lambda: mock_provider)
    
    record = await reconcile_action(db_session, executed_action.id)
    
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_metrics_api(db_session, test_app, executed_action):
    # Create some reconciliation records
    case = executed_action.case
    record1 = ReconciliationRecord(
        case_id=case.id,
        action_id=executed_action.id,
        expected_amount_paise=1000,
        actual_amount_paise=1000,
        status=ReconciliationStatus.MATCHED
    )
    record2 = ReconciliationRecord(
        case_id=case.id,
        action_id=executed_action.id,
        expected_amount_paise=2000,
        actual_amount_paise=1500,
        status=ReconciliationStatus.PARTIAL
    )
    record3 = ReconciliationRecord(
        case_id=case.id,
        action_id=executed_action.id,
        expected_amount_paise=1000,
        actual_amount_paise=0,
        status=ReconciliationStatus.EXCEPTION
    )
    db_session.add_all([record1, record2, record3])
    await db_session.commit()
    
    async with AsyncClient(app=test_app, base_url="http://test") as client:
        response = await client.get("/metrics/")
        
    assert response.status_code == 200
    data = response.json()
    assert data["incremental_recovered_revenue_paise"] == 2500
    assert data["recovery_rate_percent"] == 62.5  # 2500 / 4000 = 62.5%
    assert data["reconciliation_exception_rate_percent"] == 33.33  # 1 / 3

