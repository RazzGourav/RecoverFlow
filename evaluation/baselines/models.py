"""
RecoverFlow API — Baseline Models

Why this file exists:
  Provides deterministic baseline policies (always-retry, fixed-schedule, simple-rule)
  so that RecoverFlow's performance can be compared against what a typical
  merchant would do without AI.
"""

from typing import Literal

def compute_baseline_recovery(
    cases: list[dict], 
    baseline_type: Literal["always_retry", "fixed_schedule", "simple_rule"]
) -> dict:
    """
    Computes recovery metrics for a given baseline strategy over a list of cases.
    
    Args:
        cases: A list of dicts, each representing a failed payment case with properties:
               `amount_paise`, `failure_type`, `is_actually_recoverable` (mock ground truth for eval).
        baseline_type: Which baseline to apply.
        
    Returns:
        dict with `recovered_paise`, `attempted_cases`, `recovery_rate`.
    """
    recovered_paise = 0
    attempted_cases = 0
    
    for case in cases:
        amount = case["amount_paise"]
        is_recoverable = case.get("is_actually_recoverable", False)
        
        attempt_action = False
        
        if baseline_type == "always_retry":
            # Baseline 1: Retry every single failure regardless of reason
            attempt_action = True
            
        elif baseline_type == "fixed_schedule":
            # Baseline 2: Only retry on days 3, 5, 7. 
            # (We simulate this by assuming it attempts 50% of the time based on timing luck)
            attempt_action = True if hash(str(case.get("id", ""))) % 2 == 0 else False
            
        elif baseline_type == "simple_rule":
            # Baseline 3: Don't retry hard declines (e.g. CUSTOMER_ACTION)
            if case.get("failure_type") != "CUSTOMER_ACTION":
                attempt_action = True
                
        if attempt_action:
            attempted_cases += 1
            if is_recoverable:
                recovered_paise += amount
                
    total_amount = sum(c["amount_paise"] for c in cases)
    rate = (recovered_paise / total_amount) * 100.0 if total_amount > 0 else 0.0
    
    return {
        "baseline": baseline_type,
        "attempted_cases": attempted_cases,
        "recovered_paise": recovered_paise,
        "recovery_rate_percent": round(rate, 2)
    }
