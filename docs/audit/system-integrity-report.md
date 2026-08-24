# System Integrity & Reproducibility Audit Report

This report provides an honest, evidence-based assessment of the RecoverFlow codebase. It investigates whether the system's claims (AI reasoning, risk scoring, budget optimization, funnel tracking) are driven by live computation or if they are faked, stubbed, or hardcoded.

## Executive Summary

The underlying domain logic for ML Inference, Risk Firewalls, and Policy execution is remarkably solid and functional. However, the **presentation layer** (UI tables, Benchmark Reports) heavily relies on unlabeled hardcoded data that does not match the actual system output. Furthermore, the live end-to-end asynchronous event pipeline is currently broken, meaning webhooks are ingested but never processed into recovery cases.

---

## Part A & B — Static Code Audit & End-to-End Runtime

### 1. Web UI & Dashboard
**Verdict:** HARDCODED (unlabeled — RED FLAG)
- **Evidence:** In `apps/web/app/cases/CasesTable.tsx`, if the API does not provide an `expected_recovery_paise` (which `apps/api/routes/cases.py` currently omits from the list endpoint), the frontend arbitrarily calculates it as: `c.amount_paise * (c.risk_level === 'HIGH' ? 0.1 : 0.8)`. 
- **Impact:** The recovery values shown in the main dashboard table are completely fabricated and not driven by the ML models.

### 2. ML Models (`analyze_case`)
**Verdict:** WORKING (real) but highly skewed.
- **Evidence:** `ai/inference/predict.py` correctly loads `recovery_xgb_v1.0.0.joblib` and `intervention_logistic_v1.0.0.joblib`. Testing with synthetic cases shows that it performs live feature engineering and outputs significantly different probabilities and recommendations based on the input features (e.g., a high-value temporary failure yields 81% recoverability, while a low-value persistent failure yields 5% recoverability).
- **Honest Assessment of Recommended Actions:** A full evaluation across the Phase 2 synthetic test dataset reveals that the Policy Engine *never* naturally selects `PAYMENT_LINK`, `INVOICE`, `REMINDER`, or `PAYMENT_METHOD_UPDATE`. The predicted probabilities are skewed such that the ranked actions always heavily favour `RETRY` (101 out of 101 cases in the test set). The model is executing live, but its training/synthetic data does not produce a diverse distribution of interventions in practice.

### 3. LLM Reasoning Layer
**Verdict:** WORKING (mocked, labeled)
- **Evidence:** `ai/inference/llm.py` contains fully implemented integrations for Gemini and OpenAI. It defaults to a mock response if `LLM_PROVIDER=mock`, which is clearly documented in `.env.example`. 

### 4. Risk Firewall (`domain/risk/checks.py`)
**Verdict:** WORKING (real)
- **Evidence:** The risk checks (`check_transaction_risk`, `check_frequency_risk`, `check_amount_risk`, etc.) are implemented as pure functions that evaluate live case data against dynamic thresholds. They calculate actual scores and generate detailed reason strings rather than returning fixed ALLOW/BLOCK responses.

### 5. Policy Engine (`domain/policies/pipeline.py`)
**Verdict:** WORKING (real)
- **Evidence:** The decision pipeline correctly orchestrates the AI recommendation and the Risk Firewall. The simulation core (`ai/evaluation/simulation_core.py`) heavily reuses this exact pipeline within a nested SQL transaction to guarantee zero side-effects.

### 6. Budget Optimizer Benchmark
**Verdict:** HARDCODED (unlabeled — RED FLAG)
- **Evidence:** The budget optimizer logic itself (`domain/recovery/budget_optimizer.py`) is real. However, the benchmark script used to generate the README metrics (`scripts/run_final_benchmark.py`) is completely faked. The script bypasses ML inference, hardcodes success probabilities (`0.75 if actually_recovered else 0.25`), invents a naive baseline (`naive_recovery = int(res_optimal.expected_recovery_paise * 0.7)`), and hardcodes perfect assertions for catch rate and funnel consistency as strings. 

### 7. Revenue Leak / Funnel Graph
**Verdict:** WORKING (real)
- **Evidence:** The `/funnel/summary` endpoint uses `SyntheticProvider.get_funnel_summary()`, which runs a live `GROUP BY` query on the `funnel_events` table in PostgreSQL to calculate stage counts and drop-off rates.

