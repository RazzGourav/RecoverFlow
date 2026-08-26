# Final Evaluation Benchmark Report

**Date:** 2026-08-25 20:38:23 UTC
**Commit:** 565a74d
**Test Set:** 100 held-out cases (data/processed/test.csv, fixed seed 42)
**Total Value at Risk:** ₹1,224,420.73
**Budget Cap:** ₹250.00
**Policy:** live defaults (confidence 0.80 / ₹5k autonomous / ₹25k review) — same values as Policy Studio & seed data; no benchmark-only overrides

## Strategy Comparison

| Metric | Retry Baseline | Rules Baseline (5% Discount) | RecoverFlow (AI Optimal) |
|---|---|---|---|
| **Strategy** | RETRY_PLUS_REMINDER | DISCOUNT_5 | RECOVERFLOW_OPTIMAL |
| **Cases Processed** | 100 | 100 | 100 |
| **Action Cost (₹)** | ₹0.00 | ₹61,220.58 | ₹0.00 |
| **Expected Recovery (₹)** | ₹947,468.71 | ₹920,231.50 | ₹947,468.71 |
| **Net Recovery (₹)** | ₹947,468.71 | ₹859,010.92 | ₹947,468.71 |

**Result: TIE at the top** — Retry Baseline and RecoverFlow (AI Optimal) both net ₹947,468.71. Reported exactly as measured.

**Why Retry Baseline ties RecoverFlow (cross-confirmed, not a benchmark artifact):**

The intervention model ranks RETRY as the top-scoring action for 100 of 100 held-out cases. Because RecoverFlow's 'optimal' strategy picks the argmax action per case and that argmax is always RETRY, it executes exactly what the naive always-retry baseline executes — same actions, same expected recovery, and since RETRY costs ₹0 in ACTION_COSTS, same net. This was verified against two independent input paths after fixing a feature-parity bug (build_case_context previously fed every case segment=UNKNOWN/tenure=0): (a) raw CSV features via scripts/check_distribution.py, and (b) the benchmark's own DB-seeded pipeline path via scripts/check_benchmark_feature_parity.py — both produce an identical 100% RETRY argmax distribution with fully corrected features (39 NEW / 38 ESTABLISHED / 23 HIGH_VALUE segments, tenure mean 196.7d). RETRY-dominance is therefore a property of the trained intervention model and its synthetic training data (RETRY is the most frequent successful action in training), NOT of broken benchmark inputs. Until the model differentiates between action types on real production data, RecoverFlow's 'AI optimal' adds zero recovery value over a plain retry loop; its differentiation claims for this demo rest on the policy/firewall/validation/reconciliation layers, not on action-selection intelligence.

## Sub-System Metrics (measured this run)

### 1. Authorization Routing under Live Policy Defaults
- Policy used: live defaults (confidence_threshold=0.80, max_autonomous ₹5,000, review threshold ₹25,000, retry_limit=2, cooldown=12h, contacts/72h cap=2) — identical to Policy Studio / seed data
- AUTONOMOUS: 0 / 100
- AWAITING_HUMAN: 100 / 100
- Routing reasons (from audit events):
  - (91x) POLICY_LOW_CONFIDENCE
  - (9x) POLICY_HUMAN_REVIEW_THRESHOLD_EXCEEDED

### 2. Validation Layer Catch Rate
- Stale (already-captured) cases seeded: 4; reached executor with an authorized action: 0
- Blocked by validation layer (VALIDATION_BLOCKED): 0
- **Catch Rate:** no stale cases reached the executor — not measurable this run

### 3. Reconciliation Exception Rate
- Actions reconciled against provider state: 0
- MATCHED: 0, EXCEPTION: 0, other/PENDING: 0
- **Exception Rate:** no reconciled actions this run — not measurable

### 4. Read-Only Guarantee (measured)
- Row counts before run — Actions: 189, AuditEvents: 414, ReconciliationRecords: 53
- Row counts after run  — Actions: 189, AuditEvents: 414, ReconciliationRecords: 53
- **Zero-leak proof:** PASS — all benchmark writes rolled back

