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
**Verdict:** FIXES APPLIED, NOT YET RE-VERIFIED
- **Code review (static):** The webhook ingestion route validates HMAC and persists `PaymentEvent` rows. The event worker (`workers/event_worker/worker.py`) extracts `customer_id`, `email`, `contact` from the Razorpay payload entity, creates or finds a `Customer` record, then runs the decision pipeline. The load-test scripts (`scripts/fire_all_actions.py`, `scripts/simulate_webhook.py`) send payloads whose field names (`customer_id`, `email`, `contact`, `notes.customer_name`) align with the worker's extraction logic.
- **Not yet verified at runtime:** No real load-test query output has been captured against a running stack to confirm events flow end-to-end through Redis, the event worker, decision pipeline, and action creation. This section will be updated to WORKING only after real `docker compose exec` query output is pasted here unedited.

### 9. Action Executor Layer
**Verdict:** FIXES APPLIED, NOT YET RE-VERIFIED
- **Code review (static):** The executor (`domain/finance/executor.py`) correctly gates customer-facing action types (`PAYMENT_LINK`, `INVOICE`, `REMINDER`, `PAYMENT_METHOD_UPDATE`) on the presence of a `Customer` record with a non-null `metadata_` dict. If missing, it sets `VALIDATION_BLOCKED` with reason `MISSING_CUSTOMER_DATA` instead of fabricating placeholder data. For actions that pass validation, it reads `name`, `email`, `contact` from `customer.metadata_` — matching the keys the event worker stores. The fake fallback has been removed.
- **Not yet verified at runtime:** No real execution output has been captured showing actions reaching `EXECUTED` status with `MATCHED` reconciliation. This section will be updated to WORKING only after real query output is pasted here unedited.

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
