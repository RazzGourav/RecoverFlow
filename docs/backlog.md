# docs/backlog.md — Deferred Work Items

Items deferred from the current phase with rationale.
Format: | Item | Reason | Target Phase | GitHub Issue |

---

| Item | Reason Deferred | Target Phase | Issue |
|---|---|---|---|
| Webhook signature validation (HMAC-SHA256) | Requires Razorpay webhook secret — safe to stub in Phase 0 | Phase 1 | #TBD |
| Event idempotency enforcement (duplicate check) | Depends on payment_events table existing — created in Phase 0 but no ingestion yet | Phase 1 | #TBD |
| arq worker implementation | No events to process until Phase 1 webhook ingestion is live | Phase 1 | #TBD |
| Razorpay Payment Link creation | Requires confirmed Razorpay Test Mode API access | Phase 1 | #TBD |
| MockProvider implementation | Depends on BaseProvider interface defined in Phase 1 | Phase 1 | #TBD |
| Recoverability ML model | Requires synthetic training data from Phase 2 | Phase 3 | #TBD |
| LLM prompt integration | Requires ML predictions as context | Phase 5 | #TBD |
| Risk Firewall rules | Depends on feature engineering from Phase 3 | Phase 6 | #TBD |
| Finance reconciliation | Depends on action execution from Phase 7 | Phase 8 | #TBD |
| Dashboard screens | Depends on data from Phases 1–8 | Phase 9 | #TBD |
| Database integration tests | Requires a test Postgres instance in CI | Phase 1 | #TBD |
| Frontend unit tests (vitest) | Placeholder config present; no components to test yet | Phase 9 | #TBD |
| next.config.ts `output: standalone` | Required for Dockerfile.web multi-stage build | Phase 0 followup | #TBD |

---

### Session Summary: Phase 5 (LLM Reasoning)
**What was done:**
- Implemented `generate_explanation()` with `google-genai` and `openai` (fallback) to provide human-readable narratives of policy decisions.
- Enforced strict JSON structures via Pydantic `ExplanationResult`.
- Integrated a 10.0s circuit breaker `asyncio.wait_for`.
- Injected LLM call into `domain/policies/pipeline.py` **after** deterministic rules execute to ensure mutation safety.
- Wrote robust tests confirming schema failures, timeouts, and hallucinated overrides are ignored and gracefully handled.
- Updated `README.md` to reflect Phase 4 and Phase 5 completion.

**What's still open:**
- Docker Desktop is currently inaccessible on the host, preventing manual DB queries and end-to-end webhook integration tests from running locally.
- A new Alembic migration needs to be generated (`alembic revision --autogenerate`) for the `LLM_EXPLANATION_FAILED` enum value once the DB is up.

**Next session read first:**
- Run `alembic revision --autogenerate` for the AuditEventType enum as soon as Docker is up.
- Review Phase 6 (Risk Firewall) requirements in PRD.

### Session Summary: Phase 6 (Risk Firewall)
**What was done:**
- Implemented PRD Module D (Risk Firewall) with 5 independent risk checks (transaction, frequency, amount, behavioral, policy).
- Aggregated checks into a defense-only layer that never overrides a BLOCK but can upgrade an ALLOW to REVIEW/BLOCK.
- Added `RISK_FIREWALL_EVALUATED` and `RISK_FIREWALL_BLOCKED` to `AuditEventType` via an Alembic migration.
- Wired the firewall into `domain/policies/pipeline.py` to evaluate before the LLM explanation layer.
- Exhaustive unit tests and integration tests written and passing. 
- All code pushed to `phase-6-risk-firewall`.

**What's still open:**
- PR for `phase-6-risk-firewall` needs to be reviewed and merged into `main`.

**Next session read first:**
- You are on branch `phase-7-action-layer` (based on `phase-6-risk-firewall`). Wait for `main` merge if required.
- Review Phase 7 (Action Layer) requirements in PRD.

### Session Summary: Phase 7 (Action Layer)
**What was done:**
- Implemented `domain/recovery/executor.py` to deterministically execute AUTONOMOUS or APPROVED actions via Razorpay Test Mode/MockProvider.
- Scaffolded a new arq worker (`workers/recovery_worker/`) to process actions safely in the background, including a 60-second cron fallback to ensure eventual execution for any dropped jobs.
- Wired the pipeline (`domain/policies/pipeline.py`) to enqueue jobs synchronously after logging the policy decision.
- Unit and integration tests written, and `docker-compose.yml` updated with the `recovery_worker` service.
- All pre-push and smoke tests pass.

**What's still open:**
- PR for `phase-7-action-layer` needs to be reviewed and merged into `main`.
- Webhook verification of `payment_link.paid` needs to be established in Phase 8 (Finance Truth Layer).

**Next session read first:**
- Review Phase 8 (Finance Truth Layer) requirements in PRD.

