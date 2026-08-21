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
            "reason": e.reason,
            "context": e.context,
            "timestamp": e.timestamp.isoformat()
        }
        for e in events
    ]
