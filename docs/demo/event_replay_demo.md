# Event Replay Lab - Hero Case Demo

## The Problem
RecoverFlow analyzes thousands of cases automatically, applying optimized policies to maximize recovery. However, operations teams need the ability to drill down into a single failed recovery case and ask counterfactual questions:
- "What if we had waited 12 hours instead of 5 minutes before retrying?"
- "What if we offered a 10% discount instead of just a reminder?"
- "What would our risk score have been if this payment was a high-value subscription?"

## The Hero Case
Let's look at Case ID `c2aa5c6a-365b-4002-835f-ae111b25d6fd` (a typical medium-value subscription failure).

### Baseline Outcome
- **Initial Action**: `REMINDER`
- **Expected Recovery**: ₹450
- **Cost**: ₹1
- **Risk Level**: LOW

### Counterfactual Replay
Using the **Event Replay Lab** (`POST /simulate/replay/{case_id}`), we can replay the exact state of this case at the time of failure, but force a different recovery strategy.

#### Scenario A: Aggressive Discounting (10% Discount)
```json
POST /simulate/replay/c2aa5c6a-365b-4002-835f-ae111b25d6fd
{
  "strategy": "DISCOUNT_10"
}
```
**Outcome**:
- **New Action**: `PAYMENT_LINK` (with 10% discount applied)
- **Expected Recovery**: ₹405 (lower expected value due to the discount)
- **Cost**: ₹10 (SMS delivery cost)
- **Risk Level**: MEDIUM (discounting increases churn risk on next cycle)

**Business Insight**: While discounting increases the raw probability of success, the expected value is actually *lower* than a simple reminder, and the risk increases. The Replay Lab mathematically proves that the Policy Engine made the right call.

#### Scenario B: Do Nothing
```json
POST /simulate/replay/c2aa5c6a-365b-4002-835f-ae111b25d6fd
{
  "strategy": "DO_NOTHING"
}
```
**Outcome**:
- **New Action**: `NO_ACTION`
- **Expected Recovery**: ₹0
- **Cost**: ₹0
- **Risk Level**: HIGH (guaranteed churn)

## How It Works Technically
The Event Replay Lab leverages the exact same `simulation_core` as the batch-level Counterfactual Simulator, but scopes the pipeline down to a single case.

1. **Transaction Isolation**: The replay executes inside a nested Postgres savepoint (`session.begin_nested()`).
2. **Mocking Engine**: Database `commit()` and `rollback()` calls from the underlying `executor.py` are dynamically mocked during the replay so that the internal state machine (PENDING -> EXECUTING -> EXECUTED) can run, without destroying the outer savepoint.
3. **Zero Writes Guarantee**: At the end of the simulation, the entire nested savepoint is rolled back. No side-effects touch the live database, ensuring the replay is completely safe for production auditing.
