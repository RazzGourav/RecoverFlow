# workers/

Background task workers using `arq` (async Redis queue).

This directory is intentionally empty in Phase 0.
Implementation begins in **Phase 1 (Payment Event Foundation)**.

## Planned sub-modules

| Directory | Purpose | Phase |
|---|---|---|
| `event_worker/` | Processes raw payment events from the queue | 1 |
| `recovery_worker/` | Runs ML analysis and Policy Engine per case | 4 |
| `reconciliation_worker/` | Verifies payment outcomes and reconciles records | 8 |

## Worker Design

- Workers consume jobs from Redis using `arq`.
- Each job handler is idempotent — running it twice produces the same result.
- Workers never directly call payment SDKs — all provider calls go through `integrations/`.
- All worker actions write to `audit_events` before returning.
