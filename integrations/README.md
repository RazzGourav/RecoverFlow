# integrations/

Payment provider abstraction layer.

This directory is intentionally empty in Phase 0.
Implementation begins in **Phase 1 (Payment Event Foundation)**.

## Planned sub-modules

| Directory | Purpose | Phase |
|---|---|---|
| `razorpay/` | Razorpay Test Mode provider (webhooks, Payment Links, subscriptions) | 1 |
| `mock/` | MockProvider — simulates all provider calls without hitting real APIs | 1 |

## Provider Abstraction Rule

**Business logic never calls a payment SDK directly.**

All payment-provider interactions go through the `BaseProvider` interface:

```python
class BaseProvider(Protocol):
    async def create_payment_link(self, ...) -> PaymentLinkResult: ...
    async def get_payment_status(self, ...) -> PaymentStatus: ...
    async def cancel_payment_link(self, ...) -> CancelResult: ...
```

The active provider is selected via the `PAYMENT_PROVIDER` env var:
- `razorpay` → live test-mode calls
- `mock` → deterministic offline simulation (default for tests)

This ensures:
1. Tests never hit real APIs.
2. The demo can run fully offline.
3. No Razorpay capability is assumed without being documented.
