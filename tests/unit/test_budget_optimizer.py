import pytest
from domain.recovery.budget_optimizer import optimize_budget, CandidateOptimizationInput

def test_optimize_budget_greedy_allocation():
    candidates = [
        CandidateOptimizationInput(
            case_id="case_1", 
            action_type="HUMAN_ESCALATION", 
            expected_recovery_paise=10000, 
            action_cost_paise=5000  # net_gain = 5000, ratio = 1.0
        ),
        CandidateOptimizationInput(
            case_id="case_2", 
            action_type="DISCOUNT_LINK", 
            expected_recovery_paise=15000, 
            action_cost_paise=3000  # net_gain = 12000, ratio = 4.0 (Highest priority)
        ),
        CandidateOptimizationInput(
            case_id="case_3", 
            action_type="HUMAN_ESCALATION", 
            expected_recovery_paise=8000, 
            action_cost_paise=5000  # net_gain = 3000, ratio = 0.6
        )
    ]
    
    # Total cost of all is 13000. 
    # If budget is 8000, we expect case_2 (cost 3000) and case_1 (cost 5000) to be funded. case_3 is not.
    allocations = optimize_budget(candidates, budget_paise=8000)
    
    # Convert list of models to dictionary keyed by case_id for easy asserting
    alloc_dict = {a.case_id: a for a in allocations}
    
    assert alloc_dict["case_2"].funded is True
    assert alloc_dict["case_1"].funded is True
    assert alloc_dict["case_3"].funded is False


def test_optimize_budget_exhaustion():
    candidates = [
        CandidateOptimizationInput(
            case_id="case_1", 
            action_type="HUMAN_ESCALATION", 
            expected_recovery_paise=10000, 
            action_cost_paise=5000
        ),
        CandidateOptimizationInput(
            case_id="case_2", 
            action_type="HUMAN_ESCALATION", 
            expected_recovery_paise=10000, 
            action_cost_paise=5000
        )
    ]
    
    # If budget is exactly 5000, only one should be funded, the other skipped.
    allocations = optimize_budget(candidates, budget_paise=5000)
    funded_count = sum(1 for a in allocations if a.funded)
    
    assert funded_count == 1


def test_optimize_budget_zero_cost():
    candidates = [
        CandidateOptimizationInput(
            case_id="case_1", 
            action_type="RETRY", 
            expected_recovery_paise=1000, 
            action_cost_paise=0  # net_gain = 1000, ratio = inf
        ),
    ]
    
    # Should always be funded if net_gain is >= 0, even with 0 budget
    allocations = optimize_budget(candidates, budget_paise=0)
    assert allocations[0].funded is True
