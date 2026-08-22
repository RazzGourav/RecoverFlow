"""
RecoverFlow API — Budget Optimizer Routes
"""


from domain.recovery.budget_optimizer import (
    AllocationResult,
    CandidateOptimizationInput,
    optimize_budget,
)
from fastapi import APIRouter, Query
from pydantic import BaseModel

router = APIRouter()

class BudgetOptimizeRequest(BaseModel):
    candidates: list[CandidateOptimizationInput]


class BudgetOptimizeResponse(BaseModel):
    allocations: list[AllocationResult]


@router.post("/optimize", response_model=BudgetOptimizeResponse)
async def optimize_budget_route(
    request: BudgetOptimizeRequest,
    budget: int = Query(..., description="Available recovery budget in paise")
):
    """
    Allocates a given budget across a batch of candidate actions based on expected net gain.
    """
    allocations = optimize_budget(
        candidates=request.candidates,
        budget_paise=budget
    )
    return BudgetOptimizeResponse(allocations=allocations)
