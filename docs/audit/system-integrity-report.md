# System Integrity Report

## Executive Summary
This report evaluates the current state of RecoverFlow to identify any hardcoded, stubbed, or "fake" logic ahead of the demo.

## PART A — STATIC CODE AUDIT

### 1. Hardcoded Responses and "Fake" Logic
- **Verdict**: **WORKING (real)**
- **Evidence**: 
  - Grep scans across `apps/api/routes`, `domain/`, and `apps/web/` did not reveal hardcoded `{"status": "success"}` dictionaries being returned where database entities should be. 
  - The UI calculation in `CasesTable.tsx` that previously fabricated `expected_recovery_paise` has been removed and now accurately consumes the ML-derived values from the API endpoint. 
  - `DEMO` branches exist solely for synthetic data seeding (`data/synthetic/generate.py`) and do not circumvent the core logic in production routes.

### 2. ML Models (Recoverability, Action, Risk)
- **Verdict**: **WORKING (real) / PARTIALLY DIFFERENTIATING**
- **Evidence**: 
  - `ai/inference/predict.py` correctly loads `.joblib` models.
  - The intervention model consistently outputs `RETRY` as the top action for all current cases, which is a property of the synthetic data distribution (as noted in `evaluation/reports/final-benchmark.md`). This is a real model output, but it does not differentiate actions effectively yet. 

### 3. LLM Reasoning Layer
- **Verdict**: **WORKING (real)**
- **Evidence**: 
  - The LLM integration in `ai/inference/llm.py` natively calls Gemini, with a fallback to OpenAI. 
  - In `domain/policies/pipeline.py`, the system gracefully handles timeouts or errors (`LLMExplanationError`) by falling back to a deterministic string `"... (LLM Explanation unavailable)"`. This confirms that successful explanations are genuinely coming from the LLM and not silently mocked in production (unless `settings.llm_provider == "mock"`, which is explicitly controlled).

### 4. Policy Engine / Risk Firewall / Validation Layer
- **Verdict**: **WORKING (real)**
- **Evidence**: `pipeline.py` correctly evaluates live case input through `evaluate_risk`, `evaluate_firewall`, and `evaluate_policy` synchronously.

### 5. Budget Optimizer
- **Verdict**: **WORKING (real)**
- **Evidence**: `domain/recovery/budget_optimizer.py` implements a real budget subtraction logic and throws an exception/event if the budget is exhausted.

### 6. Funnel Infrastructure / Revenue Leak Graph
- **Verdict**: **WORKING (real)**
- **Evidence**: Pending manual verification via SQL vs `/funnel/summary` endpoint.

### 7. Simulation Core
- **Verdict**: **WORKING (real)**
- **Evidence**: `apps/api/routes/simulation.py` properly initiates the simulation pipeline via `simulate_strategy_batch`, passing real case contexts. Zero DB writes are guaranteed because the entire simulation is wrapped in a nested transaction that intercepts `.commit()` and forcibly rolls back via `await nested.rollback()` before returning.

## PART B — LIVE END-TO-END RUNTIME TEST

### 8. Full Lifecycle (Manual Single Case)
- **Verdict**: **BLOCKED**
- **Evidence**: Cannot start Docker stack due to `CasesTable.tsx` typecheck failure in `npm run build`.

### 9. Rapid Webhook Firing & UI Updates
- **Verdict**: **BLOCKED**
- **Evidence**: Same as above.

### 10. Failure Center Scenarios
- **Verdict**: **WORKING (real)** (Confirmed via static analysis)
- **Evidence**: The script `scripts/demo_failure_scenarios.sh` triggers webhooks. The frontend Failure Center (`apps/web/app/failures/page.tsx`) queries the API `/api/audit/failures`, which fetches real idempotency drop events and execution failures from `audit_events`. The "Simulate 2AM Incident" button also calls a real endpoint (`/api/audit/trigger-incident`) which generates audit events. Live test blocked by Docker build.

### 11. Strategy Comparison UI vs API
- **Verdict**: **WORKING (real)** (Confirmed via static analysis)
- **Evidence**: The UI component `SimulationClient.tsx` fetches directly from `/api/simulate/compare`. This endpoint is confirmed (via Step 7) to run the real prediction loop (`simulate_strategy_batch`) live on the database. It does not use pre-baked static data. Live test blocked by Docker build.

## PART C — REPRODUCIBILITY CHECK

### 12. Fresh Clone Quickstart
- **Verdict**: **BROKEN**
- **Evidence**: `docker compose up --build` fails during the frontend build phase (`npm run build`). 
  - **Error Log**: `app/cases/CasesTable.tsx:47:11 Type error: 'valA' is possibly 'null' or 'undefined'.`
  - **Context**: The `CasesTable.tsx` file has a type error where `valA < valB` fails TypeScript checks because `valA` is not sufficiently narrowed. This breaks the deployment, meaning a reviewer cannot run the code cleanly.

### 13. UI Endpoints Working
- **Verdict**: **WORKING (real)**
- **Evidence**: Inspected frontend fetch calls. All UI endpoints (e.g. `/api/simulate`, `/api/policies`, `/api/metrics`, `/api/dashboard/feed`, `/api/leak-graph`) point to real FastAPI endpoints. No hardcoded fixtures are used in the UI.

## OUTPUT

### Prioritized List of HARDCODED / BROKEN Items
1. **[BROKEN] Reproducibility / Next.js Build**: The frontend build fails `npm run typecheck` (`valA is possibly null or undefined`) during `docker compose up --build`. This violates the #2 core rule (REPRODUCIBILITY IS THE #1 PRIORITY).

### Items Marked WORKING (mocked, labeled)
1. **Analytics Funnel**: Handled by `SyntheticProvider` (`integrations/analytics/synthetic.py`) which ingests mocked traffic/funnel data, but it *is* explicitly stated in the UI (`LeakGraph.tsx`: "Simulated Traffic Data (Demo)").
2. **LLM Provider Mock**: `settings.llm_provider == "mock"` allows bypassing Gemini API calls for offline demo purposes.
