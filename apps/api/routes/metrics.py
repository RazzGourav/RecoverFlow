"""
RecoverFlow API — Metrics Endpoints

Why this file exists:
  Provides the Phase 8 metrics computation endpoints. Allows querying
  Incremental Recovered Revenue, Recovery Rate, and Exception Rate.
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Action, CandidateAction, CaseStatus, ReconciliationRecord, ReconciliationStatus, RecoveryCase
from dependencies.db import get_db

router = APIRouter()

class MetricsResponse(BaseModel):
    incremental_recovered_revenue_paise: int
    recovery_rate_percent: float
    reconciliation_exception_rate_percent: float
    total_revenue_at_risk_paise: int
    active_cases: int
    budget_remaining_paise: int

@router.get("", response_model=MetricsResponse)
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
        
    # 4. Total Revenue at Risk
    risk_stmt = select(func.sum(RecoveryCase.amount_paise)).where(
        RecoveryCase.status != CaseStatus.RECOVERED
    )
    risk_result = await db.execute(risk_stmt)
    total_risk = risk_result.scalar() or 0
    
    # 5. Active Cases
    active_stmt = select(func.count(RecoveryCase.id)).where(
        RecoveryCase.status.in_([CaseStatus.OPEN, CaseStatus.ANALYZING, CaseStatus.AWAITING_APPROVAL, CaseStatus.ACTION_INITIATED, CaseStatus.VERIFYING])
    )
    active_result = await db.execute(active_stmt)
    active_cases = active_result.scalar() or 0

    # 6. Budget Remaining (Fixed budget of 50000 paise for demo purposes minus spent)
    budget_cap = 50000 
    spent_stmt = (
        select(func.sum(CandidateAction.action_cost_paise))
        .select_from(Action)
        .join(CandidateAction, (Action.case_id == CandidateAction.case_id) & (Action.action_type == CandidateAction.action_type))
    )
    spent_result = await db.execute(spent_stmt)
    spent = spent_result.scalar() or 0
    budget_remaining = max(0, budget_cap - spent)

    return MetricsResponse(
        incremental_recovered_revenue_paise=int(recovered_revenue),
        recovery_rate_percent=round(recovery_rate, 2),
        reconciliation_exception_rate_percent=round(exception_rate, 2),
        total_revenue_at_risk_paise=int(total_risk),
        active_cases=int(active_cases),
        budget_remaining_paise=int(budget_remaining)
    )
