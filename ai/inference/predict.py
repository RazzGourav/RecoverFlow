"""
Inference Entrypoint

Why this exists:
  Provides a single, cohesive function `analyze_case()` that orchestrates feature
  engineering, model loading, risk scoring, and action ranking to produce the final
  `AIDecisionContract`. This isolates all ML complexity from the API and Workers.
"""

import json
from pathlib import Path
from typing import Dict, Any

import joblib
import pandas as pd

from ai.features.engineer import build_features
from ai.models.risk.scorer import score_risk
from ai.inference.contract import AIDecisionContract

# In real code, ACTION_TYPES could live in a shared domain enum
ACTION_TYPES = [
    "RETRY",
    "PAYMENT_LINK",
    "INVOICE",
    "PAYMENT_METHOD_UPDATE",
    "REMINDER",
    "HUMAN_ESCALATION",
    "NO_ACTION",
]

ARTIFACTS_DIR = Path(__file__).resolve().parents[1] / "artifacts"
MODEL_VERSION = "1.0.0"

_recovery_model = None
_intervention_model = None


def load_models():
    """Lazy-loads models into memory on first inference."""
    global _recovery_model, _intervention_model
    if _recovery_model is None:
        rec_path = ARTIFACTS_DIR / f"recovery_xgb_v{MODEL_VERSION}.joblib"
        if not rec_path.exists():
            raise FileNotFoundError(f"Recovery model not found at {rec_path}. Did you run `make train`?")
        _recovery_model = joblib.load(rec_path)
        
    if _intervention_model is None:
        int_path = ARTIFACTS_DIR / f"intervention_logistic_v{MODEL_VERSION}.joblib"
        if not int_path.exists():
            raise FileNotFoundError(f"Intervention model not found at {int_path}. Did you run `make train`?")
        _intervention_model = joblib.load(int_path)


def analyze_case(case_data: Dict[str, Any]) -> AIDecisionContract:
    """
    Given raw case features, predicts recoverability and ranks actions.
    
    Args:
        case_data: Raw dictionary of case fields (matches DB schema).
        
    Returns:
        A validated AIDecisionContract ready for the Policy Engine.
    """
    load_models()
    
    # 1. Feature Engineering for Base Recoverability
    df = pd.DataFrame([case_data])
    
    # Fill required base fields if missing
    if "segment" not in df.columns:
        df["segment"] = "UNKNOWN"
    if "failure_type" not in df.columns:
        df["failure_type"] = "UNKNOWN"
    if "tenure_days" not in df.columns:
        df["tenure_days"] = 0
    if "amount_paise" not in df.columns:
        df["amount_paise"] = 0
        
    X_base = build_features(df)
    
    # Predict overall recoverability
    recoverability = float(_recovery_model.predict_proba(X_base)[0, 1])
    
    # 2. Score Risk
    risk_level, reason_codes = score_risk(case_data)
    
    # Convert risk level to a dummy continuous score for the contract
    risk_score_map = {"LOW": 0.1, "MEDIUM": 0.5, "HIGH": 0.9}
    risk_score = risk_score_map.get(risk_level, 0.5)
    
    # 3. Action Effectiveness (Evaluate all candidates)
    best_action = "NO_ACTION"
    best_prob = 0.0
    
    for action in ACTION_TYPES:
        # Create a copy of base features and inject the one-hot action
        X_action = X_base.copy()
        for a in ACTION_TYPES:
            X_action[f"action_{a}"] = 1 if a == action else 0
            
        prob = float(_intervention_model.predict_proba(X_action)[0, 1])
        if prob > best_prob:
            best_prob = prob
            best_action = action
            
    # Expected recovery
    amount = float(case_data.get("amount_paise", 0))
    expected_recovery = best_prob * amount
    
    human_approval = (risk_level == "HIGH") or case_data.get("requires_human_review", False)
    
    # 4. Construct Contract
    contract = AIDecisionContract(
        case_id=str(case_data.get("case_id", "unknown")),
        recoverability=recoverability,
        risk_score=risk_score,
        risk_level=risk_level,
        recommended_action=best_action,
        expected_recovery=expected_recovery,
        confidence=best_prob,  # Using action effectiveness as confidence heuristic
        human_approval_required=human_approval,
        reason_codes=reason_codes,
        model_version=MODEL_VERSION
    )
    
    return contract
