import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from apps.api.db.database import get_db
from apps.api.db.models import RecoveryCase, CaseStatus
from ai.evaluation.simulation_core import simulate_strategy_batch, SimulationResult

router = APIRouter(prefix="/simulate", tags=["simulation"])

class SimulationCompareRequest(BaseModel):
    case_ids: Optional[List[uuid.UUID]] = None
    sample_size: int = 100
    budget_paise: int = 500000  # Default 5,000 INR

class StrategyComparisonResult(SimulationResult):
    vs_optimal_paise: int

class SimulationCompareResponse(BaseModel):
    results: List[StrategyComparisonResult]

@router.post("/compare", response_model=SimulationCompareResponse)
async def compare_strategies(
    request: SimulationCompareRequest,
    session: AsyncSession = Depends(get_db)
):
    """
    Simulates a batch of cases across multiple strategies and compares the outcomes.
    """
    case_ids = request.case_ids
    if not case_ids:
        # Sample OPEN cases if none provided
        stmt = select(RecoveryCase.id).where(RecoveryCase.status == CaseStatus.OPEN).limit(request.sample_size)
        result = await session.execute(stmt)
        case_ids = list(result.scalars().all())

    if not case_ids:
        raise HTTPException(status_code=400, detail="No cases available for simulation.")

    strategies = [
        "RECOVERFLOW_OPTIMAL",
        "REMINDER_ONLY",
        "DISCOUNT_5",
        "DISCOUNT_10",
        "RETRY_PLUS_REMINDER",
        "DO_NOTHING"
    ]

    sim_results = []
    
    # We must run these sequentially or in a way that respects the DB connection/transaction.
    # Since they use nested transactions on the same session, sequential is safest.
    for strategy in strategies:
        try:
            res = await simulate_strategy_batch(
                session=session,
                case_ids=case_ids,
                strategy=strategy,
                budget_paise=request.budget_paise
            )
            sim_results.append(res)
        except Exception as e:
            import traceback
            traceback.print_exc()
            raise HTTPException(status_code=500, detail=f"Simulation failed for strategy {strategy}: {str(e)}")
            
    # Find OPTIMAL net recovery for comparison
    optimal_net = next((r.net_recovery_paise for r in sim_results if r.strategy == "RECOVERFLOW_OPTIMAL"), 0)
    
    final_results = []
    for r in sim_results:
        final_results.append(
            StrategyComparisonResult(
                strategy=r.strategy,
                expected_recovery_paise=r.expected_recovery_paise,
                cost_paise=r.cost_paise,
                net_recovery_paise=r.net_recovery_paise,
                cases_processed=r.cases_processed,
                vs_optimal_paise=r.net_recovery_paise - optimal_net
            )
        )
        
    return SimulationCompareResponse(results=final_results)
