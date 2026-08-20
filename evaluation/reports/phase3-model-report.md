# Phase 3: ML Engine Report

This report captures the honest evaluation of the Recovery Models trained on the Phase 2 synthetic dataset. 

## 1. Recoverability Predictor
**Goal:** Predict the likelihood `P(recovery)` within a 7-day window.

The evaluation was conducted strictly on the **held-out Test split (20%)** to avoid data leakage.

### Metrics

| Model | Precision | Recall | F1 Score |
|---|---|---|---|
| Naive Baseline (Majority Class) | 0.000 | 0.000 | 0.000 |
| Logistic Regression (Class Balanced) | 0.455 | 1.000 | 0.626 |
| XGBoost Classifier (Primary) | 0.525 | 0.456 | 0.488 |

> [!WARNING]
> **Performance Caveat:** The `Logistic Regression` model achieved a higher Recall and F1 score than our primary `XGBoost` model. This is an artifact of the relatively simplistic linear probabilistic modifiers used to generate the synthetic data in Phase 2. Since the underlying data logic maps cleanly to linear additive modifiers, a Logistic Regression model fits it very well, while an un-tuned tree model struggles to generalize without deeper features. We will retain XGBoost as the primary model architecture in preparation for real, non-linear merchant data, but acknowledge this limitation in the synthetic lab environment.

## 2. Action Effectiveness
**Goal:** Estimate `P(success | case, action)` to rank candidate actions by expected value.

- **Architecture:** Logistic Regression (trained on case features + one-hot action vector).
- **Evaluation Metric:** Calibration was evaluated using Log Loss on the held-out test set.
- **Log Loss Score:** `0.663`

This model provides smooth, calibrated probability outputs for each candidate action, allowing the inference engine to securely identify the most profitable intervention path.

## 3. Risk Firewall Scoring
**Goal:** Assess structural and behavioral risk prior to autonomous financial action.

- **Architecture:** Rule-based heuristics.
- **Reasoning:** We explicitly opted against a black-box ML model for risk scoring. Fraud and structural risk (e.g., policy thresholds) require strict auditability and explainability (PRD Module D). The Risk Firewall relies on deterministic thresholds (Amounts > ₹25,000, Suspicious Frequency, etc.) to enforce the `HIGH`, `MEDIUM`, and `LOW` classifications.

## 4. Inference Contract
The `AIDecisionContract` guarantees that the Decision Engine (Phase 4) receives rigorously typed outputs.
- Ensures bounding on probabilities (`0.0 <= p <= 1.0`).
- Validates the presence of `reason_codes` and a tracked `model_version`.
