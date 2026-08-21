"""
Deterministic Policy Rules

Why this exists:
  Implements the strict merchant-configured guardrails exactly as specified
  in PRD Module G. These are pure functions designed to be 100% unit-testable.
  There are ZERO LLM calls or ML inferences in this file — this is the
  hard-coded safety net.
"""

from datetime import datetime, timezone
from typing import Tuple

# Possible outcomes for a rule check.
# The engine will select the strictest outcome: BLOCKED > AWAITING_HUMAN > AUTONOMOUS
OUTCOME_AUTONOMOUS = "AUTONOMOUS"
OUTCOME_HUMAN = "AWAITING_HUMAN"
OUTCOME_BLOCKED = "BLOCKED"


def check_autonomous_amount_limit(
    amount_paise: int, max_autonomous_amount_paise: int
) -> Tuple[str, str | None]:
    """
    If the amount exceeds the max autonomous amount, it requires human approval.
    """
    if amount_paise > max_autonomous_amount_paise:
        return OUTCOME_HUMAN, "POLICY_MAX_AUTONOMOUS_AMOUNT_EXCEEDED"
    return OUTCOME_AUTONOMOUS, None


def check_human_review_threshold(
    amount_paise: int, human_review_threshold_paise: int
) -> Tuple[str, str | None]:
    """
    If the amount is extremely high (above human review threshold), it ALWAYS requires human approval.
    (This is often structurally similar to autonomous limit but kept separate for clear audit trails).
    """
    if amount_paise >= human_review_threshold_paise:
        return OUTCOME_HUMAN, "POLICY_HUMAN_REVIEW_THRESHOLD_EXCEEDED"
    return OUTCOME_AUTONOMOUS, None


def check_confidence_threshold(
    confidence: float, required_confidence: float
) -> Tuple[str, str | None]:
    """
    If the AI model's confidence in the action is below the required threshold,
    a human must review the case.
    """
    if confidence < required_confidence:
        return OUTCOME_HUMAN, "POLICY_LOW_CONFIDENCE"
    return OUTCOME_AUTONOMOUS, None


def check_retry_limit(
    past_actions_count: int, retry_limit: int
) -> Tuple[str, str | None]:
    """
    If the case has already met or exceeded the retry limit, further actions are blocked.
    """
    if past_actions_count >= retry_limit:
        return OUTCOME_BLOCKED, "POLICY_RETRY_LIMIT_EXCEEDED"
    return OUTCOME_AUTONOMOUS, None


def check_cooldown_period(
    last_action_time: datetime | None,
    current_time: datetime,
    cooldown_hours: int
) -> Tuple[str, str | None]:
    """
    If an action was taken too recently (within the cooldown window), block this action.
    """
    if not last_action_time:
        return OUTCOME_AUTONOMOUS, None
        
    delta_hours = (current_time - last_action_time).total_seconds() / 3600.0
    if delta_hours < cooldown_hours:
        return OUTCOME_BLOCKED, "POLICY_COOLDOWN_ACTIVE"
    return OUTCOME_AUTONOMOUS, None


def check_frequency_cap(
    contacts_in_last_72h: int, max_contacts_per_72h: int, action_type: str
) -> Tuple[str, str | None]:
    """
    If the customer has been contacted too many times recently, block customer-facing actions.
    Non-customer-facing actions (like backend retries) are exempt from this specific cap.
    """
    customer_facing_actions = ["PAYMENT_LINK", "INVOICE", "REMINDER"]
    if action_type in customer_facing_actions:
        if contacts_in_last_72h >= max_contacts_per_72h:
            return OUTCOME_BLOCKED, "POLICY_FREQUENCY_CAP_EXCEEDED"
    return OUTCOME_AUTONOMOUS, None
