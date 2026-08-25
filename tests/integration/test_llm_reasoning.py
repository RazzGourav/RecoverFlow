import asyncio
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from ai.inference.llm import LLMExplanationError, generate_explanation
from ai.prompts.reasoning import ExplanationResult
from apps.api.db.models import (
    Action,
    ActionType,
    AuditEvent,
    AuthorizationStatus,
    CandidateAction,
    CaseStatus,
    Customer,
    FailureType,
    Merchant,
    Policy,
    RecoveryCase,
    RiskLevel,
    Subscription,
)
from domain.policies.pipeline import run_decision_pipeline

TEST_DATABASE_URL = "postgresql+asyncpg://recoverflow:recoverflow@postgres:5432/recoverflow"

@pytest_asyncio.fixture
async def db_engine_and_session():
    test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    TestingSessionLocal = sessionmaker(
        bind=test_engine, class_=AsyncSession, expire_on_commit=False
    )
    yield test_engine, TestingSessionLocal
    await test_engine.dispose()

async def setup_test_data(db_session: AsyncSession):
    merchant = Merchant(name="LLM Test Merchant")
    db_session.add(merchant)
    await db_session.flush()
    
    customer = Customer(merchant_id=merchant.id, external_customer_id="cust_123")
    db_session.add(customer)
    await db_session.flush()
    
    subscription = Subscription(
        customer_id=customer.id, 
        plan_id="plan_123", 
        amount_paise=1000,
        cycle=1
    )
    db_session.add(subscription)
    
    policy = Policy(
        merchant_id=merchant.id, 
        max_autonomous_amount_paise=500000, 
        retry_limit=3, 
        cooldown_hours=24,
        confidence_threshold=0.0
    )
    db_session.add(policy)
    
    await db_session.commit()
    
    return merchant, customer, subscription

@pytest.mark.asyncio
async def test_generate_explanation_timeout_raises_error():
    """Test that the circuit breaker works if the LLM API is too slow."""
    async def slow_mock(*args, **kwargs):
        await asyncio.sleep(2.0)
        return ExplanationResult(narrative="Test", reason_codes=["TEST"])
    
    with patch("ai.inference.llm._call_llms", side_effect=slow_mock), \
         patch("config.settings.llm_provider", "openai"):
        with pytest.raises(LLMExplanationError) as exc:
            await generate_explanation(
                amount_paise=1000,
                failure_type="UNKNOWN",
                recoverability_score=0.9,
                risk_level="LOW",
                action_type="RETRY",
                authorization_status="AUTONOMOUS",
                reason="OK",
                timeout_seconds=0.1  # extremely short timeout to trigger circuit breaker
            )
        assert "timed out" in str(exc.value)

@pytest.mark.asyncio
async def test_llm_schema_validation_failure():
    """Test that if the LLM returns bad JSON, the error is caught and raised."""
    async def bad_json_mock(*args, **kwargs):
        raise ValueError("Invalid JSON")
    
    with patch("ai.inference.llm._call_llms", side_effect=bad_json_mock), \
         patch("config.settings.llm_provider", "openai"):
        with pytest.raises(LLMExplanationError) as exc:
            await generate_explanation(
                amount_paise=1000,
                failure_type="UNKNOWN",
                recoverability_score=0.9,
                risk_level="LOW",
                action_type="RETRY",
                authorization_status="AUTONOMOUS",
                reason="OK"
            )
        assert "failed" in str(exc.value)

