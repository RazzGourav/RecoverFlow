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
- Check out a new branch for Phase 8.
- Review Phase 8 (Finance Truth Layer) requirements in PRD.
