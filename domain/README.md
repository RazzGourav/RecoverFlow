# domain/

Business logic domain modules — pure Python, no HTTP or DB concerns.

This directory is intentionally empty in Phase 0.
Implementation begins in **Phase 4 (Decision Engine)**.

## Planned sub-modules

| Directory | Purpose | Phase |
|---|---|---|
| `recovery/` | Recovery case state machine and orchestration | 4 |
| `policies/` | Deterministic Policy Engine (ALLOW/REVIEW/BLOCK) | 4 |
| `risk/` | Risk Firewall rules and score aggregation | 6 |
| `finance/` | Finance Truth Layer and reconciliation logic | 8 |
| `audit/` | Audit event writer (append-only) | 4 |

## Design Rule

Every module in `domain/` must be:
- **Pure** — no direct database calls (DB access goes through services in `apps/api/services/`)
- **Testable** — fully unit-testable without a database or HTTP server
- **Deterministic** — same inputs always produce same outputs (no hidden randomness)

The LLM output is an input to `domain/policies/`, never a substitute for it.
