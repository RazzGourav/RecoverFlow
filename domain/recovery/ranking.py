"""
Candidate Action Ranking

Why this exists:
  Computes Expected Value (EV = Amount * P(Success)) for all candidate actions
  using the AI Engine's probability outputs. Ranks them highest-EV first.
  This ensures we always attempt the most profitable recovery path first.
"""


from pydantic import BaseModel


class RankedAction(BaseModel):
    action_type: str
    success_probability: float
    expected_value_paise: float
    rank: int


def rank_candidate_actions(
    amount_paise: int, action_probabilities: dict[str, float]
) -> list[RankedAction]:
    """
    Ranks actions strictly by Expected Value (Amount * P(Success)).
    
    Args:
        amount_paise: The payment amount in paise.
        action_probabilities: A dict mapping action_type (str) to P(Success) (float).
        
    Returns:
        A sorted list of RankedAction objects (highest EV first).
    """
    candidates = []
    
    for action, prob in action_probabilities.items():
        ev = amount_paise * prob
        candidates.append({
            "action_type": action,
            "success_probability": prob,
            "expected_value_paise": ev
        })
        
    # Sort descending by EV
    candidates.sort(key=lambda x: x["expected_value_paise"], reverse=True)
    
    # Assign ranks
    ranked_actions = []
    for i, c in enumerate(candidates):
        ranked_actions.append(
            RankedAction(
                action_type=c["action_type"],
                success_probability=c["success_probability"],
                expected_value_paise=c["expected_value_paise"],
                rank=i + 1
            )
        )
        
    return ranked_actions
