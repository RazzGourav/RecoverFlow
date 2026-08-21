# Domain: Recovery

This module contains the core business logic for taking the ML model's expected-value outputs and determining the optimal recovery strategy and allocation.

## Phase 8.5: Budget Optimizer

The Budget Optimizer (`budget_optimizer.py`) acts as a portfolio-level allocator. Rather than evaluating cases in isolation, it takes a batch of cases and a maximum budget (defined by `policies.max_recovery_spend_paise`) and decides which cases should be funded.

### Cost Assumptions
The optimizer relies on deterministic cost estimations per action type:
- `RETRY`: ₹0 (Zero marginal cost for an automated retry payload).
- `PAYMENT_LINK`: ₹0 (Standard Razorpay link generation cost).
- `HUMAN_ESCALATION`: ₹50 (Fixed operations cost estimate for a support agent's time).
- `DISCOUNT_LINK`: Estimated as the expected absolute value of the discount offered.

### Algorithm Selection: Greedy vs Knapsack
We use a greedy algorithm sorted by the ratio of `expected_net_gain / action_cost`. 

**Why is this acceptable?**
1. **Auditable & Explainable:** A deterministic sorted list is trivial to explain to a merchant ("We fund the highest ROI actions first until money runs out").
2. **Speed & Scale:** O(N log N) sorting handles tens of thousands of cases instantly, avoiding the NP-Hard exponential overhead of an exact 0/1 knapsack solver.
3. **Problem Shape:** Since individual action costs (e.g. ₹50) are generally tiny fractions of typical portfolio budgets (e.g. ₹50,000), the greedy approximation error is negligible.

### Precedence & Safety Gates
**IMPORTANT**: The Budget Optimizer is an *allocation* layer, not an *execution* layer.

If the optimizer marks an action as `funded: true`, it does **not** bypass the existing safety gates. The action is still subjected to:
1. **Phase 4 Policy Engine**: Ensures it doesn't violate retry limits, cooldowns, or max-contacts.
2. **Phase 6 Risk Firewall**: Ensures it isn't blocked by frequency/transaction risk checks.
3. **Phase 7.5 Validation Gate**: Ensures the payment isn't already captured out-of-band right before execution.

The optimizer simply decides *if* there is budget to attempt the action. The downstream safety gates still dictate *how* and *if* it actually executes.
