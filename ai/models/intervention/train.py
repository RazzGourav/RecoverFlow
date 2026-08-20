"""
Action Effectiveness Predictor Training Script

Why this exists:
  Estimates P(success | case, action) to rank interventions by expected value.
  We train a logistic regression model on case features + action taken, enabling
  the inference engine to query the model for every candidate action.
"""

import json
from pathlib import Path
import joblib
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import log_loss

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from ai.features.engineer import build_features, ACTION_TYPES

DATA_DIR = Path(__file__).resolve().parents[3] / "data" / "processed"
ARTIFACTS_DIR = Path(__file__).resolve().parents[2] / "artifacts"
ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

MODEL_VERSION = "1.0.0"


def prepare_action_features(df: pd.DataFrame) -> pd.DataFrame:
    """Enhances base features with action one-hot encoding."""
    X_base = build_features(df)
    
    # Encode the action that was actually taken in this historical data
    for action in ACTION_TYPES:
        X_base[f"action_{action}"] = (df["action_taken"] == action).astype(int)
        
    return X_base


def load_data(split_name: str) -> tuple[pd.DataFrame, pd.Series]:
    df = pd.read_csv(DATA_DIR / f"{split_name}.csv")
    if df["actually_recovered"].dtype == object:
        y = df["actually_recovered"] == "True"
    else:
        y = df["actually_recovered"].astype(bool)
        
    X = prepare_action_features(df)
    return X, y


def train_and_evaluate():
    print("Loading data for Action Effectiveness...")
    X_train, y_train = load_data("train")
    X_test, y_test = load_data("test")
    
    # We use Logistic Regression for interpretability and smooth probabilities
    print("Training Action Effectiveness model (Logistic Regression)...")
    model = LogisticRegression(class_weight="balanced", max_iter=1000, random_state=42)
    model.fit(X_train, y_train)
    
    # Evaluate calibration (Log Loss)
    y_pred_proba = model.predict_proba(X_test)[:, 1]
    loss = log_loss(y_test, y_pred_proba)
    
    metrics = {
        "log_loss": float(loss)
    }
    
    print("\n--- Action Effectiveness Evaluation ---")
    print(json.dumps(metrics, indent=2))
    
    print(f"\nSaving action artifact to {ARTIFACTS_DIR} ...")
    joblib.dump(model, ARTIFACTS_DIR / f"intervention_logistic_v{MODEL_VERSION}.joblib")
    
    with open(ARTIFACTS_DIR / f"intervention_metrics_v{MODEL_VERSION}.json", "w") as f:
        json.dump(metrics, f, indent=2)
        
    print("✅ Action effectiveness training complete.")


if __name__ == "__main__":
    # Ensure ACTION_TYPES is imported from engineer if we moved it there, 
    # but engineer.py doesn't currently export ACTION_TYPES. Let's fix that!
    from data.synthetic.generate import ACTION_TYPES
    train_and_evaluate()
