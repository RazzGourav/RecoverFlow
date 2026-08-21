"""
RecoverFlow API — Action Executor

Why this file exists:
  Provides the deterministic execution state machine for actions. It acts as
  a bridge between the Policy Engine's decision (`Action` row in DB) and
  the external `PaymentProvider`.
  It guarantees that only AUTONOMOUS or APPROVED actions are executed, and
  handles exceptions/network failures idempotently.
"""

import uuid

import structlog
from integrations.factory import get_provider
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from apps.api.db.models import (
    Action,
    ActionType,
    AuditEvent,
    AuditEventType,
    AuthorizationStatus,
    ExecutionStatus,
    RecoveryCase,
)

logger = structlog.get_logger()


async def execute_action(session: AsyncSession, action_id: uuid.UUID) -> Action:
    """
    Executes a PENDING action via the payment provider.

    Args:
        session: Active SQLAlchemy async session.
        action_id: UUID of the action to execute.

    Returns:
        The updated Action object.

    Raises:
        ValueError: If the action is not in a valid state to be executed.
        Exception: If the provider call fails (the action is marked FAILED).
    """
    # 1. Fetch action with related case and customer details
    stmt = (
        select(Action)
        .options(
            joinedload(Action.case).joinedload(RecoveryCase.customer),
            joinedload(Action.case).joinedload(RecoveryCase.merchant),
        )
        .where(Action.id == action_id)
        .with_for_update()  # Lock row to prevent concurrent execution
    )
    result = await session.execute(stmt)
    action = result.scalar_one_or_none()

    if not action:
        raise ValueError(f"Action {action_id} not found.")

    # 2. Guardrails: State machine checks & Idempotency
    if action.execution_status in (ExecutionStatus.EXECUTED, ExecutionStatus.VERIFIED):
        logger.info("action_already_executed", action_id=str(action_id), status=action.execution_status)
        return action
        
    if action.provider_reference:
        logger.info("action_has_provider_reference", action_id=str(action_id), provider_reference=action.provider_reference)
        # Even if status is not EXECUTED for some reason, if it has a provider reference, it was executed.
        # Self-correcting state
        action.execution_status = ExecutionStatus.EXECUTED
        await session.commit()
        return action

    if action.execution_status != ExecutionStatus.PENDING:
        raise ValueError(
            f"Action {action_id} has invalid execution status: {action.execution_status}"
        )

    if action.authorization_status not in (
        AuthorizationStatus.AUTONOMOUS,
        AuthorizationStatus.APPROVED,
    ):
        raise ValueError(
            f"Action {action_id} is not authorized for execution (status: {action.authorization_status})"
        )

    # 3. Execution Phase
    case = action.case
    customer = case.customer

    logger.info(
        "executing_action",
        action_id=str(action_id),
        action_type=action.action_type.value,
        case_id=str(case.id),
    )

    action.execution_status = ExecutionStatus.EXECUTING
    await session.commit()

    provider = get_provider()

    try:
        import asyncio
        if action.action_type == ActionType.PAYMENT_LINK:
            # Prepare payload for payment link
            customer_details = {
                "name": customer.name or "Customer",
                "email": customer.email,
                "contact": customer.phone or "",
            }
            description = f"Payment for subscription recovery (Case {case.id})"
            
            # Use idempotency key as reference_id to ensure safe retries on the provider side
            reference_id = action.idempotency_key

            # Provider calls are async. Apply a timeout to protect our system.
            provider_ref = await asyncio.wait_for(
                provider.create_payment_link(
                    amount_paise=case.amount_paise,
                    currency=case.currency,
                    description=description,
                    customer_details=customer_details,
                    reference_id=reference_id,
                ),
                timeout=15.0
            )
            
            action.provider_reference = provider_ref
            action.execution_status = ExecutionStatus.EXECUTED
            reason_msg = "Successfully generated payment link."

        elif action.action_type == ActionType.NO_ACTION:
            action.execution_status = ExecutionStatus.EXECUTED
            reason_msg = "No action executed."

        else:
            raise NotImplementedError(
                f"Action type {action.action_type} is not yet supported for automated execution."
            )

        # 4. Success Audit Log
        event = AuditEvent(
            case_id=case.id,
            event_type=AuditEventType.ACTION_EXECUTED,
            reason=reason_msg,
            actor="SYSTEM",
            metadata_payload={
                "action_id": str(action.id),
                "action_type": action.action_type.value,
                "provider_reference": action.provider_reference,
            },
        )
        session.add(event)
        await session.commit()
        
        logger.info(
            "action_executed_successfully",
            action_id=str(action_id),
            provider_reference=action.provider_reference,
        )

    except asyncio.TimeoutError as e:
        logger.error(
            "action_execution_timeout",
            action_id=str(action_id),
            exc_info=True,
        )
        await session.rollback()
        
        action.execution_status = ExecutionStatus.TIMED_OUT
        session.add(action)
        
        event = AuditEvent(
            case_id=case.id,
            event_type=AuditEventType.ACTION_EXECUTED,
            reason=f"Execution timed out.",
            actor="SYSTEM",
            metadata_payload={
                "action_id": str(action.id),
                "action_type": action.action_type.value,
                "error": "TimeoutError",
            },
        )
        session.add(event)
        await session.commit()
        
        # Don't raise, we handled it as an expected exception state
        return action

    except Exception as e:
        logger.error(
            "action_execution_failed",
            action_id=str(action_id),
            error=str(e),
            exc_info=True,
        )
        # Rollback any uncommitted changes from the try block
        await session.rollback()
        
        # Re-fetch or reuse object to mark as EXCEPTION
        action.execution_status = ExecutionStatus.EXCEPTION
        session.add(action)
        
        event = AuditEvent(
            case_id=case.id,
            event_type=AuditEventType.ACTION_EXECUTED,  # Or a specific failed event type if defined
            reason=f"Execution failed with exception: {str(e)[:200]}",
            actor="SYSTEM",
            metadata_payload={
                "action_id": str(action.id),
                "action_type": action.action_type.value,
                "error": str(e),
            },
        )
        session.add(event)
        await session.commit()
        
        return action

    return action
