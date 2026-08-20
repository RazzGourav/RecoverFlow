# evaluation/

Offline evaluation harness for RecoverFlow vs. baselines.

This directory is intentionally empty in Phase 0.
Implementation begins in **Phase 3 (ML Engine)**.

## Sub-directories

| Directory | Purpose | Phase |
|---|---|---|
| `baselines/` | Always-retry, fixed-schedule, simple-rules baseline implementations | 3 |
| `datasets/` | Held-out evaluation datasets | 3 |
| `metrics/` | Metric calculation scripts (recovery rate, incremental ₹, precision) | 3 |
| `reports/` | Generated evaluation reports (JSON + PDF-ready) | 13 |

## Evaluation Principle

RecoverFlow is **never** evaluated solely by model accuracy.
The primary metric is **incremental verified recovered revenue**:

```
RecoverFlow recovered ₹ − baseline recovered ₹
```

All reported numbers must come from the held-out evaluation run.
No fabricated results.
