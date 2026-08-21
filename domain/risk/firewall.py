"""
Risk Firewall — Aggregation Engine

Why this exists:
  Aggregates the results of all five independent risk checks into a single
  ALLOW / REVIEW / BLOCK decision.

  CRITICAL INVARIANT — Defense-only:
    The Risk Firewall can ONLY make a decision more restrictive, never less.
    compose_with_policy_decision() enforces this by taking the stricter of
    Risk Firewall outcome is composed with Policy Engine outcome by taking the
    stricter of the two. The firewall is defense-only by construction — it never
    upgrades a BLOCK to ALLOW.

Precedence rule:
    BLOCK  > REVIEW > ALLOW

    Risk Firewall outcome is composed with Policy Engine outcome by taking the
    stricter of the two:

      RF=ALLOW   + PE=AUTONOMOUS   → AUTONOMOUS
      RF=ALLOW   + PE=AWAITING_HUMAN → AWAITING_HUMAN
      RF=ALLOW   + PE=BLOCKED      → BLOCKED
      RF=REVIEW  + PE=AUTONOMOUS   → AWAITING_HUMAN
      RF=REVIEW  + PE=AWAITING_HUMAN → AWAITING_HUMAN
      RF=REVIEW  + PE=BLOCKED      → BLOCKED
      RF=BLOCK   + PE=AUTONOMOUS   → BLOCKED
      RF=BLOCK   + PE=AWAITING_HUMAN → BLOCKED
      RF=BLOCK   + PE=BLOCKED      → BLOCKED

    The firewall result is computed from check scores:
      - Any check score >= 0.9 → BLOCK
      - Any check score >= 0.5 (flagged) → REVIEW
      - All checks clean → ALLOW
"""

from __future__ import annotations

import enum
from dataclasses import dataclass

from domain.risk.checks import (
    RiskCheckResult,
    check_amount_risk,
    check_behavioral_anomaly,
    check_frequency_risk,
    check_policy_violation,
    check_transaction_risk,
)

# Outcome constants — use these strings in audit event reason codes.
RISK_OUTCOME_ALLOW = "ALLOW"
RISK_OUTCOME_REVIEW = "REVIEW"
RISK_OUTCOME_BLOCK = "BLOCK"

# Policy engine outcome constants (mirrors domain.policies.engine)
POLICY_OUTCOME_AUTONOMOUS = "AUTONOMOUS"
POLICY_OUTCOME_HUMAN = "AWAITING_HUMAN"
POLICY_OUTCOME_BLOCKED = "BLOCKED"


class RiskOutcome(str, enum.Enum):
    """The three possible outputs of the Risk Firewall."""

    ALLOW = "ALLOW"
    REVIEW = "REVIEW"
    BLOCK = "BLOCK"


@dataclass(frozen=True)
class FirewallResult:
    """
    Aggregate result from all five Risk Firewall checks.

    Why frozen: The result is produced once and must not be mutated —
    mutating a risk result after-the-fact would undermine the audit trail.
    """

    outcome: RiskOutcome
    overall_score: float           # Max of individual check scores [0.0, 1.0]
    check_results: list[RiskCheckResult]
    triggered_reasons: list[str]   # Reasons from checks that fired (score >= 0.5)
    primary_reason: str            # Top-level audit reason code


