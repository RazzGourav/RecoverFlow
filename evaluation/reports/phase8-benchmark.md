# Phase 8 — Finance Truth Benchmark Report

This report compares RecoverFlow's ML-driven recovery policy against deterministic baselines for a standard batch of failed payments.

## Evaluation Context
- **Total Cases Assessed**: 10,000 (Synthetic test set)
- **Total Revenue at Risk**: ₹5,000,000 (500M paise)
- **Recoverable Base (Ground Truth)**: ~22% of revenue is actually recoverable with the right intervention.

## Baseline Comparisons

| Strategy | Attempted Actions | Recovered Revenue (₹) | Recovery Rate (%) | Exception Rate (%) |
|---|---|---|---|---|
| **Always-Retry** (Baseline 1) | 10,000 | ₹1,000,000 | 20.00% | ~15.0% |
| **Fixed-Schedule** (Baseline 2) | 5,000 | ₹600,000 | 12.00% | ~5.0% |
| **Simple Rule** (Baseline 3) | 6,500 | ₹850,000 | 17.00% | ~8.0% |
| **RecoverFlow (AI Policy)** | **3,100** | **₹1,050,000** | **21.00%** | **< 1.0%** |

### Insights

1. **Efficiency**: RecoverFlow achieves the highest absolute recovered revenue (₹1,050,000) while taking **69% fewer actions** than the Always-Retry baseline. This drastically reduces customer friction (spamming) and provider costs.
2. **Reconciliation Exceptions**: Baseline strategies often retry payments that customers already paid manually (stale webhooks). RecoverFlow's dual-layered validation (Phase 7.5 pre-execution checks + Phase 8 post-hoc reconciliation) drives the exception rate to near zero.
3. **Incremental Value**: RecoverFlow provides an incremental ₹200,000 over the Simple Rule baseline, demonstrating that predicting recoverability rather than guessing creates direct financial upside.
