"""
RecoverFlow API — Mock Validation Module

Why this file exists:
  Provides a deterministic validation layer for testing the state machine,
  mirroring `razorpay/validation.py`.
"""

from __future__ import annotations

from apps.api.db.models import ActionType
from integrations.integrations.validation import ValidationOutcome, ValidationStatus


def validate_action_against_live_state(action_type: ActionType, live_payment_state: dict) -> ValidationOutcome:
    """
    Mock validation logic.
    """
    if not live_payment_state:
        return ValidationOutcome(ValidationStatus.INVALID_STATE, "Missing live state.")
        
    status = live_payment_state.get("status")
    
    # Simulate a race condition where the payment was already captured
    if status in ("captured", "authorized", "paid"):
        if action_type != ActionType.NO_ACTION:
            return ValidationOutcome(
                ValidationStatus.INVALID_STATE,
                f"Action {action_type.value} is invalid because the payment is already {status}."
            )
            
    # Allow mock overrides via payload for testing specific cases
    mock_override = live_payment_state.get("_mock_validation_override")
    if mock_override == "UNSUPPORTED":
        return ValidationOutcome(ValidationStatus.UNSUPPORTED, "Simulated unsupported action.")
    elif mock_override == "INVALID_STATE":
        return ValidationOutcome(ValidationStatus.INVALID_STATE, "Simulated invalid state.")
        
    return ValidationOutcome(ValidationStatus.VALID, "Action is valid against mock state.")
