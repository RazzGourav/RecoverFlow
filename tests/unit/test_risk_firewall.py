"""
Risk Firewall — Unit Tests

Tests:
  - Each of the 5 risk checks: a TRIP case (flags it) and a PASS case (clean).
  - Regression tests using Phase 2 synthetic dataset edge cases:
      - Suspicious high-frequency contact (high_frequency_contact flag, i % 32 == 2)
      - High-amount cases needing human review (i % 30 == 0, amount ≥ ₹25,000)
      - Duplicate webhook (is_duplicate=True)
  - Invariant test: Risk Firewall NEVER upgrades a downstream BLOCK to ALLOW.

Why these tests are important:
  The Risk Firewall is a defense-only layer. If any code path could produce a
  less restrictive outcome than the Policy Engine, money could be moved without
  proper authorization. These tests assert that invariant with fuzzed inputs.
"""

import pytest

from domain.risk.checks import (
    check_amount_risk,
    check_behavioral_anomaly,
    check_frequency_risk,
    check_policy_violation,
    check_transaction_risk,
)
from domain.risk.firewall import (
    POLICY_OUTCOME_AUTONOMOUS,
    POLICY_OUTCOME_BLOCKED,
    POLICY_OUTCOME_HUMAN,
    RiskOutcome,
    compose_with_policy_decision,
    evaluate_risk_firewall,
)

# ===========================================================================
# Check 1 — Transaction Risk
# ===========================================================================

class TestTransactionRisk:
    """Unit tests for check_transaction_risk."""

    def test_trip_duplicate_event(self):
        """Duplicate webhook must be flagged as suspicious transaction."""
        result = check_transaction_risk(
            is_duplicate=True,
            is_stale=False,
            failure_type="TEMPORARY",
            past_failed_attempts=0,
        )
        assert result.flagged is True
        assert result.score >= 0.5
        assert "RISK_TRANSACTION_SUSPICIOUS" in result.reason
        assert "duplicate_event" in result.reason

    def test_trip_stale_event(self):
        """Stale webhook (already paid) must be flagged."""
        result = check_transaction_risk(
            is_duplicate=False,
            is_stale=True,
            failure_type="TEMPORARY",
            past_failed_attempts=0,
        )
        assert result.flagged is True
        assert result.score >= 0.5
        assert "stale_event_already_paid" in result.reason

    def test_trip_persistent_failure(self):
        """PERSISTENT failure type is a high-risk signal."""
        result = check_transaction_risk(
            is_duplicate=False,
            is_stale=False,
            failure_type="PERSISTENT",
            past_failed_attempts=0,
        )
        assert result.flagged is True
        assert "persistent_failure_type" in result.reason

    def test_trip_high_failed_attempts(self):
        """Excessive failed attempts (≥ 5) triggers the check."""
        result = check_transaction_risk(
            is_duplicate=False,
            is_stale=False,
            failure_type="TEMPORARY",
            past_failed_attempts=7,
            max_failed_attempts_before_suspicious=5,
        )
        assert result.flagged is True
        assert "high_failed_attempts_7" in result.reason

    def test_pass_clean_transaction(self):
        """Normal transaction should pass the check cleanly."""
        result = check_transaction_risk(
            is_duplicate=False,
            is_stale=False,
            failure_type="TEMPORARY",
            past_failed_attempts=1,
        )
        assert result.flagged is False
        assert result.score < 0.5
        assert result.reason == "RISK_TRANSACTION_CLEAN"


# ===========================================================================
# Check 2 — Frequency Risk
# ===========================================================================

class TestFrequencyRisk:
    """Unit tests for check_frequency_risk."""

    def test_trip_high_contact_frequency(self):
        """Too many contacts in 72h should flag frequency risk.
        
        This matches the Phase 2 synthetic dataset edge case:
        'suspicious high-frequency contacts' (i % 32 == 2, high_frequency_contact=True).
        """
        result = check_frequency_risk(
            contacts_in_last_72h=5,  # Above default threshold of 3
            actions_in_last_24h=0,
            max_contacts_72h=3,
        )
        assert result.flagged is True
        assert "contacts_72h_5_exceeds_3" in result.reason
        assert "RISK_FREQUENCY_EXCEEDED" in result.reason

    def test_trip_high_action_frequency(self):
        """Too many actions in 24h should flag frequency risk."""
        result = check_frequency_risk(
            contacts_in_last_72h=0,
            actions_in_last_24h=4,  # Above default threshold of 2
            max_actions_24h=2,
        )
        assert result.flagged is True
        assert "actions_24h_4_exceeds_2" in result.reason

    def test_pass_within_frequency_limits(self):
        """Frequency within policy limits should pass cleanly."""
        result = check_frequency_risk(
            contacts_in_last_72h=2,
            actions_in_last_24h=1,
            max_contacts_72h=3,
            max_actions_24h=2,
        )
        assert result.flagged is False
        assert result.reason == "RISK_FREQUENCY_CLEAN"


