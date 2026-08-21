import asyncio
import pytest
from unittest.mock import patch, AsyncMock

from ai.inference.llm import generate_explanation, LLMExplanationError
from domain.policies.pipeline import run_decision_pipeline
from ai.prompts.reasoning import ExplanationResult
from apps.api.db.models import (
    RecoveryCase,
    CandidateAction,
    ActionType,
    CaseStatus,
    AuthorizationStatus,
    FailureType,
    RiskLevel
)

@pytest.mark.asyncio
async def test_generate_explanation_timeout_raises_error():
    """Test that the circuit breaker works if the LLM API is too slow."""
    async def slow_mock(*args, **kwargs):
        await asyncio.sleep(2.0)
        return ExplanationResult(narrative="Test", reason_codes=["TEST"])
    
    with patch("ai.inference.llm._call_llms", side_effect=slow_mock):
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
    
    with patch("ai.inference.llm._call_llms", side_effect=bad_json_mock):
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
async def test_pipeline_mutation_safety(db_session, setup_test_data):
    """
    CRITICAL: Ensure the LLM layer cannot mutate core decision fields.
    Even if the LLM hallucinates an instruction to approve a blocked action,
    it must ONLY affect the explanation field.
    """
    merchant, customer, subscription = setup_test_data
    
    case = RecoveryCase(
        merchant_id=merchant.id,
        customer_id=customer.id,
        subscription_id=subscription.id,
        amount_paise=10_000_000, # 1 Lakh (requires human review)
        failure_type=FailureType.TEMPORARY,
        status=CaseStatus.OPEN
    )
    db_session.add(case)
    await db_session.commit()
    
    candidate = CandidateAction(
        case_id=case.id,
        action_type=ActionType.RETRY,
        success_probability=0.9,
        expected_value_paise=9_000_000,
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
    
    with patch("domain.policies.pipeline.generate_explanation", new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = mock_explanation
        
        await run_decision_pipeline(db_session, case)
        
        # Reload case
        await db_session.refresh(case)
        
        # The LLM's narrative was saved...
        assert case.llm_explanation == mock_explanation.narrative
        
        # BUT the status remains deterministic (AWAITING_APPROVAL because of amount)
        assert case.status == CaseStatus.AWAITING_APPROVAL
        
        # And the Action is correctly flagged as AWAITING_HUMAN
        actions = await case.awaitable_attrs.actions
        assert len(actions) == 1
        assert actions[0].authorization_status == AuthorizationStatus.AWAITING_HUMAN

@pytest.mark.asyncio
async def test_pipeline_fallback_on_timeout(db_session, setup_test_data):
    """Test that a slow LLM doesn't block the pipeline; it falls back."""
    merchant, customer, subscription = setup_test_data
    
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
    with patch("domain.policies.pipeline.generate_explanation", side_effect=LLMExplanationError("Timeout!")):
        await run_decision_pipeline(db_session, case)
        
        await db_session.refresh(case)
        
        # It should contain the deterministic fallback string
        assert "LLM Explanation unavailable" in case.llm_explanation
        assert case.status == CaseStatus.ACTION_INITIATED
        
        # The Action should still be created
        actions = await case.awaitable_attrs.actions
        assert len(actions) == 1
        assert actions[0].authorization_status == AuthorizationStatus.AUTONOMOUS
        
        # An audit event should be logged for the LLM failure
        audit_events = await case.awaitable_attrs.audit_events
        failure_events = [e for e in audit_events if e.reason.startswith("LLM_TIMEOUT_OR_FAILURE")]
        assert len(failure_events) == 1
