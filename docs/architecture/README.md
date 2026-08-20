# docs/architecture/

Architecture documentation for RecoverFlow.

See the ASCII diagram in [README.md](../../README.md#system-architecture) for the high-level system view.

### Phase 1: Webhook Ingestion & Event Flow

This diagram illustrates how raw payment failures are ingested from the provider and normalized into actionable `RecoveryCase` records.

```mermaid
sequenceDiagram
    participant Razorpay
    participant API (FastAPI)
    participant Database (Postgres)
    participant Redis (Arq)
    participant Worker (Arq)

    Razorpay->>API: POST /webhooks/razorpay (payment.failed)
    Note over API: 1. Validate HMAC Signature
    Note over API: 2. Check X-Razorpay-Event-Id
    
    API->>Database: INSERT PaymentEvent (status=RECEIVED)
    alt Idempotency Constraint Hit (Duplicate ID)
        Database-->>API: IntegrityError
        API-->>Razorpay: 200 OK {"status": "duplicate"}
    else New Event
        Database-->>API: OK
        API->>Redis: Enqueue 'normalize_payment_event'
        API-->>Razorpay: 200 OK {"status": "received"}
    end

    Redis-->>Worker: Dequeue Job
    Worker->>Database: SELECT PaymentEvent
    Note over Worker: Map Razorpay error code -> FailureType
    Worker->>Database: INSERT RecoveryCase (status=OPEN)
    Worker->>Database: UPDATE PaymentEvent (status=PROCESSED)
```
