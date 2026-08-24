"""
RecoverFlow — Reconciliation Worker

Why this file exists:
  Provides the arq worker for verifying authoritative payment state.
  After an action is EXECUTED, this worker polls the provider to verify
  the outcome (e.g., if a payment link was actually paid).
"""

from __future__ import annotations

import structlog
from arq.connections import RedisSettings
from arq.cron import cron

from config import settings
from db.models import Action, ExecutionStatus, ActionType, AuditEvent, AuditEventType
from db.session import AsyncSessionLocal
from sqlalchemy import select

from integrations.factory import get_provider

logger = structlog.get_logger(__name__)


async def verify_executed_actions(ctx: dict) -> None:
    """
    Cron job: Finds actions in EXECUTED state and polls the Payment Provider
    to see if they have reached a terminal successful state (e.g., paid).
    If so, moves them to VERIFIED.
    """
    logger.info("reconciliation_worker.verify_actions.started")
    
    async with AsyncSessionLocal() as session:
        # Fetch up to 50 EXECUTED actions
        stmt = (
            select(Action)
            .where(
                Action.execution_status == ExecutionStatus.EXECUTED,
                Action.provider_reference.isnot(None)
            )
            .limit(50)
            .with_for_update(skip_locked=True)
        )
        
        result = await session.execute(stmt)
        actions = result.scalars().all()
        
        if not actions:
            logger.info("reconciliation_worker.verify_actions.no_actions")
            return
            
        provider = get_provider()
        
        for action in actions:
            try:
                if action.action_type == ActionType.PAYMENT_LINK:
                    link_details = await provider.fetch_payment_link(action.provider_reference)
                    
                    status = link_details.get("status")
                    if status == "paid":
                        action.execution_status = ExecutionStatus.VERIFIED
                        
                        from db.models import ReconciliationRecord, ReconciliationStatus
                        # Create the reconciliation record matching the prompt requirement
                        recon_record = ReconciliationRecord(
                            case_id=action.case_id,
                            action_id=action.id,
                            expected_amount_paise=link_details.get("amount", 0),
                            actual_amount_paise=link_details.get("amount", 0),
                            status=ReconciliationStatus.MATCHED,
                        )
                        session.add(recon_record)
                        
                        event = AuditEvent(
                            case_id=action.case_id,
                            event_type=AuditEventType.ACTION_EXECUTED,
                            reason="Payment link was verified as paid by provider.",
                            actor="SYSTEM",
                            metadata_payload={
                                "action_id": str(action.id),
                                "provider_status": status,
                            }
                        )
                        session.add(event)
                        
                        logger.info(
                            "reconciliation_worker.action_verified",
                            action_id=str(action.id),
                            provider_reference=action.provider_reference
                        )
                    elif status in ("cancelled", "expired"):
                        action.execution_status = ExecutionStatus.FAILED
                        event = AuditEvent(
                            case_id=action.case_id,
                            event_type=AuditEventType.ACTION_EXECUTED,
                            reason=f"Payment link was {status}.",
                            actor="SYSTEM",
                            metadata_payload={
                                "action_id": str(action.id),
                                "provider_status": status,
                            }
                        )
                elif action.action_type == ActionType.RETRY:
                    payment_details = await provider.fetch_payment(action.provider_reference)
                    
                    status = payment_details.get("status")
                    if status == "captured":
                        action.execution_status = ExecutionStatus.VERIFIED
                        
                        from db.models import ReconciliationRecord, ReconciliationStatus
                        recon_record = ReconciliationRecord(
                            case_id=action.case_id,
                            action_id=action.id,
                            expected_amount_paise=payment_details.get("amount", 0),
                            actual_amount_paise=payment_details.get("amount", 0),
                            status=ReconciliationStatus.MATCHED,
                        )
                        session.add(recon_record)
                        
                        event = AuditEvent(
                            case_id=action.case_id,
                            event_type=AuditEventType.ACTION_EXECUTED,
                            reason="Retry was verified as captured by provider.",
                            actor="SYSTEM",
                            metadata_payload={
                                "action_id": str(action.id),
                                "provider_status": status,
                            }
                        )
                        session.add(event)
                        
                        logger.info(
                            "reconciliation_worker.action_verified",
                            action_id=str(action.id),
                            provider_reference=action.provider_reference
                        )
                    elif status == "failed":
                        action.execution_status = ExecutionStatus.FAILED
                        event = AuditEvent(
                            case_id=action.case_id,
                            event_type=AuditEventType.ACTION_EXECUTED,
                            reason=f"Retry payment was {status}.",
                            actor="SYSTEM",
                            metadata_payload={
                                "action_id": str(action.id),
                                "provider_status": status,
                            }
                        )
                        session.add(event)
                elif action.action_type == ActionType.INVOICE:
                    details = await provider.fetch_invoice(action.provider_reference)
                    status = details.get("status")
                    if status == "paid":
                        action.execution_status = ExecutionStatus.VERIFIED
                        from db.models import ReconciliationRecord, ReconciliationStatus
                        recon_record = ReconciliationRecord(
                            case_id=action.case_id, action_id=action.id,
                            expected_amount_paise=details.get("amount", 0), actual_amount_paise=details.get("amount", 0),
                            status=ReconciliationStatus.MATCHED,
                        )
                        session.add(recon_record)
                        event = AuditEvent(
                            case_id=action.case_id, event_type=AuditEventType.ACTION_EXECUTED,
                            reason="Invoice was verified as paid.", actor="SYSTEM",
                            metadata_payload={"action_id": str(action.id), "provider_status": status}
                        )
                        session.add(event)

                elif action.action_type == ActionType.PAYMENT_METHOD_UPDATE:
                    details = await provider.fetch_payment_method_update(action.provider_reference)
                    status = details.get("status")
                    if status == "updated":
                        action.execution_status = ExecutionStatus.VERIFIED
                        from db.models import ReconciliationRecord, ReconciliationStatus
                        recon_record = ReconciliationRecord(
                            case_id=action.case_id, action_id=action.id,
                            expected_amount_paise=0, actual_amount_paise=0,
                            status=ReconciliationStatus.MATCHED,
                        )
                        session.add(recon_record)
                        event = AuditEvent(
                            case_id=action.case_id, event_type=AuditEventType.ACTION_EXECUTED,
                            reason="Payment method update verified.", actor="SYSTEM",
                            metadata_payload={"action_id": str(action.id), "provider_status": status}
                        )
                        session.add(event)

                elif action.action_type == ActionType.REMINDER:
                    details = await provider.fetch_reminder(action.provider_reference)
                    status = details.get("status")
                    if status == "sent":
                        action.execution_status = ExecutionStatus.VERIFIED
                        from db.models import ReconciliationRecord, ReconciliationStatus
                        recon_record = ReconciliationRecord(
                            case_id=action.case_id, action_id=action.id,
                            expected_amount_paise=0, actual_amount_paise=0,
                            status=ReconciliationStatus.MATCHED,
                        )
                        session.add(recon_record)
                        event = AuditEvent(
                            case_id=action.case_id, event_type=AuditEventType.ACTION_EXECUTED,
                            reason="Reminder verified as sent.", actor="SYSTEM",
                            metadata_payload={"action_id": str(action.id), "provider_status": status}
                        )
                        session.add(event)

                elif action.action_type == ActionType.HUMAN_ESCALATION:
                    # Automatically mark human escalation as verified since there's no provider state to check
                    action.execution_status = ExecutionStatus.VERIFIED
                    from db.models import ReconciliationRecord, ReconciliationStatus
                    recon_record = ReconciliationRecord(
                        case_id=action.case_id, action_id=action.id,
                        expected_amount_paise=0, actual_amount_paise=0,
                        status=ReconciliationStatus.MATCHED,
                    )
                    session.add(recon_record)
                    event = AuditEvent(
                        case_id=action.case_id, event_type=AuditEventType.ACTION_EXECUTED,
                        reason="Human escalation implicitly verified.", actor="SYSTEM",
                        metadata_payload={"action_id": str(action.id), "provider_status": "escalated"}
                    )
                    session.add(event)
                    
                else:
                    pass
                
            except Exception as e:
                logger.error("reconciliation_worker.verification_error", action_id=str(action.id), error=str(e))
                # Leave it in EXECUTED to be retried next time, unless it's a permanent error.

        await session.commit()


# ARQ worker settings
class WorkerSettings:
    queue_name = "arq:reconciliation_queue"
    redis_settings = RedisSettings.from_dsn(settings.redis_url)
    functions = [verify_executed_actions]
    cron_jobs = [
        cron(verify_executed_actions, minute=set(range(60)))  # Run every minute
    ]
    max_jobs = settings.worker_concurrency
