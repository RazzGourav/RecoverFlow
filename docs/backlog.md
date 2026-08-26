# Backlog

## Testing Hooks
- `FORCE_ACTION_TYPE_FOR_TESTING`: This environment variable can be set to `1` to force the Policy Engine to select specific actions based on the ones digit of the amount_paise. This is a test-only override and must NEVER be enabled in a demo or production run.

## Benchmark Policy + Feature Parity (fixed 2026-08-26, branch `fix-benchmark-script-real-computation`)
- **Permissive benchmark Policy retired.** Earlier benchmark runs seeded a Policy with `confidence_threshold=0.0` / review thresholds at ₹10L — values no real merchant sees. The benchmark now seeds the exact live defaults (`confidence_threshold=0.80`, ₹5k autonomous cap, ₹25k review threshold). Consequence: most cases legitimately route to AWAITING_HUMAN at these thresholds; that is reported as measured.
- **Feature-parity bug fixed in `build_case_context()`** (domain/policies/pipeline.py): it previously hardcoded `segment="UNKNOWN"`, `tenure_days=0`, so every case through the live pipeline produced all-zero segment features regardless of Customer data. It now reads the Customer row (async-safe explicit fetch) and maps DB segments back to ML vocabulary via `metadata_["ml_segment"]` (stashed at ingest/seed time) or a deterministic enum fallback. The risk-firewall call now receives the same real segment/tenure instead of hardcoded placeholders. Verified by `scripts/check_benchmark_feature_parity.py`: pipeline-fed argmax distribution is byte-identical to the raw-CSV check_distribution path.
- **RETRY dominance confirmed genuine** (not a benchmark-input artifact): with fully corrected features (39 NEW / 38 ESTABLISHED / 23 HIGH_VALUE, tenure mean 196.7d), the intervention model still ranks RETRY top for 100/100 held-out cases — identical to the raw-CSV cross-check. This is a model/training-data property; see evaluation/reports/final-benchmark.md.

## Known Failing Tests (triaged 2026-08-25, branch `triage-pre-existing-failures`)
Full suite: 8 failed / 64 passed / 22 errors. Triage found **no new production bugs** — every failure is test infrastructure or environment:

**IMPORTANT: run the full test suite / PRE-PUSH CHECK with Docker Compose stopped, or expect `test_simulation_read_only_guarantee` to occasionally show a false failure due to live workers writing to the shared DB. Do not treat a red result on this specific test as a real regression if Docker was running during the test.**

### A. Missing shared DB fixtures (22 ERRORs)
Tests request `db_session` / `setup_test_case` / `test_app` / `async_client` fixtures that were never added to `tests/conftest.py`. Affected files: `test_finance_executor.py` (7), `test_reconciliation.py` (4), `test_funnel.py` (2), `test_human_approval.py` (2), `test_2am_incident.py` (2), `test_action_layer.py` (2), `test_webhook_flow.py` (2), `test_leak_graph.py` (1). These 22 tests lack automated coverage, but every code path they exercise (finance executor, reconciliation, human approval, 2am incident, action layer, webhook flow, leak graph) has been manually verified end-to-end with real query output during the fix-executor-fake-customer-fallback branch work (see PR history). This is not equivalent to automated coverage and should be restored post-demo — but it is not a blind gap right now.
**Fix:** add one real-Postgres `db_session` + `setup_test_case` fixture pair to conftest (pattern already exists per-file in `test_decision_pipeline.py`). Safe to schedule post-demo.

### B. Stale test bugs (3 FAILEDs — FIXED 2026-08-25)
- `test_decision_pipeline_blocks_repeated_action`: asserted on an undefined `audit` variable (leftover refactor). Fixed: binds `audit = policy_audits[0]` before asserting.
- `test_generate_explanation_timeout_raises_error` / `test_llm_schema_validation_failure`: patched `apps.api.config.settings.llm_provider`, but `ai/inference/llm.py` imports `config.settings` — the patch never took effect, so provider stayed `mock` and nothing raised. Fixed by patching `config.settings.llm_provider`. Production circuit breaker (`asyncio.wait_for` → `LLMExplanationError`) was verified correct; only the mock target was wrong. All three now pass.

### C. Environment-dependent failures (demo-route modules, understood)
- `test_replay_read_only_guarantee` / `test_simulate_compare_endpoint`: drive the real FastAPI app, which loads `.env`'s `DATABASE_URL=postgres:5432` (Docker-internal hostname) → DNS `gaierror` on host runs. Pass inside containers.
- `test_simulation_read_only_guarantee`: flaky only in full-suite runs — counts Action/AuditEvent rows while the live Docker workers concurrently write to the shared Postgres, producing false "leak" detections. Passed 3/3 in isolation. Simulation-core nested-transaction isolation itself verified sound.