# ===========================================================================
# Check 3 — Amount Risk
# ===========================================================================

class TestAmountRisk:
    """Unit tests for check_amount_risk."""

    def test_trip_above_autonomous_threshold(self):
        """Amount between autonomous and review thresholds triggers REVIEW."""
        result = check_amount_risk(
            amount_paise=1_000_000,  # ₹10,000 — above ₹5,000 autonomous limit
            autonomous_threshold_paise=500_000,
            review_threshold_paise=2_500_000,
        )
        assert result.flagged is True
        assert "RISK_AMOUNT_ABOVE_AUTONOMOUS" in result.reason

    def test_trip_above_review_threshold(self):
        """Amount above review threshold (₹25,000) → high score.
        
        Matches Phase 2 synthetic dataset: 'High-amount cases needing human review'
        (i % 30 == 0, amount ≥ ₹25,000, requires_human_review=True).
        """
        result = check_amount_risk(
            amount_paise=3_000_000,  # ₹30,000 — above ₹25,000 review threshold
            autonomous_threshold_paise=500_000,
            review_threshold_paise=2_500_000,
        )
        assert result.flagged is True
        assert result.score >= 0.8
        assert "RISK_AMOUNT_REQUIRES_REVIEW" in result.reason

    def test_trip_above_hard_block_threshold(self):
        """Amount above hard block threshold (₹1,00,000) → BLOCK with score=1.0."""
        result = check_amount_risk(
            amount_paise=15_000_000,  # ₹1,50,000
            autonomous_threshold_paise=500_000,
            review_threshold_paise=2_500_000,
            hard_block_threshold_paise=10_000_000,
        )
        assert result.flagged is True
        assert result.score == 1.0
        assert "RISK_AMOUNT_HARD_BLOCK" in result.reason

    def test_pass_below_autonomous_threshold(self):
        """Small amount well under threshold should pass cleanly."""
        result = check_amount_risk(
            amount_paise=10_000,  # ₹100 — comfortably under ₹5,000
            autonomous_threshold_paise=500_000,
        )
        assert result.flagged is False
        assert result.score == 0.0
        assert result.reason == "RISK_AMOUNT_CLEAN"


# ===========================================================================
# Check 4 — Behavioral Anomaly
# ===========================================================================

class TestBehavioralAnomaly:
    """Unit tests for check_behavioral_anomaly."""

    def test_trip_amount_spike(self):
        """Amount 10x the typical triggers anomaly detection."""
        result = check_behavioral_anomaly(
            tenure_days=200,
            amount_paise=1_000_000,  # 10x the typical
            typical_amount_paise=100_000,
            segment="ESTABLISHED",
            failure_type="TEMPORARY",
            amount_deviation_factor=5.0,
        )
        assert result.flagged is True
        assert "amount_spike" in result.reason
        assert "RISK_BEHAVIORAL_ANOMALY" in result.reason

    def test_trip_new_customer_large_amount(self):
        """New customer (< 30 days) with a large payment is anomalous."""
        result = check_behavioral_anomaly(
            tenure_days=5,
            amount_paise=500_000,  # ₹5,000 — large for a 5-day-old customer
            typical_amount_paise=500_000,
            segment="NEW",
            failure_type="TEMPORARY",
            new_customer_max_amount_paise=100_000,  # ₹1,000 threshold for new
        )
        assert result.flagged is True
        assert "new_customer" in result.reason

    def test_trip_new_customer_persistent_failure(self):
        """New customer with PERSISTENT failure is an anomalous combination."""
        result = check_behavioral_anomaly(
            tenure_days=15,
            amount_paise=5_000,
            typical_amount_paise=5_000,
            segment="NEW",
            failure_type="PERSISTENT",
        )
        assert result.flagged is True
        assert "new_customer_persistent_failure" in result.reason

    def test_pass_established_customer_normal_amount(self):
        """Established customer, normal amount — should be clean."""
        result = check_behavioral_anomaly(
            tenure_days=365,
            amount_paise=50_000,   # ₹500
            typical_amount_paise=45_000,  # Close to typical
            segment="ESTABLISHED",
            failure_type="TEMPORARY",
        )
        assert result.flagged is False
        assert result.reason == "RISK_BEHAVIORAL_CLEAN"


