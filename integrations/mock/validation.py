"""
RecoverFlow API — Mock Validation Module

Why this file exists:
  Provides a deterministic validation layer for testing the state machine,
  mirroring `razorpay/validation.py`.
"""

from __future__ import annotations

import structlog
from db.models import ActionType
from integrations.validation import ValidationOutcome, ValidationStatus

logger = structlog.get_logger(__name__)

def validate_action_against_live_state(action_type: ActionType, live_payment_state: dict) -> ValidationOutcome:
    """
    Mock validation logic.
    """
    logger.info("validation.started", action_type=action_type.value if hasattr(action_type, "value") else str(action_type), live_state=live_payment_state)
    
    if not live_payment_state:
        logger.info("validation.result", outcome="INVALID_STATE", reason="Missing live state.")
        return ValidationOutcome(ValidationStatus.INVALID_STATE, "Missing live state.")
        
    status = live_payment_state.get("status")
    
    # Simulate a race condition where the payment was already captured
    if status in ("captured", "authorized", "paid"):
        if action_type != ActionType.NO_ACTION:
            logger.info("validation.result", outcome="INVALID_STATE", reason=f"Action invalid because payment is already {status}.")
            return ValidationOutcome(
                ValidationStatus.INVALID_STATE,
                f"Action {action_type.value if hasattr(action_type, 'value') else action_type} is invalid because the payment is already {status}."
            )
            
    # Allow mock overrides via payload for testing specific cases
    mock_override = live_payment_state.get("_mock_validation_override")
    if mock_override == "UNSUPPORTED":
        logger.info("validation.result", outcome="UNSUPPORTED", reason="Simulated unsupported action.")
        return ValidationOutcome(ValidationStatus.UNSUPPORTED, "Simulated unsupported action.")
    elif mock_override == "INVALID_STATE":
        logger.info("validation.result", outcome="INVALID_STATE", reason="Simulated invalid state.")
        return ValidationOutcome(ValidationStatus.INVALID_STATE, "Simulated invalid state.")
        
    logger.info("validation.result", outcome="VALID", reason="Action is valid against mock state.")
    return ValidationOutcome(ValidationStatus.VALID, "Action is valid against mock state.")
