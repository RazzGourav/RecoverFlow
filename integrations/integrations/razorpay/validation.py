"""
RecoverFlow API — Razorpay Validation Module

Why this file exists:
  Checks if a recommended action is compatible with the live Razorpay payment/subscription state.
"""

from __future__ import annotations

from db.models import ActionType
from integrations.integrations.validation import ValidationOutcome, ValidationStatus


def validate_action_against_live_state(action_type: ActionType, live_payment_state: dict) -> ValidationOutcome:
    """
    Validates whether an action is still applicable given the live state from Razorpay.
    
    Args:
        action_type: The recommended action (e.g., PAYMENT_LINK, RETRY_PAYMENT).
        live_payment_state: The dict returned by `fetch_payment` or equivalent.
        
    Returns:
        A ValidationOutcome (VALID, INVALID_STATE, UNSUPPORTED) with a reason.
    """
    if not live_payment_state:
        return ValidationOutcome(
            status=ValidationStatus.INVALID_STATE,
            reason="Cannot validate action against empty live state."
        )
        
    status = live_payment_state.get("status")
    
    # If the payment is already captured/paid, no recovery actions are valid
    if status in ("captured", "authorized", "paid"):
        if action_type != ActionType.NO_ACTION:
            return ValidationOutcome(
                status=ValidationStatus.INVALID_STATE,
                reason=f"Action {action_type.value} is invalid because the payment is already {status}."
            )
            
    # For PAYMENT_LINK actions, check if the provider supports generating links for this state
    if action_type == ActionType.PAYMENT_LINK:
        # In reality, you'd check if the invoice/payment allows a new link to be generated.
        # We assume it's valid if it failed or was created.
        if status not in ("failed", "created", "created"):
            return ValidationOutcome(
                status=ValidationStatus.INVALID_STATE,
                reason=f"Cannot send payment link when payment status is {status}."
            )
            
    if action_type == ActionType.RETRY_CHARGE:
        # RETRY_CHARGE requires a valid token/mandate and might not be supported if hard failure
        error_code = live_payment_state.get("error_code")
        if error_code in ("BAD_REQUEST_ERROR", "GATEWAY_ERROR"):
             return ValidationOutcome(
                status=ValidationStatus.UNSUPPORTED,
                reason="Direct retry is unsupported for this specific error code."
            )

    return ValidationOutcome(
        status=ValidationStatus.VALID,
        reason="Action is valid against current live state."
    )
