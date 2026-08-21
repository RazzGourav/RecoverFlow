# Defense-in-Depth against Stale State

One of the most common issues in payment recovery is acting on stale information. For example, a webhook arrives indicating a payment failed, the system initiates a recovery sequence, but the customer manually pays via the original checkout link before the recovery action executes. 

If the system executes the recovery action, it risks double-charging the customer or sending a confusing communication.

RecoverFlow employs a two-layered defense-in-depth strategy to prevent this.

## Layer 1: Pre-Execution Validation Gate (Phase 7.5)

Before the Action Executor (`domain/finance/executor.py`) transitions a `PENDING` action to `EXECUTING`, it performs a live check:

1. **Fetch Live State**: The executor calls `PaymentProvider.fetch_payment` using the original case's `external_payment_id`.
2. **Validate**: The live state is passed to the validation module (`integrations/integrations/validation.py`).
3. **Block if Invalid**: If the payment is already marked as `captured`, `authorized`, or `paid`, the validation module returns `INVALID_STATE`. The action is immediately routed to the `VALIDATION_BLOCKED` terminal state. 
4. **Result**: No money moves. The provider API is never called to create a payment link.

## Layer 2: Post-Hoc Finance Truth Reconciliation (Phase 8)

If an action somehow bypasses the validation gate (e.g. the customer pays exactly between the validation check and the execution call — a rare but possible race condition), the Finance Truth Layer catches it during reconciliation.

1. **Reconcile**: When the background worker polls the provider for the execution outcome (e.g. checking if the newly generated payment link was paid).
2. **Cross-Check Ground Truth**: Even if the new action appears "successful", the reconciliation layer (`domain/finance/reconciliation.py`) fetches the *original* payment state.
3. **Exception Flagging**: If the original payment was paid out-of-band, the reconciliation record is marked as an `EXCEPTION` rather than `MATCHED` recovery.
4. **Result**: The system correctly attributes the recovery to the original flow, preventing inflated "AI recovered" metrics and flagging the overlap for operational review.
