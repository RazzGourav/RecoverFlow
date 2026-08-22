import uuid
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from dependencies.db import get_db
from db.models import AuditEvent

router = APIRouter()

@router.get("/", response_model=List[Dict[str, Any]])
async def list_audit_events(
    case_id: Optional[uuid.UUID] = None,
    event_type: Optional[str] = None,
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

@router.get("/failures", response_model=List[Dict[str, Any]])
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
        AuditEventType.POLICY_DENIED,
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