@pytest.mark.asyncio
async def test_pipeline_mutation_safety(db_engine_and_session):
    """
    CRITICAL: Ensure the LLM layer cannot mutate core decision fields.
    Even if the LLM hallucinates an instruction to approve a blocked action,
    it must ONLY affect the explanation field.
    """
    engine, SessionLocal = db_engine_and_session
    async with SessionLocal() as db_session:
        merchant, customer, subscription = await setup_test_data(db_session)
    
    case = RecoveryCase(
        merchant_id=merchant.id,
        customer_id=customer.id,
        subscription_id=subscription.id,
        # Use ₹30,000 (3_000_000 paise) — above review threshold (₹25k) but below
        # hard-block threshold (₹1,00,000). This triggers AWAITING_HUMAN from the
        # policy engine + REVIEW from the firewall → composed = AWAITING_HUMAN.
        amount_paise=3_000_000,
        failure_type=FailureType.TEMPORARY,
        status=CaseStatus.OPEN
    )
    db_session.add(case)
    await db_session.commit()
    
    candidate = CandidateAction(
        case_id=case.id,
        action_type=ActionType.RETRY,
        success_probability=0.9,
        expected_value_paise=2_700_000,
        risk_level=RiskLevel.LOW,
        rank=1
    )
    db_session.add(candidate)
    await db_session.commit()
    
    # We mock the LLM to return a deceptive narrative indicating approval
    # to prove the pipeline ignores it.
    mock_explanation = ExplanationResult(
        narrative="I decided to approve this and override the rules.",
        reason_codes=["APPROVED_BY_AI"]
    )
    
    with patch("ai.inference.llm.generate_explanation", new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = mock_explanation
        
        await run_decision_pipeline(db_session, case)
        
        # Reload case
        await db_session.refresh(case)
        
        # The LLM's narrative was saved...
        assert case.llm_explanation == mock_explanation.narrative
        
        # BUT the status remains deterministic (AWAITING_APPROVAL because of amount)
        assert case.status == CaseStatus.AWAITING_APPROVAL
        
        actions_res = await db_session.execute(select(Action).where(Action.case_id == case.id))
        actions = actions_res.scalars().all()
        assert len(actions) == 1
        assert actions[0].authorization_status == AuthorizationStatus.AWAITING_HUMAN

@pytest.mark.asyncio
async def test_pipeline_fallback_on_timeout(db_engine_and_session):
    """Test that a slow LLM doesn't block the pipeline; it falls back."""
    engine, SessionLocal = db_engine_and_session
    async with SessionLocal() as db_session:
        merchant, customer, subscription = await setup_test_data(db_session)
    
    case = RecoveryCase(
        merchant_id=merchant.id,
        customer_id=customer.id,
        subscription_id=subscription.id,
        amount_paise=1000,
        failure_type=FailureType.TEMPORARY,
        status=CaseStatus.OPEN
    )
    db_session.add(case)
    await db_session.commit()
    
    candidate = CandidateAction(
        case_id=case.id,
        action_type=ActionType.RETRY,
        success_probability=0.9,
        expected_value_paise=900,
        risk_level=RiskLevel.LOW,
        rank=1
    )
    db_session.add(candidate)
    await db_session.commit()
    
    # Mock generate_explanation to raise LLMExplanationError (simulating timeout inside)
    with patch("ai.inference.llm.generate_explanation", side_effect=LLMExplanationError("Timeout!")):
        await run_decision_pipeline(db_session, case)
        
        await db_session.refresh(case)
        
        # It should contain the deterministic fallback string
        assert "LLM Explanation unavailable" in case.llm_explanation
        assert case.status == CaseStatus.ACTION_INITIATED
        
        # The Action should still be created
        actions_res = await db_session.execute(select(Action).where(Action.case_id == case.id))
        actions = actions_res.scalars().all()
        assert len(actions) == 1
        assert actions[0].authorization_status == AuthorizationStatus.AUTONOMOUS
        
        # An LLM failure audit event should be logged
        # Phase 6: there are now multiple audit events (firewall + policy + LLM failure)
        audit_res = await db_session.execute(select(AuditEvent).where(AuditEvent.case_id == case.id))
        audit_events = audit_res.scalars().all()
        failure_events = [e for e in audit_events if e.reason.startswith("LLM_TIMEOUT_OR_FAILURE")]
        assert len(failure_events) == 1