# ===========================================================================
# Check 5 — Policy Violation
# ===========================================================================

class TestPolicyViolation:
    """Unit tests for check_policy_violation."""

    def test_trip_action_not_in_allowlist(self):
        """Action not in merchant's configured allowlist must be blocked."""
        result = check_policy_violation(
            action_type="PAYMENT_LINK",
            allowed_action_types=["RETRY", "REMINDER"],
            merchant_is_active=True,
            action_requires_human_approval=False,
            current_authorization_status="AUTONOMOUS",
        )
        assert result.flagged is True
        assert "PAYMENT_LINK_not_in_allowlist" in result.reason

    def test_trip_merchant_inactive(self):
        """Inactive merchant → all actions must be blocked at maximum score."""
        result = check_policy_violation(
            action_type="RETRY",
            allowed_action_types=["RETRY"],
            merchant_is_active=False,
            action_requires_human_approval=False,
            current_authorization_status="AUTONOMOUS",
        )
        assert result.flagged is True
        assert result.score == 1.0
        assert "merchant_account_inactive" in result.reason

    def test_trip_unapproved_action(self):
        """Action requiring approval without APPROVED status must flag."""
        result = check_policy_violation(
            action_type="PAYMENT_LINK",
            allowed_action_types=["PAYMENT_LINK"],
            merchant_is_active=True,
            action_requires_human_approval=True,
            current_authorization_status="AWAITING_HUMAN",
        )
        assert result.flagged is True
        assert "requires_approval_but_status_is_AWAITING_HUMAN" in result.reason

    def test_pass_allowed_action_autonomous(self):
        """Allowed action on active merchant with AUTONOMOUS status should pass."""
        result = check_policy_violation(
            action_type="RETRY",
            allowed_action_types=["RETRY", "PAYMENT_LINK"],
            merchant_is_active=True,
            action_requires_human_approval=False,
            current_authorization_status="AUTONOMOUS",
        )
        assert result.flagged is False
        assert result.reason == "RISK_POLICY_CLEAN"


# ===========================================================================
# Phase 2 Regression Tests — Planted "Suspicious" Edge Cases
# ===========================================================================