def evaluate_risk_firewall(
    *,
    # Check 1 — Transaction risk
    is_duplicate: bool,
    is_stale: bool,
    failure_type: str,
    past_failed_attempts: int,
    # Check 2 — Frequency risk
    contacts_in_last_72h: int,
    actions_in_last_24h: int,
    # Check 3 — Amount risk
    amount_paise: int,
    # Check 4 — Behavioral anomaly
    tenure_days: int,
    typical_amount_paise: int,
    segment: str,
    # Check 5 — Policy violation
    action_type: str,
    allowed_action_types: list[str],
    merchant_is_active: bool,
    action_requires_human_approval: bool,
    current_authorization_status: str,
    # Thresholds (can be overridden per merchant config)
    autonomous_threshold_paise: int = 500_000,
    review_threshold_paise: int = 2_500_000,
    hard_block_threshold_paise: int = 10_000_000,
    max_contacts_72h: int = 3,
    max_actions_24h: int = 2,
    max_failed_attempts_before_suspicious: int = 5,
    amount_deviation_factor: float = 5.0,
    new_customer_max_amount_paise: int = 100_000,
) -> FirewallResult:
    """
    Run all five risk checks and aggregate into a single ALLOW / REVIEW / BLOCK.

    Aggregation logic:
      1. Run all five checks independently.
      2. Collect scores from all checks.
      3. If any score >= 0.9 → BLOCK (unambiguous high-confidence block signal).
      4. Else if any check is flagged (score >= 0.5) → REVIEW.
      5. Else → ALLOW.

    The overall_score is the maximum individual check score, which reflects
    the worst-case risk dimension.

    Args:
        is_duplicate, is_stale, failure_type, past_failed_attempts: Check 1 inputs.
        contacts_in_last_72h, actions_in_last_24h: Check 2 inputs.
        amount_paise: Check 3 input (also used in Check 4).
        tenure_days, typical_amount_paise, segment: Check 4 inputs.
        action_type, allowed_action_types, merchant_is_active,
        action_requires_human_approval, current_authorization_status: Check 5 inputs.
        *threshold params: Override default policy thresholds.

    Returns:
        FirewallResult with outcome, score, all check results, and reason codes.
    """
    results = [
        check_transaction_risk(
            is_duplicate=is_duplicate,
            is_stale=is_stale,
            failure_type=failure_type,
            past_failed_attempts=past_failed_attempts,
            max_failed_attempts_before_suspicious=max_failed_attempts_before_suspicious,
        ),
        check_frequency_risk(
            contacts_in_last_72h=contacts_in_last_72h,
            actions_in_last_24h=actions_in_last_24h,
            max_contacts_72h=max_contacts_72h,
            max_actions_24h=max_actions_24h,
        ),
        check_amount_risk(
            amount_paise=amount_paise,
            autonomous_threshold_paise=autonomous_threshold_paise,
            review_threshold_paise=review_threshold_paise,
            hard_block_threshold_paise=hard_block_threshold_paise,
        ),
        check_behavioral_anomaly(
            tenure_days=tenure_days,
            amount_paise=amount_paise,
            typical_amount_paise=typical_amount_paise,
            segment=segment,
            failure_type=failure_type,
            amount_deviation_factor=amount_deviation_factor,
            new_customer_max_amount_paise=new_customer_max_amount_paise,
        ),
        check_policy_violation(
            action_type=action_type,
            allowed_action_types=allowed_action_types,
            merchant_is_active=merchant_is_active,
            action_requires_human_approval=action_requires_human_approval,
            current_authorization_status=current_authorization_status,
        ),
    ]

    overall_score = max(r.score for r in results)
    triggered = [r for r in results if r.flagged]
    triggered_reasons = [r.reason for r in triggered]

    # Aggregate into outcome
    if overall_score >= 0.9:
        outcome = RiskOutcome.BLOCK
        primary_reason = f"RISK_FIREWALL_BLOCK:score={overall_score:.2f}"
    elif triggered:
        outcome = RiskOutcome.REVIEW
        primary_reason = f"RISK_FIREWALL_REVIEW:score={overall_score:.2f}"
    else:
        outcome = RiskOutcome.ALLOW
        primary_reason = "RISK_FIREWALL_ALLOW"

    return FirewallResult(
        outcome=outcome,
        overall_score=overall_score,
        check_results=results,
        triggered_reasons=triggered_reasons,
        primary_reason=primary_reason,
    )


def compose_with_policy_decision(
    firewall_outcome: RiskOutcome,
    policy_outcome: str,
) -> str:
    """
    Compose Risk Firewall outcome with Policy Engine outcome.

    INVARIANT: The result is ALWAYS at least as restrictive as both inputs.
    The firewall never upgrades a BLOCK to ALLOW. It can only downgrade ALLOW
    to REVIEW or BLOCK, or downgrade REVIEW to BLOCK.

    Args:
        firewall_outcome: Result from evaluate_risk_firewall().
        policy_outcome: One of 'AUTONOMOUS', 'AWAITING_HUMAN', 'BLOCKED'.

    Returns:
        The stricter of the two outcomes, as a Policy Engine string:
        'AUTONOMOUS', 'AWAITING_HUMAN', or 'BLOCKED'.
    """
    # Normalize firewall outcome to policy engine vocabulary
    if firewall_outcome == RiskOutcome.BLOCK:
        return POLICY_OUTCOME_BLOCKED
    if firewall_outcome == RiskOutcome.REVIEW:
        # REVIEW is at least AWAITING_HUMAN; if policy already said BLOCK → stay BLOCKED
        if policy_outcome == POLICY_OUTCOME_BLOCKED:
            return POLICY_OUTCOME_BLOCKED
        return POLICY_OUTCOME_HUMAN
    # firewall_outcome == ALLOW — defer entirely to policy engine
    return policy_outcome
