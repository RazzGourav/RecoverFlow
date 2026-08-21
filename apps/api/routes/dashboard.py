import uuid
from typing import List, Dict, Any
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from dependencies.db import get_db
from db.models import RecoveryCase, Customer, RiskLevel, CaseStatus

router = APIRouter()

@router.get("/feed", response_model=Dict[str, Any])
async def get_dashboard_feed(db: AsyncSession = Depends(get_db)):
    """
    Returns data for the Revenue Control Tower live feed.
    - recent_cases: The latest 10 recovery cases
    - high_risk_alerts: The latest 5 high-risk cases that are not recovered or suppressed
    """
    
    # 1. Recent Cases
    stmt_recent = select(RecoveryCase).options(
        selectinload(RecoveryCase.customer)
    ).order_by(RecoveryCase.created_at.desc()).limit(10)
    
    recent_result = await db.execute(stmt_recent)
    recent_cases = recent_result.scalars().all()
    
    # 2. High Risk Alerts
    stmt_alerts = select(RecoveryCase).options(
        selectinload(RecoveryCase.customer)
    ).where(
        RecoveryCase.risk_level == RiskLevel.HIGH,
        RecoveryCase.status.notin_([CaseStatus.RECOVERED, CaseStatus.SUPPRESSED, CaseStatus.UNRECOVERABLE])
    ).order_by(RecoveryCase.created_at.desc()).limit(5)
    
    alerts_result = await db.execute(stmt_alerts)
    high_risk_alerts = alerts_result.scalars().all()
    
    def serialize_case(c):
        return {
            "id": str(c.id),
            "status": c.status.value if hasattr(c.status, 'value') else c.status,
            "amount_paise": c.amount_paise,
            "risk_level": c.risk_level.value if c.risk_level and hasattr(c.risk_level, 'value') else c.risk_level,
            "customer_segment": (c.customer.segment.value if hasattr(c.customer.segment, 'value') else c.customer.segment) if c.customer else None,
            "created_at": c.created_at.isoformat()
        }
        
    return {
        "recent_cases": [serialize_case(c) for c in recent_cases],
        "high_risk_alerts": [serialize_case(c) for c in high_risk_alerts]
    }
