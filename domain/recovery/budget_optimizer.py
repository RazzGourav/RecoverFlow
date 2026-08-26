"""
RecoverFlow API — Budget Optimizer (Phase 8.5)

Why this file exists:
  Allocates a limited financial budget across a batch of candidate recovery actions.
  Uses a greedy approximation by sorting candidates by expected net gain ratio.
  
  Why Greedy?
  Given our action costs are generally a small fraction of the total budget, the 
  greedy-by-ratio approach is near-optimal. It avoids the NP-Hard overhead of an
  exact 0/1 knapsack solver, executes quickly on large batches, and is easily
  auditable/explainable.

  Note: This is an ALLOCATION layer. It determines funding eligibility. It does NOT
  bypass the Policy Engine or Risk Firewall, which evaluate actions at execution time.
"""

from typing import List
import structlog
from pydantic import BaseModel

logger = structlog.get_logger(__name__)


class CandidateOptimizationInput(BaseModel):
    case_id: str
    action_type: str
    expected_recovery_paise: int
    action_cost_paise: int
    

class AllocationResult(BaseModel):
    case_id: str
    action_type: str
    action_cost_paise: int
    expected_recovery_paise: int
    expected_net_gain_paise: int
    funded: bool


def optimize_budget(
    candidates: List[CandidateOptimizationInput],
    budget_paise: int
) -> List[AllocationResult]:
    """
    Allocates a budget across candidate actions using a greedy ratio approach.
    
    Args:
        candidates: List of CandidateOptimizationInput items.
        budget_paise: Total available budget.
        
    Returns:
        List of AllocationResult indicating which cases are funded.
    """
    annotated_candidates = []
    for cand in candidates:
        net_gain = cand.expected_recovery_paise - cand.action_cost_paise
        
        # Avoid zero division. If cost is 0, the ratio is effectively infinite if gain > 0
        if cand.action_cost_paise == 0:
            ratio = float('inf') if net_gain > 0 else -float('inf')
        else:
            ratio = net_gain / cand.action_cost_paise
            
        annotated_candidates.append({
            "cand": cand,
            "net_gain": net_gain,
            "ratio": ratio
        })
        
    # Sort descending by ratio, with deterministic tie-breakers (net gain, cost,
    # expected recovery) so allocation is reproducible across runs regardless of
    # input ordering. Candidates fully tied on all keys are interchangeable:
    # swapping them cannot change aggregate funded EV or cost.
    annotated_candidates.sort(
        key=lambda x: (
            -x["net_gain"],
            x["cand"].action_cost_paise,
            -x["cand"].expected_recovery_paise,
        ),
        reverse=False,
    )
    # Primary key: ratio descending. Re-sort stably by ratio so the tie-breaker
    # order above is preserved within equal-ratio groups.
    annotated_candidates.sort(key=lambda x: x["ratio"], reverse=True)
    
    remaining_budget = budget_paise
    allocations = []
    
    for item in annotated_candidates:
        cand = item["cand"]
        net_gain = item["net_gain"]
        cost = cand.action_cost_paise
        
        # We only fund if we have budget AND it's a net positive gain (or at least break even).
        # We also enforce that the cost fits in the remaining budget.
        if net_gain >= 0 and cost <= remaining_budget:
            funded = True
            remaining_budget -= cost
        else:
            funded = False
            
        allocations.append(
            AllocationResult(
                case_id=cand.case_id,
                action_type=cand.action_type,
                action_cost_paise=cost,
                expected_recovery_paise=cand.expected_recovery_paise,
                expected_net_gain_paise=net_gain,
                funded=funded
            )
        )
        
    return allocations
