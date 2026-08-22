# The 2 AM Incident: A Case Study in Deterministic Failure Handling

## The Scenario
It's 2 AM on Black Friday. A massive spike in traffic hits the payment gateway.
The gateway gets overwhelmed and starts sending duplicate webhooks for the same failed payment.
Simultaneously, the provider's API begins timing out.
Later, when things recover, the provider's API becomes available but another process (or manual intervention) already resolved the payment.

## How RecoverFlow Survives

RecoverFlow implements three layers of defense that work together seamlessly to prevent double-charging, infinite retries, or corrupted state.

### 1. Ingestion Idempotency (The First Defense)
- **What happens:** Two identical `payment.failed` webhooks arrive at exactly 2:01 AM.
- **How it's handled:** The `webhooks.py` router attempts to insert a `PaymentEvent` into the database. The `external_event_id` column has a unique constraint. The database rejects the second insert with an `IntegrityError`. 
- **The Result:** The system safely ignores the duplicate and emits a `WEBHOOK_DUPLICATE_DROPPED` audit event.

### 2. Execution Timeout (The Second Defense)
- **What happens:** The first webhook successfully spawns a `RecoveryCase`. The Policy Engine autonomously decides to send a payment link. The Action Executor attempts to create a payment link via the Provider API, but the API times out after 15 seconds.
- **How it's handled:** The `asyncio.wait_for` wrapper catches the `TimeoutError`. The executor safely rolls back any intermediate state, marks the action as `TIMED_OUT`, and emits an `ACTION_TIMEOUT` audit event.
- **The Result:** The case is paused. No half-finished state exists.

### 3. Validation Firewall (The Third Defense)
- **What happens:** A retry mechanism (or manual click) attempts to execute the timed-out action again. However, during the downtime, the customer manually paid their invoice via another channel.
- **How it's handled:** Right before execution, the Action Executor polls the live provider state. The Validation Layer detects that the original payment is already `paid`. 
- **The Result:** It blocks the execution with `ValidationStatus.STALE_STATE`, marks the action as `VALIDATION_BLOCKED`, and emits an audit event.

## Conclusion
A situation that typically causes duplicate charges or database corruption is handled gracefully. The Failure Center dashboard displays a clear, chronological log of these 3 blocked threats, giving engineering absolute confidence in the system's safety.
