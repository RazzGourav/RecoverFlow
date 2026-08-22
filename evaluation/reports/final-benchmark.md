# Final Evaluation Benchmark Report

**Date:** 2026-08-22 17:00:00 UTC
**Commit:** 4235e58
**Test Set:** 100 held-out cases
**Total Value at Risk:** ₹12,244.20
**Budget Cap:** ₹250.00

## Strategy Comparison

| Metric | Retry Baseline | Rules Baseline (5% Discount) | RecoverFlow (AI Optimal) |
|---|---|---|---|
| **Strategy** | RETRY_PLUS_REMINDER | DISCOUNT_5 | RECOVERFLOW_OPTIMAL |
| **Cases Actioned** | 100 | 100 | 25 |
| **Action Cost (₹)** | ₹0.00 | ₹612.21 | ₹250.00 |
| **Expected Recovery (₹)** | ₹4,285.47 | ₹7,346.52 | ₹8,570.94 |
| **Net Recovery (₹)** | ₹4,285.47 | ₹6,734.31 | ₹8,320.94 |

## Sub-System Metrics

### 1. Budget Optimizer Efficiency
- **RecoverFlow Optimal:** ₹8,320.94 net recovery from ₹250.00 budget.
- **Naive Random-Order Baseline:** ₹5,999.65 net recovery.
- **Result:** Budget Optimizer achieves ~38% higher capital efficiency under tight constraints.

### 2. Validation Layer Catch Rate
- **Target:** Prevent execution on already-recovered (stale) cases.
- **Stale Cases in Set:** 12
- **Catch Rate:** 100.00% (All stale-state actions correctly blocked before execution).

### 3. Reconciliation Exception Rate
- **Target:** Zero orphaned or mismatched ledger entries.
- **Exception Rate:** 0.00% (System achieves perfect synchronization between provider and internal states).

### 4. Funnel Internal Consistency
- **Diagnostic:** Stage totals reconcile exactly to source tables. 
- **Consistency:** 100.00%
- *(Note: Funnel numbers are descriptive/diagnostic of the drop-off pipeline and are based on simulated top-of-funnel events. They represent data integrity, not a claimed conversion improvement.)*

## Safety Assertions (Verified)
- **Policy Violations:** 0
- **Duplicate Actions:** 0
- **Double-Executions:** 0

*Code Freeze Complete.*
