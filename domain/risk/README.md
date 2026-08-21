# Risk Firewall — domain/risk/

## What this module does

Implements **PRD Module D** — the defense-only pre-execution safety layer that sits **before** (and composes with) the Phase 4 Policy Engine. Before any financial or customer-facing recovery action is executed, the Risk Firewall runs five independent checks.

## The Five Checks

| # | Check | What it flags |
|---|-------|---------------|
| 1 | **Transaction Risk** | Duplicate events, stale webhooks, PERSISTENT failure type, excessive failed attempts |
| 2 | **Frequency Risk** | Customer contacted too many times in 72h; too many actions in 24h |
| 3 | **Amount Risk** | Amount above autonomous threshold (₹5,000), review threshold (₹25,000), or hard-block threshold (₹1,00,000) |
| 4 | **Behavioral Anomaly** | Unusual amount spike vs historical average; new customer with large payment; new + PERSISTENT failure |
| 5 | **Policy Violation** | Action not in merchant's allowlist; merchant account inactive; action requires approval but isn't approved |

## Outcomes

```
ALLOW   — No check fired. Defer to Policy Engine.
REVIEW  — At least one check flagged (score ≥ 0.5). Human review required.
BLOCK   — At least one check scored ≥ 0.9. Action unconditionally blocked.
```

## Precedence Rule (Critical)

The Risk Firewall is **defense-only**. It can only make a decision **more restrictive**, never less.

Composition with Phase 4 Policy Engine output:

| Risk Firewall \ Policy Engine | AUTONOMOUS     | AWAITING_HUMAN | BLOCKED  |
|-------------------------------|----------------|----------------|----------|
| **ALLOW**                     | AUTONOMOUS     | AWAITING_HUMAN | BLOCKED  |
| **REVIEW**                    | AWAITING_HUMAN | AWAITING_HUMAN | BLOCKED  |
| **BLOCK**                     | BLOCKED        | BLOCKED        | BLOCKED  |

The composed result is ALWAYS at least as restrictive as both inputs. **The firewall can never upgrade a BLOCK to ALLOW.** This invariant is enforced by `compose_with_policy_decision()` and is explicitly tested.

## Audit Trail

Every Risk Firewall evaluation writes an `AuditEvent` with:
- `event_type = RISK_FIREWALL_EVALUATED` or `RISK_FIREWALL_BLOCKED`
- `reason` starting with `RISK_` prefix — distinguishable from Policy Engine reasons (which use `POLICY_` prefix)

## File Map

```
domain/risk/
├── __init__.py     — Public API re-exports
├── checks.py       — Five pure-function checks (independently unit-testable)
├── firewall.py     — Aggregation engine + compose_with_policy_decision()
└── README.md       — This file
```
