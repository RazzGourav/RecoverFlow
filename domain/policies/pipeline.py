"""
Decision Pipeline Orchestrator

Why this exists:
  Wires together the Phase 3 ML Inference and the Phase 4 Policy Engine.
  Takes a newly generated RecoveryCase, extracts context, runs AI predictions,
  ranks candidates, evaluates policies, and saves the final Action and AuditEvent.
"""

from typing import Any, Dict
from datetime import datetime, timezone
import uuid
import json

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from apps.api.db.models import (
    RecoveryCase, 
    Policy, 
    Action, 
    CandidateAction, 
    ActionType,
    CaseStatus,
    AuthorizationStatus,
    ExecutionStatus,
    RiskLevel
)
from ai.inference.predict import analyze_case
from ai.features.engineer import ACTION_TYPES
from domain.recovery.ranking import rank_candidate_actions
from domain.policies.engine import evaluate_action, OUTCOME_AUTONOMOUS, OUTCOME_HUMAN, OUTCOME_BLOCKED
from domain.audit.logger import log_decision


def build_case_context(case: RecoveryCase) -> Dict[str, Any]:
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


async def run_decision_pipeline(session: AsyncSession, case: RecoveryCase) -> None:
    """
    Executes the decision logic for a RecoveryCase.
    """
    case.status = CaseStatus.ANALYZING
    await session.flush()
    
    # 1. Fetch Policy (use the merchant's policy, fallback to first policy in system)
    policy_query = select(Policy)
    if case.merchant_id:
        policy_query = policy_query.where(Policy.merchant_id == case.merchant_id)
        
    result = await session.execute(policy_query)
    policy = result.scalars().first()
    
    if not policy:
        # Failsafe if DB has no policies at all
        raise RuntimeError("No active policy found in database to evaluate case.")
        
    policy_config = {
        "max_autonomous_amount_paise": policy.max_autonomous_amount_paise,
        "human_review_threshold_paise": policy.human_review_threshold_paise,
        "confidence_threshold": policy.confidence_threshold,
        "retry_limit": policy.retry_limit,
        "cooldown_hours": policy.cooldown_hours,
        "max_contacts_per_72h": policy.max_contacts_per_72h
    }
    
    # 2. Extract context & run AI (Phase 3)
    case_context = build_case_context(case)
    # The analyze_case function evaluates all candidate actions and returns the best.
    # We actually want the probabilities for ALL actions to rank them, so we will 
    # directly call the models or extract from the contract.
    # Wait, the contract only gives us the best action. Let's modify the local logic
    # to evaluate all candidates directly here to populate ranking, or just re-import ML models.
    # For Phase 4, we will re-calculate expected values manually using the ML model.
    # Note: AI inference functions are synchronous because they use Scikit-Learn/XGBoost.
    
    from ai.inference import predict
    from ai.features.engineer import build_features
    import pandas as pd
    
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
    best_candidate = ranked_actions[0]
    
    status, reason = evaluate_action(
        action_type=best_candidate.action_type,
        confidence=best_candidate.success_probability,
        amount_paise=case.amount_paise,
        policy_config=policy_config,
        case_history=history_context,
        current_time=datetime.now(timezone.utc)
    )
    
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
        
    # 7. Audit Log
    await log_decision(
        session=session,
        case_id=str(case.id),
        action_type=best_candidate.action_type,
        decision=status,
        reason=reason,
        model_version=decision_contract.model_version,
        policy_version=policy.version,
        context={
            "expected_value_paise": best_candidate.expected_value_paise,
            "confidence": best_candidate.success_probability,
            "risk_level": decision_contract.risk_level
        }
    )