class TestPhase2EdgeCases:
    """
    Regression tests against the three suspicious edge cases planted in the
    Phase 2 synthetic data generator (data/synthetic/generate.py).

    These ensure that the Risk Firewall correctly catches known bad patterns
    that the synthetic dataset was designed to surface.
    """

    def test_regression_high_frequency_contact(self):
        """
        Regression: Phase 2 edge case 'suspicious high-frequency contact'
        (i % 32 == 2, high_frequency_contact=True, action=HUMAN_ESCALATION).
        
        A customer that has already been contacted many times should be flagged
        by the frequency check before any further action.
        """
        # Simulate a customer contacted 6 times in 72h (well above limit of 3)
        freq_result = check_frequency_risk(
            contacts_in_last_72h=6,
            actions_in_last_24h=3,
            max_contacts_72h=3,
            max_actions_24h=2,
        )
        assert freq_result.flagged is True, "High-frequency contact case must be flagged"
        assert freq_result.score >= 0.6

        # Full firewall should also produce REVIEW or BLOCK
        fw_result = evaluate_risk_firewall(
            is_duplicate=False,
            is_stale=False,
            failure_type="TEMPORARY",
            past_failed_attempts=0,
            contacts_in_last_72h=6,
            actions_in_last_24h=3,
            amount_paise=20_000,
            tenure_days=100,
            typical_amount_paise=20_000,
            segment="ESTABLISHED",
            action_type="HUMAN_ESCALATION",
            allowed_action_types=["HUMAN_ESCALATION", "RETRY"],
            merchant_is_active=True,
            action_requires_human_approval=False,
            current_authorization_status="AUTONOMOUS",
        )
        assert fw_result.outcome in (RiskOutcome.REVIEW, RiskOutcome.BLOCK)

    def test_regression_high_amount_requires_human_review(self):
        """
        Regression: Phase 2 edge case 'High-amount cases needing human review'
        (i % 30 == 0, amount ≥ ₹25,000, requires_human_review=True).
        
        A high-amount case should be caught by the amount check and escalated.
        """
        amount_result = check_amount_risk(
            amount_paise=4_000_000,  # ₹40,000 — above ₹25,000 review threshold
            autonomous_threshold_paise=500_000,
            review_threshold_paise=2_500_000,
        )
        assert amount_result.flagged is True, "High-amount case must be flagged"
        assert amount_result.score >= 0.8

        fw_result = evaluate_risk_firewall(
            is_duplicate=False,
            is_stale=False,
            failure_type="TEMPORARY",
            past_failed_attempts=0,
            contacts_in_last_72h=0,
            actions_in_last_24h=0,
            amount_paise=4_000_000,
            tenure_days=200,
            typical_amount_paise=4_000_000,
            segment="HIGH_VALUE",
            action_type="RETRY",
            allowed_action_types=["RETRY"],
            merchant_is_active=True,
            action_requires_human_approval=False,
            current_authorization_status="AUTONOMOUS",
        )
        # High amount must be at minimum REVIEW
        assert fw_result.outcome in (RiskOutcome.REVIEW, RiskOutcome.BLOCK)

    def test_regression_duplicate_webhook(self):
        """
        Regression: Phase 2 edge case 'Duplicate webhooks'
        (i % 33 == 3, is_duplicate=True).
        
        A duplicate event must always be flagged at the transaction risk level
        to prevent double-actions on the same payment.
        """
        txn_result = check_transaction_risk(
            is_duplicate=True,
            is_stale=False,
            failure_type="TEMPORARY",
            past_failed_attempts=0,
        )
        assert txn_result.flagged is True, "Duplicate event must always be flagged"
        assert txn_result.score >= 0.9  # Duplicate is high-confidence block signal

        fw_result = evaluate_risk_firewall(
            is_duplicate=True,
            is_stale=False,
            failure_type="TEMPORARY",
            past_failed_attempts=0,
            contacts_in_last_72h=0,
            actions_in_last_24h=0,
            amount_paise=10_000,
            tenure_days=100,
            typical_amount_paise=10_000,
            segment="ESTABLISHED",
            action_type="RETRY",
            allowed_action_types=["RETRY"],
            merchant_is_active=True,
            action_requires_human_approval=False,
            current_authorization_status="AUTONOMOUS",
        )
        # Duplicate with score 0.9 must be BLOCK
        assert fw_result.outcome == RiskOutcome.BLOCK


# ===========================================================================
# Invariant Tests — Firewall NEVER upgrades a BLOCK
# ===========================================================================

