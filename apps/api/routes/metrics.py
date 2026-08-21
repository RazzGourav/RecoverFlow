"""
RecoverFlow API — Metrics Endpoints

Why this file exists:
  Provides the Phase 8 metrics computation endpoints. Allows querying
  Incremental Recovered Revenue, Recovery Rate, and Exception Rate.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from db.session import get_db
from db.models import Action, ReconciliationRecord, ReconciliationStatus, ActionType
from pydantic import BaseModel

router = APIRouter()

class MetricsResponse(BaseModel):
    incremental_recovered_revenue_paise: int
    recovery_rate_percent: float
    reconciliation_exception_rate_percent: float


@router.get("/", response_model=MetricsResponse)
async def get_metrics(db: AsyncSession = Depends(get_db)):
    """
    Computes system-level recovery metrics.
    """
    # 1. Incremental Recovered Revenue (Actual amount from MATCHED/PARTIAL records)
    rev_stmt = select(func.sum(ReconciliationRecord.actual_amount_paise)).where(
        ReconciliationRecord.status.in_([ReconciliationStatus.MATCHED, ReconciliationStatus.PARTIAL])
    )
    rev_result = await db.execute(rev_stmt)
    recovered_revenue = rev_result.scalar() or 0
    
    # 2. Recovery Rate (Recovered Amount / Total Expected Amount)
    expected_stmt = select(func.sum(ReconciliationRecord.expected_amount_paise))
    expected_result = await db.execute(expected_stmt)
    total_expected = expected_result.scalar() or 0
    
    recovery_rate = 0.0
    if total_expected > 0:
        recovery_rate = (recovered_revenue / total_expected) * 100.0
        
    # 3. Reconciliation Exception Rate
    total_records_stmt = select(func.count(ReconciliationRecord.id))
    total_records_result = await db.execute(total_records_stmt)
    total_records = total_records_result.scalar() or 0
    
    exception_stmt = select(func.count(ReconciliationRecord.id)).where(
        ReconciliationRecord.status == ReconciliationStatus.EXCEPTION
    )
    exception_result = await db.execute(exception_stmt)
    exceptions = exception_result.scalar() or 0
    
    exception_rate = 0.0
    if total_records > 0:
        exception_rate = (exceptions / total_records) * 100.0
        
    return MetricsResponse(
        incremental_recovered_revenue_paise=int(recovered_revenue),
        recovery_rate_percent=round(recovery_rate, 2),
        reconciliation_exception_rate_percent=round(exception_rate, 2)
    )
