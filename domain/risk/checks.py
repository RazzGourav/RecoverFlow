"""
Risk Firewall — Five Independent Risk Checks

Why this exists:
  Each check targets a specific risk dimension as defined in PRD Module D.
  They are implemented as pure functions so they are independently unit-testable
  with zero database or network dependencies.

  All checks return a RiskCheckResult with:
    - flagged: bool — True means the check found a problem.
    - score:   float in [0.0, 1.0] — severity (0 = no risk, 1 = max risk).
    - reason:  str — human-readable explanation prefixed with "RISK_" so audit
               trails can distinguish Risk Firewall reasons from Policy Engine reasons.

Design principle — defense only:
  No check can make an action MORE permissive. They only flag risk.
  The firewall aggregates flags and scores into ALLOW / REVIEW / BLOCK.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RiskCheckResult:
    """
    Immutable result of a single risk dimension check.

    Why frozen: Results should never be mutated after creation; freezing enforces
    that the firewall cannot accidentally modify them during aggregation.
    """

    check_name: str
    flagged: bool
    score: float  # [0.0, 1.0] — 0 = clean, 1 = maximum risk
    reason: str  # Always starts with "RISK_" prefix


# ---------------------------------------------------------------------------
# Check 1 — Transaction Risk
# ---------------------------------------------------------------------------

def check_transaction_risk(
    is_duplicate: bool,
    is_stale: bool,
    failure_type: str,
    past_failed_attempts: int,
    *,
    max_failed_attempts_before_suspicious: int = 5,
) -> RiskCheckResult:
    """
    Check 1 — Transaction risk: is this customer/payment pattern suspicious?

    Flags if:
      - The event is a duplicate webhook (risk of double-action).
      - The event is stale (already paid — action would be erroneous).
      - The payment has had an unusually high number of prior failed attempts,
        suggesting a non-recoverable or abusive pattern.

    Args:
        is_duplicate: Whether this event has already been processed.
        is_stale: Whether the underlying payment was already collected.
        failure_type: Root-cause classification (TEMPORARY, PERSISTENT, etc.).
        past_failed_attempts: Count of prior failed payment attempts.
        max_failed_attempts_before_suspicious: Threshold above which we flag.

    Returns:
        RiskCheckResult with check_name='TRANSACTION_RISK'.
    """
    score = 0.0
    reasons: list[str] = []

    if is_duplicate:
        score = max(score, 0.9)
        reasons.append("duplicate_event")

    if is_stale:
        score = max(score, 0.8)
        reasons.append("stale_event_already_paid")

    if failure_type == "PERSISTENT":
        score = max(score, 0.7)
        reasons.append("persistent_failure_type")

    if past_failed_attempts >= max_failed_attempts_before_suspicious:
        attempt_score = min(1.0, 0.5 + 0.1 * (past_failed_attempts - max_failed_attempts_before_suspicious))
        score = max(score, attempt_score)
        reasons.append(f"high_failed_attempts_{past_failed_attempts}")

    flagged = score >= 0.5
    reason_str = "RISK_TRANSACTION_CLEAN" if not flagged else f"RISK_TRANSACTION_SUSPICIOUS:{','.join(reasons)}"

    return RiskCheckResult(
        check_name="TRANSACTION_RISK",
        flagged=flagged,
        score=score,
        reason=reason_str,
    )


# ---------------------------------------------------------------------------
# Check 2 — Frequency Risk
# ---------------------------------------------------------------------------

def check_frequency_risk(
    contacts_in_last_72h: int,
    actions_in_last_24h: int,
    *,
    max_contacts_72h: int = 3,
    max_actions_24h: int = 2,
) -> RiskCheckResult:
    """
    Check 2 — Frequency risk: has the customer been contacted/retried too often?

    Flags if:
      - Customer has been contacted more than max_contacts_72h times in 72 hours.
      - More than max_actions_24h actions have been attempted in the last 24 hours.

    Excessive contact is both a compliance risk and a churn risk. It also
    matches the 'suspicious high-frequency contact' edge case from Phase 2's
    synthetic dataset.

    Args:
        contacts_in_last_72h: Number of customer-facing contacts in last 72 hours.
        actions_in_last_24h: Number of recovery actions attempted in last 24 hours.
        max_contacts_72h: Policy-driven contact frequency ceiling.
        max_actions_24h: Policy-driven action frequency ceiling.

    Returns:
        RiskCheckResult with check_name='FREQUENCY_RISK'.
    """
    score = 0.0
    reasons: list[str] = []

    if contacts_in_last_72h >= max_contacts_72h:
        freq_score = min(1.0, 0.6 + 0.1 * (contacts_in_last_72h - max_contacts_72h))
        score = max(score, freq_score)
        reasons.append(f"contacts_72h_{contacts_in_last_72h}_exceeds_{max_contacts_72h}")

    if actions_in_last_24h >= max_actions_24h:
        action_score = min(1.0, 0.7 + 0.1 * (actions_in_last_24h - max_actions_24h))
        score = max(score, action_score)
        reasons.append(f"actions_24h_{actions_in_last_24h}_exceeds_{max_actions_24h}")

    flagged = score >= 0.5
    reason_str = "RISK_FREQUENCY_CLEAN" if not flagged else f"RISK_FREQUENCY_EXCEEDED:{','.join(reasons)}"

    return RiskCheckResult(
        check_name="FREQUENCY_RISK",
        flagged=flagged,
        score=score,
        reason=reason_str,
    )


# ---------------------------------------------------------------------------
# Check 3 — Amount Risk
# ---------------------------------------------------------------------------

def check_amount_risk(
    amount_paise: int,
    *,
    autonomous_threshold_paise: int = 500_000,    # ₹5,000
    review_threshold_paise: int = 2_500_000,      # ₹25,000
    hard_block_threshold_paise: int = 10_000_000, # ₹1,00,000
) -> RiskCheckResult:
    """
    Check 3 — Amount risk: is the payment above the autonomous-action threshold?

    Three tiers:
      - Below autonomous_threshold: ALLOW (low risk).
      - Between autonomous and review threshold: REVIEW required.
      - Between review and hard_block threshold: REVIEW (high risk score).
      - Above hard_block threshold: BLOCK unconditionally (score = 1.0).

    This matches the PRD's 'Auto-recovery allowed ≤ ₹5,000' rule and the Phase 2
    synthetic data's 'High-amount cases needing human review' edge cases (₹25,000+).

    Args:
        amount_paise: Payment amount in paise.
        autonomous_threshold_paise: Max amount for fully autonomous action.
        review_threshold_paise: Above this, always requires human review.
        hard_block_threshold_paise: Above this, action is unconditionally blocked.

    Returns:
        RiskCheckResult with check_name='AMOUNT_RISK'.
    """
    if amount_paise > hard_block_threshold_paise:
        return RiskCheckResult(
            check_name="AMOUNT_RISK",
            flagged=True,
            score=1.0,
            reason=f"RISK_AMOUNT_HARD_BLOCK:amount_{amount_paise}_exceeds_{hard_block_threshold_paise}",
        )

    if amount_paise > review_threshold_paise:
        score = 0.85
        return RiskCheckResult(
            check_name="AMOUNT_RISK",
            flagged=True,
            score=score,
            reason=f"RISK_AMOUNT_REQUIRES_REVIEW:amount_{amount_paise}_exceeds_{review_threshold_paise}",
        )

    if amount_paise > autonomous_threshold_paise:
        # Graduated score between 0.5 and 0.8 in the middle band
        ratio = (amount_paise - autonomous_threshold_paise) / (review_threshold_paise - autonomous_threshold_paise)
        score = 0.5 + 0.3 * ratio
        return RiskCheckResult(
            check_name="AMOUNT_RISK",
            flagged=True,
            score=score,
            reason=f"RISK_AMOUNT_ABOVE_AUTONOMOUS:amount_{amount_paise}_exceeds_{autonomous_threshold_paise}",
        )

    return RiskCheckResult(
        check_name="AMOUNT_RISK",
        flagged=False,
        score=0.0,
        reason="RISK_AMOUNT_CLEAN",
    )


# ---------------------------------------------------------------------------
# Check 4 — Behavioral Anomaly
# ---------------------------------------------------------------------------

def check_behavioral_anomaly(
    tenure_days: int,
    amount_paise: int,
    typical_amount_paise: int,
    segment: str,
    failure_type: str,
    *,
    amount_deviation_factor: float = 5.0,
    new_customer_max_amount_paise: int = 100_000,  # ₹1,000
) -> RiskCheckResult:
    """
    Check 4 — Behavioral anomaly: is this case highly unusual vs history?

    Flags if:
      - Amount is more than amount_deviation_factor × the customer's typical amount
        (unusual spike, potential fraud or error).
      - New customer (tenure < 30 days) with an unusually large payment.
      - A NEW-segment customer has a PERSISTENT failure type (churn risk combined
        with unrecoverable pattern is anomalous and risky to contact).

    This is intentionally conservative — anomaly detection should err on the side
    of flagging rather than missing a suspicious case.

    Args:
        tenure_days: Customer's account age in days.
        amount_paise: Current payment amount in paise.
        typical_amount_paise: The customer's historical average payment amount.
        segment: Customer segment (NEW, ESTABLISHED, HIGH_VALUE).
        failure_type: Root-cause failure classification.
        amount_deviation_factor: How many times above typical triggers the flag.
        new_customer_max_amount_paise: Large amount threshold for new customers.

    Returns:
        RiskCheckResult with check_name='BEHAVIORAL_ANOMALY'.
    """
    score = 0.0
    reasons: list[str] = []

    # Anomalous amount spike
    if typical_amount_paise > 0 and amount_paise > typical_amount_paise * amount_deviation_factor:
        spike_ratio = amount_paise / typical_amount_paise
        spike_score = min(1.0, 0.6 + 0.05 * (spike_ratio - amount_deviation_factor))
        score = max(score, spike_score)
        reasons.append(f"amount_spike_{spike_ratio:.1f}x_typical")

    # New customer with large payment
    if tenure_days < 30 and amount_paise > new_customer_max_amount_paise:
        score = max(score, 0.7)
        reasons.append(f"new_customer_tenure_{tenure_days}d_large_amount_{amount_paise}")

    # New customer + persistent failure (high anomaly risk)
    if segment == "NEW" and failure_type == "PERSISTENT":
        score = max(score, 0.65)
        reasons.append("new_customer_persistent_failure")

    flagged = score >= 0.5
    reason_str = "RISK_BEHAVIORAL_CLEAN" if not flagged else f"RISK_BEHAVIORAL_ANOMALY:{','.join(reasons)}"

    return RiskCheckResult(
        check_name="BEHAVIORAL_ANOMALY",
        flagged=flagged,
        score=score,
        reason=reason_str,
    )


# ---------------------------------------------------------------------------
# Check 5 — Policy Violation
# ---------------------------------------------------------------------------

def check_policy_violation(
    action_type: str,
    allowed_action_types: list[str],
    merchant_is_active: bool,
    action_requires_human_approval: bool,
    current_authorization_status: str,
) -> RiskCheckResult:
    """
    Check 5 — Policy violation: would the action violate merchant rules?

    Flags if:
      - The proposed action type is not in the merchant's allowed action list.
      - The merchant account is inactive (actions must be blocked entirely).
      - The action requires human approval but has not been approved
        (i.e., authorization_status is not APPROVED or AUTONOMOUS).

    This is the last line of defense before execution. It catches cases where
    the policy engine or ranking layer erroneously selected a forbidden action.

    Args:
        action_type: The proposed action to execute.
        allowed_action_types: Merchant's allowlist of action types.
        merchant_is_active: Whether the merchant account is currently active.
        action_requires_human_approval: Whether this action class needs approval.
        current_authorization_status: The Policy Engine's authorization decision.

    Returns:
        RiskCheckResult with check_name='POLICY_VIOLATION'.
    """
    score = 0.0
    reasons: list[str] = []

    if not merchant_is_active:
        score = max(score, 1.0)
        reasons.append("merchant_account_inactive")

    if action_type not in allowed_action_types:
        score = max(score, 0.9)
        reasons.append(f"action_{action_type}_not_in_allowlist")

    if action_requires_human_approval and current_authorization_status not in ("APPROVED", "AUTONOMOUS"):
        score = max(score, 0.8)
        reasons.append(f"requires_approval_but_status_is_{current_authorization_status}")

    flagged = score >= 0.5
    reason_str = "RISK_POLICY_CLEAN" if not flagged else f"RISK_POLICY_VIOLATION:{','.join(reasons)}"

    return RiskCheckResult(
        check_name="POLICY_VIOLATION",
        flagged=flagged,
        score=score,
        reason=reason_str,
    )
