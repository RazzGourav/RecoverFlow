"""
Recoverability Predictor Training Script

Why this exists:
  Trains models to estimate the probability that a failed payment can be
  recovered within the standard 7-day window. Includes an honest Logistic
  Regression baseline and a gradient-boosted primary model.
  Evaluates exclusively on the held-out test set to prevent data leakage.
"""

import json
from pathlib import Path
import joblib
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import precision_recall_fscore_support
from xgboost import XGBClassifier

# Imports using absolute path from root
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from ai.features.engineer import build_features

DATA_DIR = Path(__file__).resolve().parents[3] / "data" / "processed"
ARTIFACTS_DIR = Path(__file__).resolve().parents[2] / "artifacts"
ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

MODEL_VERSION = "1.0.0"


def load_data(split_name: str) -> tuple[pd.DataFrame, pd.Series]:
    """Loads CSV, returns engineered features and the target label."""
    df = pd.read_csv(DATA_DIR / f"{split_name}.csv")
    
    # Extract target
    # In synthetic generation, actually_recovered is a boolean written as True/False string or bool
    if df["actually_recovered"].dtype == object:
        y = df["actually_recovered"] == "True"
    else:
        y = df["actually_recovered"].astype(bool)
        
    X = build_features(df)
    return X, y


def train_and_evaluate():
    print("Loading data splits...")
    X_train, y_train = load_data("train")
    X_test, y_test = load_data("test")
    
    print(f"Training Baseline (Logistic Regression) on {len(X_train)} rows...")
    baseline = LogisticRegression(class_weight="balanced", max_iter=1000, random_state=42)
    baseline.fit(X_train, y_train)
    
    print("Training Primary (XGBoost) model...")
    primary = XGBClassifier(
        n_estimators=100, 
        learning_rate=0.1, 
        max_depth=4,
        random_state=42,
        use_label_encoder=False,
        eval_metric="logloss"
    )
    primary.fit(X_train, y_train)
    
    print("\n--- Evaluation on Held-Out Test Set ---")
    
    # 1. Majority Class Naive Baseline
    majority_class = y_train.mode()[0]
    y_naive = [majority_class] * len(y_test)
    n_p, n_r, n_f, _ = precision_recall_fscore_support(y_test, y_naive, average="binary", zero_division=0)
    
    # 2. Logistic Baseline
    y_base_pred = baseline.predict(X_test)
    b_p, b_r, b_f, _ = precision_recall_fscore_support(y_test, y_base_pred, average="binary")
    
    # 3. XGBoost
    y_xgb_pred = primary.predict(X_test)
    x_p, x_r, x_f, _ = precision_recall_fscore_support(y_test, y_xgb_pred, average="binary")
    
    metrics = {
        "naive_baseline": {"precision": float(n_p), "recall": float(n_r), "f1": float(n_f)},
        "logistic_baseline": {"precision": float(b_p), "recall": float(b_r), "f1": float(b_f)},
        "xgboost_primary": {"precision": float(x_p), "recall": float(x_r), "f1": float(x_f)}
    }
    
    print(json.dumps(metrics, indent=2))
    
    # Save artifacts
    print(f"\nSaving artifacts to {ARTIFACTS_DIR} ...")
    joblib.dump(baseline, ARTIFACTS_DIR / f"recovery_logistic_v{MODEL_VERSION}.joblib")
    joblib.dump(primary, ARTIFACTS_DIR / f"recovery_xgb_v{MODEL_VERSION}.joblib")
    
    with open(ARTIFACTS_DIR / f"recovery_metrics_v{MODEL_VERSION}.json", "w") as f:
        json.dump(metrics, f, indent=2)
        
    print("✅ Recoverability training complete.")


if __name__ == "__main__":
    train_and_evaluate()