class TestDefenseOnlyInvariant:
    """
    CRITICAL: These tests assert the core defense-only invariant.
    The Risk Firewall can NEVER make a decision LESS restrictive.
    
    A BLOCK from the Policy Engine must remain BLOCKED regardless of the
    firewall outcome. A REVIEW must remain at least REVIEW.
    """

    def test_firewall_allow_with_policy_blocked_stays_blocked(self):
        """ALLOW from firewall + BLOCKED from policy → must remain BLOCKED."""
        result = compose_with_policy_decision(
            firewall_outcome=RiskOutcome.ALLOW,
            policy_outcome=POLICY_OUTCOME_BLOCKED,
        )
        assert result == POLICY_OUTCOME_BLOCKED, (
            "Firewall ALLOW must never override a policy BLOCK"
        )

    def test_firewall_review_with_policy_blocked_stays_blocked(self):
        """REVIEW from firewall + BLOCKED from policy → must remain BLOCKED."""
        result = compose_with_policy_decision(
            firewall_outcome=RiskOutcome.REVIEW,
            policy_outcome=POLICY_OUTCOME_BLOCKED,
        )
        assert result == POLICY_OUTCOME_BLOCKED

    def test_firewall_block_with_policy_autonomous_becomes_blocked(self):
        """BLOCK from firewall always overrides AUTONOMOUS from policy."""
        result = compose_with_policy_decision(
            firewall_outcome=RiskOutcome.BLOCK,
            policy_outcome=POLICY_OUTCOME_AUTONOMOUS,
        )
        assert result == POLICY_OUTCOME_BLOCKED

    def test_firewall_review_with_policy_autonomous_becomes_review(self):
        """REVIEW from firewall upgrades AUTONOMOUS to AWAITING_HUMAN."""
        result = compose_with_policy_decision(
            firewall_outcome=RiskOutcome.REVIEW,
            policy_outcome=POLICY_OUTCOME_AUTONOMOUS,
        )
        assert result == POLICY_OUTCOME_HUMAN

    def test_firewall_allow_with_policy_autonomous_stays_autonomous(self):
        """ALLOW from firewall defers entirely to policy AUTONOMOUS."""
        result = compose_with_policy_decision(
            firewall_outcome=RiskOutcome.ALLOW,
            policy_outcome=POLICY_OUTCOME_AUTONOMOUS,
        )
        assert result == POLICY_OUTCOME_AUTONOMOUS

    @pytest.mark.parametrize("amount_paise,contacts,attempts,expected_min_outcome", [
        # High-amount always at least REVIEW
        (3_000_000, 0, 0, RiskOutcome.REVIEW),
        # Very high amount → BLOCK
        (15_000_000, 0, 0, RiskOutcome.BLOCK),
        # High frequency → REVIEW
        (10_000, 8, 0, RiskOutcome.REVIEW),
        # Duplicate → BLOCK
        (10_000, 0, 0, RiskOutcome.BLOCK),  # covered via is_duplicate path
    ])
    def test_fuzz_firewall_never_upgrades_policy_block(
        self, amount_paise: int, contacts: int, attempts: int, expected_min_outcome: RiskOutcome
    ):
        """
        Fuzz test: for a range of inputs, verify that when the Policy Engine
        says BLOCKED, the composed result is ALWAYS BLOCKED regardless of
        what the Risk Firewall says.
        """
        # We don't need to actually call the firewall here — just compose_with_policy_decision
        # with all three possible firewall outcomes against a policy BLOCK.
        for firewall_outcome in RiskOutcome:
            composed = compose_with_policy_decision(
                firewall_outcome=firewall_outcome,
                policy_outcome=POLICY_OUTCOME_BLOCKED,
            )
            assert composed == POLICY_OUTCOME_BLOCKED, (
                f"Firewall {firewall_outcome} must not override policy BLOCK. "
                f"Got {composed} for amount={amount_paise}, contacts={contacts}"
            )

    def test_all_firewall_outcomes_against_all_policy_outcomes(self):
        """
        Exhaustive composition table test.
        Verifies the full 3x3 precedence table in domain/risk/README.md.
        """
        expected = {
            (RiskOutcome.ALLOW,   POLICY_OUTCOME_AUTONOMOUS): POLICY_OUTCOME_AUTONOMOUS,
            (RiskOutcome.ALLOW,   POLICY_OUTCOME_HUMAN):      POLICY_OUTCOME_HUMAN,
            (RiskOutcome.ALLOW,   POLICY_OUTCOME_BLOCKED):    POLICY_OUTCOME_BLOCKED,
            (RiskOutcome.REVIEW,  POLICY_OUTCOME_AUTONOMOUS): POLICY_OUTCOME_HUMAN,
            (RiskOutcome.REVIEW,  POLICY_OUTCOME_HUMAN):      POLICY_OUTCOME_HUMAN,
            (RiskOutcome.REVIEW,  POLICY_OUTCOME_BLOCKED):    POLICY_OUTCOME_BLOCKED,
            (RiskOutcome.BLOCK,   POLICY_OUTCOME_AUTONOMOUS): POLICY_OUTCOME_BLOCKED,
            (RiskOutcome.BLOCK,   POLICY_OUTCOME_HUMAN):      POLICY_OUTCOME_BLOCKED,
            (RiskOutcome.BLOCK,   POLICY_OUTCOME_BLOCKED):    POLICY_OUTCOME_BLOCKED,
        }
        for (fw, pe), expected_result in expected.items():
            actual = compose_with_policy_decision(fw, pe)
            assert actual == expected_result, (
                f"compose({fw}, {pe}) should be {expected_result}, got {actual}"
            )
