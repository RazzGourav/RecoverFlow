"""
Unit tests for the aggregate Policy Engine.

Ensures that multiple rules are evaluated correctly and the strictest outcome wins.
"""

from datetime import datetime, timedelta, timezone

from domain.policies.engine import (
    OUTCOME_AUTONOMOUS,
    OUTCOME_BLOCKED,
    OUTCOME_HUMAN,
    evaluate_action,
)


def test_engine_all_clear():
    policy = {
        "max_autonomous_amount_paise": 500000,
        "human_review_threshold_paise": 2500000,
        "confidence_threshold": 0.8,
        "retry_limit": 2,
        "cooldown_hours": 12,
        "max_contacts_per_72h": 2
    }
    history = {
        "past_actions_count": 0,
        "last_action_time": None,
        "contacts_in_last_72h": 0
    }
    
    status, reason = evaluate_action(
        action_type="PAYMENT_LINK",
        confidence=0.9,
        amount_paise=100000,
        policy_config=policy,
        case_history=history,
        current_time=datetime.now(timezone.utc)
    )
    
    assert status == OUTCOME_AUTONOMOUS
    assert reason == "POLICY_CLEARED_AUTONOMOUS"


def test_engine_human_escalation_wins_over_autonomous():
    policy = {
        "max_autonomous_amount_paise": 500000,
        "human_review_threshold_paise": 2500000,
        "confidence_threshold": 0.8,
        "retry_limit": 2,
        "cooldown_hours": 12,
        "max_contacts_per_72h": 2
    }
    history = {
        "past_actions_count": 0,
        "last_action_time": None,
        "contacts_in_last_72h": 0
    }
    
    # Amount exceeds autonomous but below review threshold
    status, reason = evaluate_action(
        action_type="PAYMENT_LINK",
        confidence=0.9,
        amount_paise=600000,
        policy_config=policy,
        case_history=history,
        current_time=datetime.now(timezone.utc)
    )
    
    assert status == OUTCOME_HUMAN
    assert reason == "POLICY_MAX_AUTONOMOUS_AMOUNT_EXCEEDED"


def test_engine_blocked_wins_over_human_escalation():
    policy = {
        "max_autonomous_amount_paise": 500000,
        "human_review_threshold_paise": 2500000,
        "confidence_threshold": 0.8,
        "retry_limit": 2,
        "cooldown_hours": 12,
        "max_contacts_per_72h": 2
    }
    now = datetime.now(timezone.utc)
    history = {
        "past_actions_count": 2,  # Retries exhausted
        "last_action_time": now - timedelta(hours=1), # Cooldown active
        "contacts_in_last_72h": 0
    }
    
    # Amount is huge (forces human review), BUT retry limit is exhausted (forces block).
    # Block must win.
    status, reason = evaluate_action(
        action_type="PAYMENT_LINK",
        confidence=0.1,  # Low confidence (human)
        amount_paise=3000000, # Huge amount (human)
        policy_config=policy,
        case_history=history,
        current_time=now
    )
    
    assert status == OUTCOME_BLOCKED
    # Depending on order of evaluation, reason might be retry or cooldown.
    assert reason in ["POLICY_RETRY_LIMIT_EXCEEDED", "POLICY_COOLDOWN_ACTIVE"]
