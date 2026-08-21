"""
RecoverFlow — Tests for ML Engine and AI Decision Inference

Ensures deterministic feature engineering logic and schema-validated 
inference output (AIDecisionContract).
"""

from unittest.mock import patch

import numpy as np
import pandas as pd

from ai.features.engineer import build_features
from ai.inference.contract import AIDecisionContract
from ai.inference.predict import analyze_case


def test_feature_engineering_deterministic():
    """Ensure raw case fields map strictly to expected numeric features."""
    raw_data = [{
        "case_id": "dummy",
        "segment": "NEW",
        "tenure_days": 15,
        "amount_paise": 50000,
        "failure_type": "TEMPORARY",
        "action_taken": "RETRY"
    }]
    df = pd.DataFrame(raw_data)
    
    features = build_features(df)
    
    assert len(features) == 1
    assert features.iloc[0]["tenure_days"] == 15.0
    assert features.iloc[0]["amount_paise"] == 50000.0
    assert features.iloc[0]["segment_NEW"] == 1
    assert features.iloc[0]["segment_ESTABLISHED"] == 0
    assert features.iloc[0]["failure_type_TEMPORARY"] == 1
    assert features.iloc[0]["failure_type_PERSISTENT"] == 0


@patch("ai.inference.predict._recovery_model")
@patch("ai.inference.predict._intervention_model")
@patch("ai.inference.predict.load_models")
def test_analyze_case_contract(mock_load, mock_int, mock_rec):
    """Ensure the analyze_case entrypoint always returns a valid Pydantic contract."""
    # Mock model predict_proba to return deterministic probabilities
    mock_rec.predict_proba.return_value = np.array([[0.2, 0.8]])  # 80% recoverability
    mock_int.predict_proba.return_value = np.array([[0.3, 0.7]])  # 70% action success
    
    raw_case = {
        "case_id": "c12345",
        "segment": "ESTABLISHED",
        "tenure_days": 100,
        "amount_paise": 100000,
        "failure_type": "PAYMENT_METHOD",
        "high_frequency_contact": False,
        "requires_human_review": False
    }
    
    decision = analyze_case(raw_case)
    
    assert isinstance(decision, AIDecisionContract)
    assert decision.case_id == "c12345"
    assert decision.recoverability == 0.8
    assert decision.confidence == 0.7
    assert decision.expected_recovery == 0.7 * 100000
    assert decision.risk_level == "LOW"
    assert "RISK_NORMAL" in decision.reason_codes
    assert not decision.human_approval_required
    assert decision.model_version == "1.0.0"

def test_analyze_case_high_risk_contract():
    """Ensure risk scores bubble up to human_approval_required."""
    raw_case = {
        "case_id": "c999",
        "segment": "HIGH_VALUE",
        "tenure_days": 500,
        "amount_paise": 3_000_000,  # > 2.5m triggers HIGH risk
        "failure_type": "PERSISTENT",
    }
    
    with patch("ai.inference.predict._recovery_model") as mock_rec, \
         patch("ai.inference.predict._intervention_model") as mock_int, \
         patch("ai.inference.predict.load_models"):
             
        mock_rec.predict_proba.return_value = np.array([[0.9, 0.1]])
        mock_int.predict_proba.return_value = np.array([[0.9, 0.1]])
        
        decision = analyze_case(raw_case)
        
        assert decision.risk_level == "HIGH"
        assert decision.human_approval_required is True
        assert "RISK_HIGH_AMOUNT" in decision.reason_codes
