"""
Deterministic Feature Engineering

Why this exists:
  ML models require numeric vectors, but raw cases contain categorical strings.
  This module houses pure, side-effect-free functions to transform raw case dictionaries
  or DataFrames into model-ready feature sets. It is used identically during
  training (Phase 3) and live inference.
"""

import pandas as pd

SEGMENTS = ["NEW", "ESTABLISHED", "HIGH_VALUE"]
FAILURE_TYPES = [
    "TEMPORARY",
    "PAYMENT_METHOD",
    "PERSISTENT",
    "CUSTOMER_ACTION",
    "UNKNOWN",
]

ACTION_TYPES = [
    "RETRY",
    "PAYMENT_LINK",
    "INVOICE",
    "PAYMENT_METHOD_UPDATE",
    "REMINDER",
    "HUMAN_ESCALATION",
    "NO_ACTION",
]

def build_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Transforms a DataFrame of raw cases into numeric features.
    
    Args:
        df: A pandas DataFrame containing raw case fields.
        
    Returns:
        A pandas DataFrame of numeric features.
    """
    df_feat = pd.DataFrame(index=df.index)
    
    # 1. Numeric features (pass-through)
    df_feat["tenure_days"] = df["tenure_days"].astype(float)
    df_feat["amount_paise"] = df["amount_paise"].astype(float)
    
    # 2. One-hot encode segments
    for seg in SEGMENTS:
        df_feat[f"segment_{seg}"] = (df["segment"] == seg).astype(int)
        
    # 3. One-hot encode failure types
    for ft in FAILURE_TYPES:
        df_feat[f"failure_type_{ft}"] = (df["failure_type"] == ft).astype(int)
        
    # Ensure no NaN
    df_feat.fillna(0, inplace=True)
    
    return df_feat
