import uuid
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import AuditEvent
from dependencies.db import get_db

router = APIRouter()

@router.get("/", response_model=list[dict[str, Any]])
async def list_audit_events(
    case_id: uuid.UUID | None = None,
    event_type: str | None = None,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    """
    Get the audit trail, optionally filtered by case_id.
    """
    stmt = select(AuditEvent).order_by(AuditEvent.timestamp.desc()).limit(limit)

    if case_id:
        stmt = stmt.where(AuditEvent.case_id == case_id)
    if event_type:
        stmt = stmt.where(AuditEvent.event_type == event_type)

    result = await db.execute(stmt)
    events = result.scalars().all()

    return [
        {
            "id": str(e.id),
            "case_id": str(e.case_id) if e.case_id else None,
            "event_type": e.event_type.value if hasattr(e.event_type, 'value') else e.event_type,
            "model_version": e.model_version,
            "policy_version": e.policy_version,
            "decision": e.decision,
        }
        for e in events
    ]

@router.get("/failures", response_model=list[dict[str, Any]])
async def list_failures(
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    """
    Get the failure timeline for the Failure Center.
    """
    from db.models import AuditEventType

    failure_types = [
        AuditEventType.WEBHOOK_DUPLICATE_DROPPED,
        AuditEventType.VALIDATION_BLOCKED,
        AuditEventType.ACTION_TIMEOUT,
        AuditEventType.RECONCILIATION_EXCEPTION,
        AuditEventType.BUDGET_EXHAUSTED,
        AuditEventType.RISK_FIREWALL_BLOCKED,
        AuditEventType.ACTION_BLOCKED,
        AuditEventType.LLM_EXPLANATION_FAILED,
    ]

    stmt = (
        select(AuditEvent)
        .where(AuditEvent.event_type.in_(failure_types))
        .order_by(AuditEvent.timestamp.desc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    events = result.scalars().all()

    return [
        {
            "id": str(e.id),
            "case_id": str(e.case_id) if e.case_id else None,
            "event_type": e.event_type.value if hasattr(e.event_type, 'value') else str(e.event_type),
            "model_version": e.model_version,
            "policy_version": e.policy_version,
            "decision": e.decision,
            "reason": e.reason,
            "context": e.context,
            "timestamp": e.timestamp.isoformat()
        }
        for e in events
    ]

@router.post("/trigger-incident", response_model=dict[str, Any])
async def trigger_2am_incident():
    """
    Triggers the 2AM incident scenario for the Failure Center demo.

    Why non-blocking: the original implementation used subprocess.run() (blocking)
    inside an async FastAPI route, which stalled the event loop for 30+ seconds
    while three simulate_webhook.py processes ran sequentially. From the browser's
    perspective the fetch appeared to hang indefinitely, so the UI success/error
    banners never appeared.

    Fix: use asyncio.create_subprocess_exec() to fire all three subprocesses
    concurrently and await them without blocking the event loop. Typical response
    time drops from 30s → 3-5s, well within the browser's default timeout.
    """
    import asyncio
    import time
    from config import settings

    test_id = f"dup_test_{int(time.time())}"
    secret = settings.razorpay_webhook_secret
    script = "/app/scripts/simulate_webhook.py"

    async def run_webhook(*extra_args: str) -> None:
        """Spawn simulate_webhook.py as a non-blocking subprocess."""
        proc = await asyncio.create_subprocess_exec(
            "python3", script, "--secret", secret, *extra_args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await proc.communicate()  # wait without blocking event loop

    async def run_all():
        # 1. Duplicate webhook pair — first fires normally, second hits idempotency layer
        await run_webhook("--id", test_id)
        await run_webhook("--id", test_id)

        # 2. Action timeout scenario — customer name convention triggers mock provider delay
        await run_webhook("--customer-name", "timeout_test_user")

    # Fire and forget
    asyncio.create_task(run_all())

    return {
        "status": "incident_triggered",
        "message": "2AM incident scenario dispatched: duplicate webhook + idempotency drop + action timeout.",
    }
