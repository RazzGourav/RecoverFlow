"""
Unit tests for deterministic policy rules.

Why this exists:
  Ensures the core safety net of the system functions exactly as specified
  at all boundary conditions, preventing unauthorized actions or money loss.
"""

from datetime import datetime, timedelta, timezone

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


def test_autonomous_amount_limit():
    # Exactly at limit is OK
    assert check_autonomous_amount_limit(500000, 500000) == (OUTCOME_AUTONOMOUS, None)
    # 1 paise over limit requires human
    assert check_autonomous_amount_limit(500001, 500000) == (OUTCOME_HUMAN, "POLICY_MAX_AUTONOMOUS_AMOUNT_EXCEEDED")
    # Well below limit is OK
    assert check_autonomous_amount_limit(100, 500000) == (OUTCOME_AUTONOMOUS, None)


def test_human_review_threshold():
    # Exactly at threshold requires human
    assert check_human_review_threshold(2500000, 2500000) == (OUTCOME_HUMAN, "POLICY_HUMAN_REVIEW_THRESHOLD_EXCEEDED")
    # 1 paise below threshold is OK
    assert check_human_review_threshold(2499999, 2500000) == (OUTCOME_AUTONOMOUS, None)


def test_confidence_threshold():
    # Exactly at threshold is OK
    assert check_confidence_threshold(0.80, 0.80) == (OUTCOME_AUTONOMOUS, None)
    # Below threshold requires human
    assert check_confidence_threshold(0.79, 0.80) == (OUTCOME_HUMAN, "POLICY_LOW_CONFIDENCE")
    # High confidence is OK
    assert check_confidence_threshold(0.99, 0.80) == (OUTCOME_AUTONOMOUS, None)


def test_retry_limit():
    # Reached limit -> BLOCKED
    assert check_retry_limit(2, 2) == (OUTCOME_BLOCKED, "POLICY_RETRY_LIMIT_EXCEEDED")
    # Exceeded limit -> BLOCKED
    assert check_retry_limit(3, 2) == (OUTCOME_BLOCKED, "POLICY_RETRY_LIMIT_EXCEEDED")
    # Below limit -> OK
    assert check_retry_limit(1, 2) == (OUTCOME_AUTONOMOUS, None)
    assert check_retry_limit(0, 2) == (OUTCOME_AUTONOMOUS, None)


def test_cooldown_period():
    now = datetime.now(timezone.utc)
    # No last action -> OK
    assert check_cooldown_period(None, now, 12) == (OUTCOME_AUTONOMOUS, None)
    
    # Exactly at cooldown boundary -> OK
    past_12h = now - timedelta(hours=12)
    assert check_cooldown_period(past_12h, now, 12) == (OUTCOME_AUTONOMOUS, None)
    
    # 1 second before cooldown ends -> BLOCKED
    past_almost_12h = now - timedelta(hours=11, minutes=59, seconds=59)
    assert check_cooldown_period(past_almost_12h, now, 12) == (OUTCOME_BLOCKED, "POLICY_COOLDOWN_ACTIVE")
    
    # Well past cooldown -> OK
    past_48h = now - timedelta(hours=48)
    assert check_cooldown_period(past_48h, now, 12) == (OUTCOME_AUTONOMOUS, None)


def test_frequency_cap():
    # Customer facing action exactly at cap -> BLOCKED
    assert check_frequency_cap(2, 2, "PAYMENT_LINK") == (OUTCOME_BLOCKED, "POLICY_FREQUENCY_CAP_EXCEEDED")
    # Customer facing action exceeded cap -> BLOCKED
    assert check_frequency_cap(3, 2, "PAYMENT_LINK") == (OUTCOME_BLOCKED, "POLICY_FREQUENCY_CAP_EXCEEDED")
    # Customer facing action below cap -> OK
    assert check_frequency_cap(1, 2, "PAYMENT_LINK") == (OUTCOME_AUTONOMOUS, None)
    
    # Non-customer facing action exactly at cap -> OK (exempt)
    assert check_frequency_cap(2, 2, "RETRY") == (OUTCOME_AUTONOMOUS, None)
    # Non-customer facing action exceeded cap -> OK (exempt)
    assert check_frequency_cap(5, 2, "PAYMENT_METHOD_UPDATE") == (OUTCOME_AUTONOMOUS, None)