### 8. End-to-End Live Webhook Pipeline
**Verdict:** WORKING (real, verified 2026-08-24)
- **Evidence:** 7 webhooks fired via `scripts/fire_all_actions.py` (amounts 5001–5007 paise, `error_reason: network_error`). All returned HTTP 200 and were processed end-to-end through the event worker, decision pipeline, and action execution.
- **Payment Events (real query output):**
```
 external_event_id  |   event_type   |  status   | recovery_case_id
---------------------+----------------+-----------+--------------------------------------
 batch_mock_630a5cfc | payment.failed | PROCESSED | c4d965be-e8b5-4cc4-89f0-3afbae434064
 batch_mock_3af5f9b6 | payment.failed | PROCESSED | 51b26a27-d1d5-461b-9844-763e5c5821fe
 batch_mock_dd9e787d | payment.failed | PROCESSED | 5f86bee4-c65f-498a-96aa-71703a17906f
 batch_mock_deb6b785 | payment.failed | PROCESSED | 932e2344-606a-428c-ada9-55ea3e22c778
 batch_mock_13ea66a7 | payment.failed | PROCESSED | 24b66cd0-c995-41dc-8795-5335e4cf4d4c
 batch_mock_5d75a192 | payment.failed | PROCESSED | 580088fb-5ede-4bb9-b84b-4aec880d50c1
 batch_mock_4adc9f1b | payment.failed | PROCESSED | e13fa3a4-9908-460a-ab1b-daebd3358f86
(7 rows)
```
- **Recovery Cases:** All 7 events produced recovery cases with status `ACTION_INITIATED`, risk_level `LOW`, real recoverability scores (0.148), and customer_ids.
- **Customer metadata stored correctly:** `{"name": "Customer N", "email": "test@example.com", "contact": "+919876543210"}` — keys match executor expectations.

### 9. Action Executor Layer
**Verdict:** WORKING (real, verified 2026-08-24)
- **Evidence:** All 7 action types executed successfully. The testing hook (`FORCE_ACTION_TYPE_FOR_TESTING=1`) forced diverse action types based on amount_paise modulo. Real query output:
```
      action_type      | authorization_status | execution_status | provider_reference
-----------------------+----------------------+------------------+---------------------
 RETRY                 | AUTONOMOUS           | VERIFIED         | retry_mock_4ae8861c
 PAYMENT_LINK          | AUTONOMOUS           | VERIFIED         | plink_mock_8cb4b13f
 INVOICE               | AUTONOMOUS           | VERIFIED         | inv_mock_3ea67cc5
 PAYMENT_METHOD_UPDATE | AUTONOMOUS           | VERIFIED         | pmu_mock_46114d6c
 REMINDER              | AUTONOMOUS           | VERIFIED         | rem_mock_6f97861d
 HUMAN_ESCALATION      | AUTONOMOUS           | VERIFIED         | esc_mock_6452abc2
 NO_ACTION             | AUTONOMOUS           | EXECUTED         |
(7 rows)
```
- **Reconciliation:** 6 of 7 actions reached VERIFIED (reconciliation worker confirmed provider references match). NO_ACTION stays at EXECUTED (no provider reference to reconcile — correct behavior).
- **Full audit trail (PAYMENT_LINK example):**
```
       event_type        |  decision  |                reason                | action_type
-------------------------+------------+--------------------------------------+--------------
 ACTION_AUTHORIZED       | AUTONOMOUS | POLICY_CLEARED_AUTONOMOUS            | PAYMENT_LINK
 RISK_FIREWALL_EVALUATED | ALLOW      | RISK_FIREWALL_ALLOW                  | PAYMENT_LINK
 ACTION_EXECUTED         |            | Successfully generated payment link. | PAYMENT_LINK
```
- **Customer data gating works:** Customer-facing actions (PAYMENT_LINK, INVOICE, REMINDER, PAYMENT_METHOD_UPDATE) all executed because Customer records had valid `metadata_` with name/email/contact. No VALIDATION_BLOCKED events.

---

## Part C — Reproducibility Audit

**Verdict:** WORKING (real)

The system was tested for out-of-the-box reproducibility by cloning the repository to a clean temporary folder (`RecoverFlow_test`) and running the quickstart instructions exactly as documented:
1. `copy .env.example .env`
2. `docker compose up --build -d`

**Findings:**
- The Docker Compose stack builds successfully without any missing dependencies or unpinned version errors.
- The `postgres`, `redis`, `api`, `worker`, `recovery_worker`, `reconciliation_worker`, and `frontend` containers all start correctly.
- The API container properly waits for Postgres, applies Alembic migrations automatically on startup (`alembic upgrade head`), and reaches a healthy state without any manual SQL intervention.
- **Result:** The system is fully reproducible from a fresh clone with zero manual steps missing.

---

## Recommendations Before Demo Day
1. **Fix the UI API Contract:** Update `apps/api/routes/cases.py` to return the real `expected_recovery_paise` from the ML layer, and remove the hardcoded math from the React frontend.
2. **Rewrite the Benchmark Script:** If the budget optimizer is to be featured in the demo, rewrite `run_final_benchmark.py` to actually use the ML pipeline instead of hardcoded strings and fake data.
