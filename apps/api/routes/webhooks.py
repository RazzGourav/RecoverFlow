"""
RecoverFlow API — Razorpay webhook ingestion route.

Why this file exists:
  Ingests webhooks from Razorpay, validates the signature, ensures idempotency,
  persists the raw event, and enqueues it for asynchronous normalization.
"""

from __future__ import annotations

import hashlib
import hmac
import json

import structlog
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from db.models import PaymentEvent, PaymentEventStatus, AuditEvent, AuditEventType
from dependencies.db import get_db

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


def verify_razorpay_signature(payload: bytes, signature: str | None, secret: str) -> bool:
    """
    Verify the Razorpay webhook signature using HMAC SHA256.
    """
    if not signature:
        return False
    expected_mac = hmac.new(
        secret.encode("utf-8"), payload, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected_mac, signature)


@router.post(
    "/razorpay",
    summary="Razorpay webhook receiver",
    description="Receives, validates, and persists Razorpay webhook events securely.",
    status_code=status.HTTP_200_OK,
)
async def razorpay_webhook(
    request: Request,
    x_razorpay_signature: str | None = Header(None),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """
    Process inbound Razorpay webhooks securely.
    """
    # 1. Read raw body and validate signature (FR-002)
    raw_body = await request.body()

    # We must skip signature validation if the secret is explicitly "REPLACE_ME"
    # and we are running tests or local dev (without real razorpay setup).
    if settings.razorpay_webhook_secret != "REPLACE_ME":
        is_valid = verify_razorpay_signature(
            raw_body, x_razorpay_signature, settings.razorpay_webhook_secret
        )
        if not is_valid:
            logger.warning("webhook.invalid_signature", signature=x_razorpay_signature)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid webhook signature",
            )
    else:
        logger.warning("webhook.signature_check_bypassed", reason="secret is REPLACE_ME")

    # 2. Parse JSON
    try:
        payload = json.loads(raw_body)
    except json.JSONDecodeError:
        logger.warning("webhook.invalid_json")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON payload",
        )

    # 3. Extract event ID and type
    # If the payload is wrapped in a `contains` key or just top level, Razorpay sends:
    # { "event": "payment.failed", "contains": [...], "payload": { ... } }
    # Plus it sends the Razorpay-Event-Id header. Let's use the header or the payload.
    # Actually, Razorpay sends X-Razorpay-Event-Id header.
    # But usually it's also safer to grab it from headers.
    event_id = request.headers.get("X-Razorpay-Event-Id")
    if not event_id:
        logger.warning("webhook.missing_event_id")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing X-Razorpay-Event-Id header",
        )

    event_type = payload.get("event")
    if not event_type:
        logger.warning("webhook.missing_event_type")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing event type in payload",
        )

    # 4. Compute payload hash
    payload_hash = hashlib.sha256(raw_body).hexdigest()

    # 5. Idempotent persistence (FR-003, FR-004)
    event_record = PaymentEvent(
        external_event_id=event_id,
        event_type=event_type,
        payload_hash=payload_hash,
        raw_payload=payload,
        status=PaymentEventStatus.RECEIVED,
    )
    db.add(event_record)

    try:
        await db.commit()
    except IntegrityError:
        # Idempotency constraint hit (external_event_id is unique)
        await db.rollback()
        logger.info("webhook.duplicate_ignored", external_event_id=event_id)
        
        # Log to AuditEvents for Failure Center visibility
        audit = AuditEvent(
            event_type=AuditEventType.WEBHOOK_DUPLICATE_DROPPED,
            context={"external_event_id": event_id, "event_type": event_type}
        )
        db.add(audit)
        await db.commit()
        
        return JSONResponse(status_code=status.HTTP_200_OK, content={"status": "duplicate"})

    # 6. Enqueue normalization job to ARQ (FR-005)
    pool = getattr(request.app.state, "arq_pool", None)
    if pool:
        await pool.enqueue_job(
            "normalize_payment_event",
            payment_event_id=str(event_record.id),
        )
        logger.info("webhook.enqueued", external_event_id=event_id, internal_id=str(event_record.id))
    else:
        logger.warning("webhook.arq_pool_missing", external_event_id=event_id)

    return JSONResponse(status_code=status.HTTP_200_OK, content={"status": "received"})
