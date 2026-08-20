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
