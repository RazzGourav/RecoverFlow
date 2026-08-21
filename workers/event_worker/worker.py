"""
RecoverFlow — Event Normalization Worker

Why this file exists:
  Normalizes raw `payment_events` into business domain `recovery_cases`.
  Processes events asynchronously to keep the webhook receiver fast and resilient.
"""

from __future__ import annotations

import structlog
from arq.connections import RedisSettings
from config import settings
from db.models import FailureType, PaymentEvent, PaymentEventStatus, RecoveryCase
from db.session import AsyncSessionLocal
from sqlalchemy import select

logger = structlog.get_logger(__name__)


def map_razorpay_failure(payload: dict) -> FailureType:
    """
    Map Razorpay webhook payload to our internal FailureType.
    """
    # Razorpay payload usually has error code/reason inside payload.payment.entity.error_code
    # Example:
    # {
    #   "event": "payment.failed",
    #   "payload": {
    #       "payment": {
    #           "entity": {
    #               "error_code": "BAD_REQUEST_ERROR",
    #               "error_reason": "payment_failed"
    #           }
    #       }
    #   }
    # }
    
    try:
        error_code = payload.get("payload", {}).get("payment", {}).get("entity", {}).get("error_code", "")
        error_reason = payload.get("payload", {}).get("payment", {}).get("entity", {}).get("error_reason", "")
    except Exception:
        return FailureType.UNKNOWN

    code_str = f"{error_code}:{error_reason}".lower()

    if "insufficient_funds" in code_str or "card_declined" in code_str:
        return FailureType.PAYMENT_METHOD
    elif "network_error" in code_str or "timeout" in code_str or "gateway" in code_str:
        return FailureType.TEMPORARY
    elif "account_closed" in code_str or "card_expired" in code_str or "invalid_card" in code_str:
        return FailureType.PERSISTENT
    elif "authentication_failed" in code_str or "3d_secure" in code_str or "otp" in code_str:
        return FailureType.CUSTOMER_ACTION
    
    return FailureType.UNKNOWN


async def normalize_payment_event(ctx: dict, payment_event_id: str) -> None:
    """
    Worker job: convert a PaymentEvent to a RecoveryCase.
    """
    logger.info("worker.normalize_event.started", payment_event_id=payment_event_id)
    
    async with AsyncSessionLocal() as session:
        # Fetch event
        result = await session.execute(
            select(PaymentEvent).where(PaymentEvent.id == payment_event_id)
        )
        event = result.scalar_one_or_none()
        
        if not event:
            logger.error("worker.normalize_event.not_found", payment_event_id=payment_event_id)
            return

        if event.status != PaymentEventStatus.RECEIVED:
            logger.info("worker.normalize_event.already_processed", payment_event_id=payment_event_id)
            return

        try:
            payload = event.raw_payload
            event_type = event.event_type

            # We only create recovery cases for failed payments.
            # If the event is something else, we just mark it processed.
            if event_type != "payment.failed":
                event.status = PaymentEventStatus.PROCESSED
                await session.commit()
                logger.info("worker.normalize_event.skipped_non_failure", payment_event_id=payment_event_id, event_type=event_type)
                return

            # Extract fields
            payment_entity = payload.get("payload", {}).get("payment", {}).get("entity", {})
            amount_paise = payment_entity.get("amount", 0)
            external_payment_id = payment_entity.get("id")
            
            # Map failure type
            failure_type = map_razorpay_failure(payload)

            # Create recovery case
            case = RecoveryCase(
                payment_event_id=event.id,
                external_payment_id=external_payment_id,
                amount_paise=amount_paise,
                failure_type=failure_type,
            )
            session.add(case)
            
            # Link case to event and mark processed
            await session.flush()  # to get case.id
            event.recovery_case_id = case.id
            event.status = PaymentEventStatus.PROCESSED
            
            # PHASE 4: Run Decision Pipeline
            from domain.policies.pipeline import run_decision_pipeline
            await run_decision_pipeline(session, case)
            
            await session.commit()
            logger.info("worker.normalize_event.success", payment_event_id=payment_event_id, case_id=str(case.id))

        except Exception as e:
            await session.rollback()
            event.status = PaymentEventStatus.FAILED
            session.add(event)
            await session.commit()
            logger.exception("worker.normalize_event.error", payment_event_id=payment_event_id, exc_info=e)
            raise


# ARQ worker settings
class WorkerSettings:
    redis_settings = RedisSettings.from_dsn(settings.redis_url)
    functions = [normalize_payment_event]
    max_jobs = settings.worker_concurrency
