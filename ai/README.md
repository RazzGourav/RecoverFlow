# ai/

AI and ML modules for RecoverFlow.

This directory is intentionally empty in Phase 0.
Implementation begins in **Phase 3 (ML Engine)** and **Phase 5 (LLM Reasoning)**.

## Planned sub-modules

| Directory | Purpose | Phase |
|---|---|---|
| `models/recovery/` | Recoverability prediction model (XGBoost/LightGBM) | 3 |
| `models/intervention/` | Action effectiveness model | 3 |
| `models/risk/` | Risk scoring model | 6 |
| `features/` | Feature engineering and computation | 3 |
| `inference/` | Inference pipeline (load model, compute predictions) | 3 |
| `prompts/` | LLM prompt templates | 5 |
| `evaluation/` | Model evaluation harness | 3 |

## AI Decision Contract

Every model must produce:

```python
{
    "prediction": float,         # P(recovery within window)
    "confidence": float,         # Model calibration confidence
    "model_version": str,        # e.g. "recoverability-v1.0.0"
    "features_used": list[str],  # Feature names for explainability
    "reason_codes": list[str],   # Human-readable reason codes
}
```

The LLM **never** directly authorises financial actions.
It produces structured recommendations that the Policy Engine evaluates.
