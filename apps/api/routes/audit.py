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
    Triggers the 2AM incident live by calling the simulate_webhook script.
    It generates a duplicate webhook and an action timeout scenario.
    """
    import subprocess
    import time
    
    test_id = f"dup_test_{int(time.time())}"
    
    # 1. Duplicate Webhook
    # First request
    subprocess.run(["python", "/app/scripts/simulate_webhook.py", "--id", test_id], capture_output=True)
    # Second request hits idempotency layer and drops
    subprocess.run(["python", "/app/scripts/simulate_webhook.py", "--id", test_id], capture_output=True)
    
    # 2. Action Timeout
    # Mock provider sleeps for 20s if customer name contains "timeout"
    subprocess.run(["python", "/app/scripts/simulate_webhook.py", "--customer-name", "timeout_test_user"], capture_output=True)
    
    return {"status": "incident_triggered", "message": "The 2AM incident scenario has been dispatched."}
