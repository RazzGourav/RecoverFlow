"""
Risk Firewall — Domain Module

Why this exists:
  Implements PRD Module D — a defense-only pre-execution safety layer that evaluates
  five independent risk checks before any financial or customer-facing action is taken.

  The Risk Firewall can only make decisions MORE restrictive, never less.
  It outputs ALLOW / REVIEW / BLOCK. A BLOCK from the firewall ALWAYS supersedes
  an AUTONOMOUS decision from the Policy Engine. A REVIEW supersedes AUTONOMOUS but
  not AWAITING_HUMAN.

Precedence rule (documented in README.md):
  BLOCK  > REVIEW > ALLOW
  Risk Firewall outcome is composed with Policy Engine outcome by taking the
  stricter of the two. The firewall is defense-only by construction — it never
  upgrades a BLOCK to ALLOW.
"""

from domain.risk.checks import (
    RiskCheckResult,
    check_amount_risk,
    check_behavioral_anomaly,
    check_frequency_risk,
    check_policy_violation,
    check_transaction_risk,
)
from domain.risk.firewall import RiskOutcome, evaluate_risk_firewall

__all__ = [
    "RiskCheckResult",
    "RiskOutcome",
    "check_amount_risk",
    "check_behavioral_anomaly",
    "check_frequency_risk",
    "check_policy_violation",
    "check_transaction_risk",
    "evaluate_risk_firewall",
]
