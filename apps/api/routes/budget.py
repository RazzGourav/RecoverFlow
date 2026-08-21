"""
RecoverFlow API — Budget Optimizer Routes
"""

from fastapi import APIRouter, Query
from pydantic import BaseModel
from typing import List

from domain.recovery.budget_optimizer import (
    optimize_budget, 
    CandidateOptimizationInput, 
    AllocationResult
)

router = APIRouter()

class BudgetOptimizeRequest(BaseModel):
    candidates: List[CandidateOptimizationInput]


class BudgetOptimizeResponse(BaseModel):
    allocations: List[AllocationResult]


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
