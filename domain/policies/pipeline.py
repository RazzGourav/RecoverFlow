"""
Decision Pipeline Orchestrator

Why this exists:
  Wires together the Phase 3 ML Inference and the Phase 4 Policy Engine.
  Takes a newly generated RecoveryCase, extracts context, runs AI predictions,
  ranks candidates, evaluates policies, and saves the final Action and AuditEvent.
"""

import structlog
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ai.features.engineer import ACTION_TYPES
from ai.inference.predict import analyze_case
from db.models import (
    Action,
    ActionType,
    AuditEventType,
    AuthorizationStatus,
    CandidateAction,
    CaseStatus,
    ExecutionStatus,
    Policy,
    RecoveryCase,
    RiskLevel,
)
from domain.audit.logger import log_decision
from domain.policies.engine import OUTCOME_AUTONOMOUS, OUTCOME_BLOCKED, evaluate_action
from domain.recovery.ranking import rank_candidate_actions
from domain.risk.firewall import (
    RiskOutcome,
    compose_with_policy_decision,
    evaluate_risk_firewall,
)


def build_case_context(case: RecoveryCase) -> dict[str, Any]:
    """Helper to map a RecoveryCase to the raw dictionary expected by ML."""
    # In a fully fleshed out system, we would join with Customer and Subscription here.
    return {
        "case_id": str(case.id),
        "amount_paise": case.amount_paise,
        "failure_type": case.failure_type.value if hasattr(case.failure_type, 'value') else str(case.failure_type),
        "segment": "UNKNOWN",  # Default if no customer context
        "tenure_days": 0,
        "high_frequency_contact": False,
        "requires_human_review": False
    }


