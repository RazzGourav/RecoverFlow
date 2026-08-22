"""
RecoverFlow API — Finance Truth Layer

Why this file exists:
  Provides the deterministic reconciliation logic. A successful action (e.g. 
  "payment link sent") does not mean revenue was recovered. This module compares
  the expected outcome against the ground truth from the Payment Provider.
"""

import uuid
import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from db.models import (
    Action,
    ActionType,
    ExecutionStatus,
    ReconciliationRecord,
    ReconciliationStatus,
    RecoveryCase,
)
from integrations.integrations.factory import get_provider

logger = structlog.get_logger(__name__)


async def reconcile_action(session: AsyncSession, action_id: uuid.UUID) -> ReconciliationRecord:
    """
    Reconciles an executed action against the live payment provider state.
    
    Args:
        session: Active async SQLAlchemy session.
        action_id: UUID of the Action to reconcile.
        
    Returns:
        The created or updated ReconciliationRecord.
    """
    stmt = (
        select(Action)
        .options(joinedload(Action.case))
        .where(Action.id == action_id)
        .with_for_update()
    )
    result = await session.execute(stmt)
    action = result.scalar_one_or_none()
    
    if not action:
        raise ValueError(f"Action {action_id} not found.")
        
    if action.execution_status not in (ExecutionStatus.EXECUTED, ExecutionStatus.VERIFIED):
        raise ValueError(f"Cannot reconcile action in state: {action.execution_status}")
        
    case = action.case
    provider = get_provider()
    
    # Check if a reconciliation record already exists
    rec_stmt = select(ReconciliationRecord).where(ReconciliationRecord.action_id == action_id)
    rec_result = await session.execute(rec_stmt)
    record = rec_result.scalar_one_or_none()
    
    if not record:
        record = ReconciliationRecord(
            case_id=case.id,
            action_id=action.id,
            expected_amount_paise=case.amount_paise,
            status=ReconciliationStatus.PENDING,
        )
        session.add(record)
        
    if action.action_type == ActionType.PAYMENT_LINK:
        if not action.provider_reference:
            record.status = ReconciliationStatus.EXCEPTION
            record.exception_reason = "No provider_reference found for PAYMENT_LINK action."
            await session.commit()
            return record
            
        try:
            link_details = await provider.fetch_payment_link(action.provider_reference)
            status = link_details.get("status")
            amount_paid = link_details.get("amount_paid", 0)
            
            record.actual_amount_paise = amount_paid
            
            if status == "paid":
                if amount_paid == record.expected_amount_paise:
                    record.status = ReconciliationStatus.MATCHED
                elif amount_paid > 0:
                    record.status = ReconciliationStatus.PARTIAL
                    record.exception_reason = f"Expected {record.expected_amount_paise}, but got {amount_paid}."
                else:
                    record.status = ReconciliationStatus.EXCEPTION
                    record.exception_reason = "Provider reported 'paid' but amount_paid is 0."
            elif status in ("cancelled", "expired"):
                record.status = ReconciliationStatus.EXCEPTION
                record.exception_reason = f"Payment link was {status}."
            else:
                # Still pending
                record.status = ReconciliationStatus.PENDING
                
            # --- Stale Webhook / Already Paid Defense (Post-hoc) ---
            # If the original case payment was already paid out of band, it's an exception, not an incremental recovery.
            # We fetch the live state of the original case payment.
            if case.external_payment_id:
                live_case_payment = await provider.fetch_payment(case.external_payment_id)
                if live_case_payment.get("status") in ("captured", "authorized", "paid"):
                    record.status = ReconciliationStatus.EXCEPTION
                    record.exception_reason = "Stale-webhook defense: Original payment was already successful. This recovery action was redundant."
                    
        except Exception as e:
            logger.error("reconciliation.failed", action_id=str(action_id), error=str(e))
            record.status = ReconciliationStatus.EXCEPTION
            record.exception_reason = f"Provider API error: {str(e)}"
            
    elif action.action_type == ActionType.NO_ACTION:
        record.actual_amount_paise = 0
        record.status = ReconciliationStatus.MATCHED
        record.exception_reason = "NO_ACTION always yields 0 recovery."
        
    else:
        record.status = ReconciliationStatus.EXCEPTION
        record.exception_reason = f"Reconciliation not implemented for action type: {action.action_type}"

    await session.commit()
    return record
