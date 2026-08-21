"""
Policy Engine Orchestrator

Why this exists:
  Takes a candidate action, the case context, and the merchant's policy,
  then runs all policy rules. It aggregates the results and returns the
  strictest authorization status (BLOCKED > AWAITING_HUMAN > AUTONOMOUS)
  along with the reason code.
"""

from datetime import datetime
from typing import Any

from domain.policies.rules import (
    OUTCOME_AUTONOMOUS,
    OUTCOME_BLOCKED,
    OUTCOME_HUMAN,
    check_autonomous_amount_limit,
    check_confidence_threshold,
    check_cooldown_period,
    check_frequency_cap,
    check_human_review_threshold,
    check_retry_limit,
)


def evaluate_action(
    action_type: str,
    confidence: float,
    amount_paise: int,
    policy_config: dict[str, Any],
    case_history: dict[str, Any],
    current_time: datetime
) -> tuple[str, str]:
    """
    Evaluates all rules for a given action and policy.
    
    Args:
        action_type: The candidate action (e.g., 'RETRY', 'PAYMENT_LINK')
        confidence: The P(success) or confidence from the AI.
        amount_paise: The payment amount.
        policy_config: Dictionary representing the Merchant's Policy row.
        case_history: Dictionary containing 'past_actions_count', 'last_action_time', 
                      and 'contacts_in_last_72h'.
        current_time: The current timestamp for cooldown calculation.
                      
    Returns:
        A tuple of (AuthorizationStatus, reason_code)
    """
    
    # 1. Evaluate all rules independently
    outcomes = [
        check_autonomous_amount_limit(amount_paise, policy_config.get("max_autonomous_amount_paise", 500000)),
        check_human_review_threshold(amount_paise, policy_config.get("human_review_threshold_paise", 2500000)),
        check_confidence_threshold(confidence, policy_config.get("confidence_threshold", 0.8)),
        check_retry_limit(case_history.get("past_actions_count", 0), policy_config.get("retry_limit", 2)),
        check_cooldown_period(case_history.get("last_action_time"), current_time, policy_config.get("cooldown_hours", 12)),
        check_frequency_cap(case_history.get("contacts_in_last_72h", 0), policy_config.get("max_contacts_per_72h", 2), action_type)
    ]
    
    # 2. Aggregate finding strictest outcome
    status = OUTCOME_AUTONOMOUS
    reason = "POLICY_CLEARED_AUTONOMOUS"
    
    print(f"DEBUG outcomes: {outcomes}")
    
    for outcome_status, outcome_reason in outcomes:
        if outcome_status == OUTCOME_BLOCKED:
            # Short-circuit: nothing overrides a BLOCK
            return OUTCOME_BLOCKED, outcome_reason
            
        if outcome_status == OUTCOME_HUMAN:
            # Upgrade from AUTONOMOUS to HUMAN, but continue checking in case a BLOCK rule fires later
            status = OUTCOME_HUMAN
            reason = outcome_reason
            
    return status, reason