async def run_decision_pipeline(session: AsyncSession, case: RecoveryCase, force_action: ActionType | None = None) -> None:
    """
    Executes the decision logic for a RecoveryCase.
    """
    import structlog
    structlog.contextvars.bind_contextvars(case_id=str(case.id), model_version="v0.1.0-alpha")
    
    # TESTING HOOK: Force ActionType based on amount_paise ones digit
    import os
    if os.environ.get("FORCE_ACTION_TYPE_FOR_TESTING") == "1":
        amount_int = int(case.amount_paise)
        logger = structlog.get_logger(__name__)
        logger.info(f"TESTING HOOK: amount_paise={amount_int}, modulo={amount_int % 10}")
        if amount_int % 10 != 0:
            index = (amount_int % 10) - 1
            action_list = ["RETRY", "PAYMENT_LINK", "INVOICE", "PAYMENT_METHOD_UPDATE", "REMINDER", "HUMAN_ESCALATION", "NO_ACTION"]
            if 0 <= index < len(action_list):
                force_action = ActionType(action_list[index])
                logger.info(f"TESTING HOOK: Forcing action to {force_action.value}")
    
    case.status = CaseStatus.ANALYZING
    await session.flush()
    
    # 1. Fetch Policy (use the merchant's policy, fallback to first policy in system)
    policy_query = select(Policy)
    if case.merchant_id:
        policy_query = policy_query.where(Policy.merchant_id == case.merchant_id)
        
    result = await session.execute(policy_query)
    policy = result.scalars().first()
    
    if not policy:
        import structlog
        structlog.get_logger(__name__).warning("No active policy found. Using default system policy.")
        policy_config = {
            "max_autonomous_amount_paise": 500_000,
            "human_review_threshold_paise": 2_500_000,
            "confidence_threshold": 0.80,
            "retry_limit": 2,
            "cooldown_hours": 12,
            "max_contacts_per_72h": 2
        }
        policy_version = "default_1.0"
    else:
        policy_config = {
            "max_autonomous_amount_paise": policy.max_autonomous_amount_paise,
            "human_review_threshold_paise": policy.human_review_threshold_paise,
            "confidence_threshold": policy.confidence_threshold,
            "retry_limit": policy.retry_limit,
            "cooldown_hours": policy.cooldown_hours,
            "max_contacts_per_72h": policy.max_contacts_per_72h
        }
        policy_version = policy.version
    
    # 2. Extract context & run AI (Phase 3)
    case_context = build_case_context(case)
    # The analyze_case function evaluates all candidate actions and returns the best.
    # We actually want the probabilities for ALL actions to rank them, so we will 
    # directly call the models or extract from the contract.
    # Wait, the contract only gives us the best action. Let's modify the local logic
    # to evaluate all candidates directly here to populate ranking, or just re-import ML models.
    # For Phase 4, we will re-calculate expected values manually using the ML model.
    # Note: AI inference functions are synchronous because they use Scikit-Learn/XGBoost.
    
    import pandas as pd

    from ai.features.engineer import build_features
    from ai.inference import predict
    
    predict.load_models()
    decision_contract = analyze_case(case_context)
    
    # Generate action probabilities mapping
    df = pd.DataFrame([case_context])
    X_base = build_features(df)
    
    action_probs = {}
    for a in ACTION_TYPES:
        X_action = X_base.copy()
        for act in ACTION_TYPES:
            X_action[f"action_{act}"] = 1 if act == a else 0
        prob = float(predict._intervention_model.predict_proba(X_action)[0, 1])
        action_probs[a] = prob
        
    # 3. Expected Value Ranking (Phase 4)
    ranked_actions = rank_candidate_actions(case.amount_paise, action_probs)
    
    # Persist CandidateActions
    db_candidates = []
    for ra in ranked_actions:
        db_c = CandidateAction(
            case_id=case.id,
            action_type=ActionType(ra.action_type),
            success_probability=ra.success_probability,
            expected_value_paise=int(ra.expected_value_paise),
            risk_level=RiskLevel(decision_contract.risk_level),
            rank=ra.rank
        )
        db_candidates.append(db_c)
        session.add(db_c)
        
    # 4. Fetch case history for policy evaluation
    # How many past actions on this case?
    past_actions_res = await session.execute(
        select(func.count(Action.id)).where(Action.case_id == case.id)
    )
    past_actions_count = past_actions_res.scalar() or 0
    
    # Last action time
    last_action_res = await session.execute(
        select(Action.created_at)
        .where(Action.case_id == case.id)
        .order_by(Action.created_at.desc())
        .limit(1)
    )
    last_action_time = last_action_res.scalar()
    
    print(f"DEBUG: last_action_time={last_action_time}, past_actions_count={past_actions_count}")
    
    history_context = {
        "past_actions_count": past_actions_count,
        "last_action_time": last_action_time,
        "contacts_in_last_72h": 0  # In a real app, query past 72h contacts across case/customer
    }
    
    # 5. Evaluate strict Policy Rules against the top-ranked action
    if force_action:
        best_candidate = next((c for c in ranked_actions if c.action_type == force_action.value), ranked_actions[0])
    else:
        best_candidate = ranked_actions[0]
    
    status, reason = evaluate_action(
        action_type=best_candidate.action_type,
        confidence=best_candidate.success_probability,
        amount_paise=case.amount_paise,
        policy_config=policy_config,
        case_history=history_context,
        current_time=datetime.now(timezone.utc)
    )
    
    # 5b. Risk Firewall (PRD Module D) — defense-only layer
    # Runs AFTER Policy Engine to compose (not replace) its decision.
    # Firewall can only make the result MORE restrictive, never less.
    firewall_result = evaluate_risk_firewall(
        # Check 1 — Transaction risk
        is_duplicate=False,  # Handled at webhook ingestion layer; here assume clean
        is_stale=False,
        failure_type=case.failure_type.value if hasattr(case.failure_type, "value") else str(case.failure_type),
        past_failed_attempts=history_context["past_actions_count"],
        # Check 2 — Frequency risk
        contacts_in_last_72h=history_context.get("contacts_in_last_72h", 0),
        actions_in_last_24h=history_context["past_actions_count"],
        # Check 3 — Amount risk
        amount_paise=case.amount_paise,
        autonomous_threshold_paise=policy_config.get("max_autonomous_amount_paise", 500_000),
        review_threshold_paise=policy_config.get("human_review_threshold_paise", 2_500_000),
        # Check 4 — Behavioral anomaly
        tenure_days=0,           # Populated from Customer in a future phase
        typical_amount_paise=case.amount_paise,   # No historical data yet; use current
        segment="UNKNOWN",
        # Check 5 — Policy violation
        action_type=best_candidate.action_type,
        allowed_action_types=[a.value for a in ActionType],  # Merchant's full allowlist
        merchant_is_active=True,
        action_requires_human_approval=(status != OUTCOME_AUTONOMOUS),
        current_authorization_status=status,
    )
    
    # Compose: take the stricter of policy engine + risk firewall outcomes
    composed_status = compose_with_policy_decision(firewall_result.outcome, status)
    
    # Log the Risk Firewall audit event (distinct reason code "RISK_*")
    rf_event_type = (
        AuditEventType.RISK_FIREWALL_BLOCKED
        if firewall_result.outcome == RiskOutcome.BLOCK
        else AuditEventType.RISK_FIREWALL_EVALUATED
    )
    await log_decision(
        session=session,
        case_id=str(case.id),
        action_type=best_candidate.action_type,
        decision=firewall_result.outcome.value,
        reason=firewall_result.primary_reason,
        model_version=decision_contract.model_version,
        policy_version=policy_version,
        event_type=rf_event_type,
        context={
            "firewall_score": firewall_result.overall_score,
            "triggered_reasons": firewall_result.triggered_reasons,
        },
    )
    
    # Use composed_status for the final action authorization.
    # Reason attribution:
    #   - If the firewall produced BLOCK, the firewall is the deciding factor → use firewall reason.
    #   - If the firewall produced REVIEW or ALLOW, the policy engine's reason is still authoritative
    #     because the firewall only added a constraint on top; the original policy decision text
    #     (e.g. POLICY_COOLDOWN_ACTIVE) is what tells the human reviewer WHY the case was blocked.
    status = composed_status
    if firewall_result.outcome == RiskOutcome.BLOCK:
        reason = firewall_result.primary_reason
    # else: keep the original policy engine reason

    # Map rule engine outcome to AuthorizationStatus
    auth_status = AuthorizationStatus.AWAITING_HUMAN
    if status == OUTCOME_AUTONOMOUS:
        auth_status = AuthorizationStatus.AUTONOMOUS
    elif status == OUTCOME_BLOCKED:
        auth_status = AuthorizationStatus.BLOCKED
        
    # 6. Save Action
    idempotency_key = f"action_{case.id}_{best_candidate.action_type}_{past_actions_count}"
    
    action = Action(
        case_id=case.id,
        action_type=ActionType(best_candidate.action_type),
        authorization_status=auth_status,
        execution_status=ExecutionStatus.PENDING if auth_status != AuthorizationStatus.BLOCKED else ExecutionStatus.CANCELLED,
        idempotency_key=idempotency_key
    )
    session.add(action)
    
    # Update Case
    case.recoverability_score = decision_contract.recoverability
    case.risk_score = decision_contract.risk_score
    case.risk_level = RiskLevel(decision_contract.risk_level)
    case.model_version = decision_contract.model_version
    case.status = CaseStatus.AWAITING_APPROVAL if auth_status == AuthorizationStatus.AWAITING_HUMAN else CaseStatus.ACTION_INITIATED
    if auth_status == AuthorizationStatus.BLOCKED:
        case.status = CaseStatus.OPEN  # Or some blocked state
        
    # 7. LLM Reasoning Layer (Phase 5)
    # This executes strictly AFTER the deterministic policy engine has set the action status.
    from ai.inference.llm import LLMExplanationError, generate_explanation
    
    llm_context = {}
    try:
        explanation_result = await generate_explanation(
            amount_paise=case.amount_paise,
            failure_type=case.failure_type.value,
            recoverability_score=decision_contract.recoverability,
            risk_level=decision_contract.risk_level,
            action_type=best_candidate.action_type,
            authorization_status=auth_status.value,
            reason=reason
        )
        case.llm_explanation = explanation_result.narrative
        llm_context["llm_reason_codes"] = explanation_result.reason_codes
    except LLMExplanationError as e:
        # Fallback to deterministic template so pipeline never blocks
        case.llm_explanation = f"Action {best_candidate.action_type} evaluated to {auth_status.value} due to {reason}. (LLM Explanation unavailable)"
        await log_decision(
            session=session,
            case_id=str(case.id),
            action_type=best_candidate.action_type,
            decision=status,
            reason=f"LLM_TIMEOUT_OR_FAILURE: {e!s}",
            model_version=decision_contract.model_version,
            policy_version=policy_version,
            event_type=AuditEventType.LLM_EXPLANATION_FAILED,
            context={"error": str(e)}
        )
        
    # 8. Audit Log
    context_data = {
        "expected_value_paise": best_candidate.expected_value_paise,
        "confidence": best_candidate.success_probability,
        "risk_level": decision_contract.risk_level
    }
    context_data.update(llm_context)
    
    await log_decision(
        session=session,
        case_id=str(case.id),
        action_type=best_candidate.action_type,
        decision=status,
        reason=reason,
        model_version=decision_contract.model_version,
        policy_version=policy_version,
        context=context_data
    )

    # 9. Enqueue Execution (Phase 7)
    if auth_status == AuthorizationStatus.AUTONOMOUS:
        from arq import create_pool
        from arq.connections import RedisSettings
        from config import settings
        
        try:
            pool = await create_pool(RedisSettings.from_dsn(settings.redis_url))
            await pool.enqueue_job("dispatch_action_job", action_id=str(action.id), _queue_name="arq:recovery_queue")
            await pool.close()
        except Exception as e:
            import structlog
            logger = structlog.get_logger(__name__)
            logger.error("pipeline.enqueue_action.failed", action_id=str(action.id), error=str(e))
            # Safe to ignore; the recovery_worker cron job will pick up any PENDING actions automatically.
