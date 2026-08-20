"""
AI Decision Contract

Why this exists:
  Provides a strict Pydantic schema for the output of the ML engine.
  This ensures the deterministic Decision Engine downstream always receives
  exactly what it expects, preventing silent failures or type errors in the
  critical path of financial recovery.
"""

from typing import List
from pydantic import BaseModel, Field

class AIDecisionContract(BaseModel):
    case_id: str = Field(..., description="The unique UUID of the recovery case.")
    recoverability: float = Field(..., ge=0.0, le=1.0, description="P(recovery) within the window.")
    risk_score: float = Field(..., ge=0.0, le=1.0, description="Continuous risk score (currently mapped from rules).")
    risk_level: str = Field(..., description="LOW, MEDIUM, or HIGH.")
    recommended_action: str = Field(..., description="The best action determined by expected value.")
    expected_recovery: float = Field(..., description="Expected value in paise (prob * amount).")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence of the prediction.")
    human_approval_required: bool = Field(..., description="True if risk or amount requires human review.")
    reason_codes: List[str] = Field(default_factory=list, description="Audit codes explaining the decision.")
    model_version: str = Field(..., description="Version of the models used for this prediction.")