### Session Summary: Phase 7.5 (Validation Layer)
**What was done:**
- Implemented `ValidationOutcome` schema and logic in `integrations/integrations/validation.py`, `razorpay/validation.py`, and `mock/validation.py`.
- Added `VALIDATION_BLOCKED` DB state to `ExecutionStatus` via an Alembic migration.
- Wired the validation layer into `domain/finance/executor.py` to intercept actions before moving to `EXECUTING` by fetching the live state.
- Wrote robust mock validation tests to simulate race conditions (e.g., payment already captured) and unsupported states.
- Re-ran tests, committed to `phase-7.5-validation-layer`, and updated `README.md`.

**What's still open:**
- Docker Desktop pipe issue persists locally; CI pipeline is required to run true Docker-based integration smoke tests.

**Next session read first:**
- Review Phase 8 (Finance Truth Layer) requirements in PRD.

### Session Summary: Phase 8 (Finance Truth) & Phase 8.5 (Budget Optimizer)
**What was done:**
- Implemented `domain/finance/reconciliation.py` to reconcile expected recovery amounts against actuals from the payment provider (`MATCHED`/`PARTIAL`/`EXCEPTION`).
- Added the `PARTIAL` reconciliation status via Alembic migration.
- Built a metrics API `apps/api/routes/metrics.py` calculating Incremental Revenue, Recovery Rate, and Exception Rate.
- Added deterministic baselines (`always_retry`, `fixed_schedule`, `simple_rule`) and generated the `phase8-benchmark.md` evaluation report proving RecoverFlow's efficacy.
- Built the Budget Optimizer (`domain/recovery/budget_optimizer.py`), an allocation layer applying a greedy expected-value knapsack approximation to fund actions.
- Documented the architecture for the "Stale Webhook Defense" (Phase 7.5 + Phase 8) and Optimizer algorithmic assumptions.
- Wrote integration and unit tests proving the math, safety boundaries, and allocator constraints.

**What's still open:**
- Docker Desktop pipeline continues to be blocked on host communication, so `smoke_test.sh` via Docker is pending CI implementation.

**Next session read first:**
- You are ready for Phase 9 (Dashboard).
- Review Phase 9 requirements in the PRD, which will start bringing all this data into the UI.

### Session Summary: Phase 9 (Funnel Infrastructure)
**What was done:**
- Created `sessions` and `funnel_events` tables with `FunnelEventType` enum via Alembic migration.
- Bridged top-of-funnel data to real recovery pipeline by adding `session_id` FK on `payment_events`.
- Built `EventTrackingProvider` interface (`integrations/analytics/base.py`) with `SyntheticProvider` implementation — mirrors the Phase 1 PaymentProvider abstraction pattern.
- Implemented idempotent `POST /funnel/events/track` ingestion endpoint.
- Created deterministic `data/synthetic/generate_funnel.py` (seed 42, modeled drop-off rates).
- Built `scripts/simulate_live_sessions.py` live-fire simulator — verified working against dockerized API.
- Implemented `GET /funnel/summary` aggregation endpoint computing stage counts and drop-off rates from DB.
- Fixed Docker build: added `COPY domain/` to Dockerfiles, corrected `get_db` import paths, resolved `apps.api.db.models` vs `db.models` import chain for Docker context.
- Updated `docs/evaluation/dataset-card.md` with funnel simulation assumptions.

**What's still open:**
- Dashboard UI (the actual React/frontend) is not yet built — this phase was backend infrastructure only.
- `smoke_test.sh` via Docker is still pending CI implementation.

**Next session read first:**
- You are ready for Phase 10 (Dashboard UI / Simulation Lab).
- The funnel backend is complete — the next phase should consume `GET /funnel/summary` and other APIs to build the visual dashboard.

### Session Summary: Phase 9.5 (Revenue Leak Graph)
**What was done:**
- Built `GET /leak-graph` API endpoint with genuine multi-table joins across `funnel_events`, `payment_events`, `recovery_cases`, `candidate_actions`, and `reconciliation_records`.
- Each leak point includes root-cause breakdown (failure_type), affected segment breakdown, and linked recovery actions with expected recovery amounts.
- Built full funnel visualization using Recharts BarChart in a new `/leak-graph` Next.js page.
- Created reusable `DataSourceBadge` component for permanent honesty labeling ("Simulated traffic data" vs "Live system data") on every stage.
- Every stage card shows count, value, drop-off rate, and a drill-through button to inspect the leak details (root causes, segments, recovery actions).
- Added link from the home page to the Leak Graph page.
- Fixed Docker builds: `domain/` directory now correctly included in Dockerfile.api and Dockerfile.worker.
- Added integration test verifying stage counts match raw DB queries.

**Next session read first:**
- Phase 10 (Simulation Lab / Dashboard Polish).
