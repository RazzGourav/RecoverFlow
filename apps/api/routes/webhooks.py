"""
RecoverFlow API — Razorpay webhook ingestion route (Phase 0 skeleton).

Why this file exists:
  Even in Phase 0 we wire up the route path so that:
  1. The OpenAPI docs show the expected interface.
  2. Integration tests can hit the endpoint.
  3. Phase 1 (payment event foundation) can implement the body without
     changing the route registration.

  Signature validation, idempotency, and event processing will be
  implemented in Phase 1.  The endpoint currently returns 501 if called
  with a real payload, making it impossible to accidentally process events
  before the safety rails exist.
"""

from __future__ import annotations

import structlog
from fastapi import APIRouter, Request, status
from fastapi.responses import JSONResponse

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post(
    "/razorpay",
    summary="Razorpay webhook receiver",
    description=(
        "Receives webhook events from Razorpay. "
        "Signature validation and event processing implemented in Phase 1."
    ),
    status_code=status.HTTP_501_NOT_IMPLEMENTED,
    include_in_schema=True,
)
async def razorpay_webhook(request: Request) -> JSONResponse:
    """
    Stub for the Razorpay webhook receiver.

    Phase 1 will add:
    - HMAC-SHA256 signature validation (FR-002)
    - Idempotency check on X-Razorpay-Event-Id (FR-003)
    - Payload persistence (FR-004)
    - Recovery case creation (FR-005)

    Returns:
        501 Not Implemented until Phase 1 is complete.
    """
    logger.info("webhook.received", path="/webhooks/razorpay", status="not_implemented")
    return JSONResponse(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        content={
            "detail": "Webhook processing not yet implemented (Phase 1).",
            "phase": "0-foundation",
        },
    )
