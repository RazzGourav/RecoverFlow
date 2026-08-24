# RecoverFlow - System Architecture & Design

## 1. Overview
**RecoverFlow** is an AI-powered Revenue Recovery Control Plane built for Razorpay. It replaces static, legacy rule-based retry logic with a dynamic, budget-aware ML policy engine. The system evaluates failed payments in real-time and executes counterfactual simulations to determine the mathematically optimal recovery action (e.g., immediate retry, delayed reminder, dynamic discount, or human intervention) for every drop-off.

## 2. Core Architecture

The system is composed of several decoupled services, orchestrated via an event-driven architecture.

### 2.1 Backend (API & Workers)
Built with **FastAPI** (Python 3.12) and **ARQ** (Redis-based async task queues).
- **Web API Layer**: Exposes REST endpoints for webhooks (Razorpay/Mock providers), dashboard data feeds (Audit, Simulation, Analytics), and policy management.
- **Event Workers**: Processes incoming webhook payloads asynchronously, parses states, and manages idempotency.
- **Recovery Workers**: Orchestrates the AI Policy Engine evaluation pipeline. Executes the final determined action (or safely blocks it if it fails validation).
- **Reconciliation Workers**: Periodically matches downstream actions to ultimate success/failure states to close the loop on revenue recovery accounting.

### 2.2 AI & Policy Engine
- **Predictive ML (XGBoost)**: Evaluates user context, cart value, and session data to predict the probability of recovery for a given candidate action.
- **Risk Firewall**: Rule-based gatekeeper that enforces hard constraints (e.g., maximum retries exceeded, fraudulent velocity detected).
- **Budget Optimizer**: Ensures that costly actions (like discounts or SMS blasts) are allocated only to high-yield cases, adhering to a global, replenishing budget.
- **Deterministic Validation**: The "Safety Net". Before any action actually touches an external API, a strict validation layer ensures the underlying state (e.g., payment status) hasn't mutated since the decision was made.

### 2.3 Frontend Dashboard
Built with **Next.js 14**, **React**, **Tailwind CSS**, and **Framer Motion**.
- **Control Tower**: Global overview of at-risk revenue, recovered revenue, and a live activity feed.
- **Case Intelligence**: Vertical full-stack drill-down into individual failures, visualizing the AI's step-by-step reasoning (Prediction -> Risk -> Budget -> Validation -> Execution).
- **Policy Studio**: Interactive interface to tweak budget caps and risk thresholds, immediately simulating the impact on historical cases.
- **Simulation / Replay Labs**: Counterfactual analysis tools ("Multiverse Simulator") comparing the AI's budget-aware decisions against static legacy rules on live data.

### 2.4 Data Persistence
- **PostgreSQL**: The primary relational store. Uses `SQLAlchemy` (async) for ORM and `Alembic` for migrations. Stores normalized domains: `Customers`, `FunnelEvents`, `PaymentEvents`, `RecoveryCases`, `AuditEvents`, `CandidateActions`.
- **Redis**: Acts as the message broker for ARQ and a high-speed cache for idempotency keys.

## 3. End-to-End Data Flow

1. **Ingestion**: A user drops off at the payment stage. Razorpay fires a `payment.failed` webhook.
2. **Event Parsing**: The webhook is caught by `/webhooks/razorpay`, checked for idempotency, and placed onto the Redis queue.
3. **State Hydration**: The `Event Worker` picks up the task, links the payment failure to the preceding `FunnelEvent` (via `session_id`), and instantiates a `RecoveryCase`.
4. **Policy Evaluation**: The `Recovery Worker` wakes up. It asks the ML model to score all candidate actions (Retry, Discount, Do Nothing).
5. **Optimization**: The Budget Optimizer runs a knapsack-like evaluation across recent cases to select the action maximizing Expected Value (EV) without blowing the discount budget.
6. **Validation & Execution**: The chosen action passes through the Validation Layer to prevent "stale state" execution. If clear, the action is executed via the `RazorpayProvider`.
7. **Audit & Reconciliation**: Every step is heavily logged to `audit_events`. Later, the `Reconciliation Worker` verifies if the user actually paid, marking the case as `RECOVERED` or `FAILED`.

## 4. Key Design Principles

- **Safety First**: The LLM / ML models *never* execute actions directly. They emit structured recommendations evaluated by deterministic code.
- **Idempotency**: All mutating webhooks utilize an `idempotency_key` constraint to prevent double-processing in distributed setups.
- **Reproducibility**: Entire local environments, from databases to worker queues, spin up deterministically via `docker-compose`.
- **Observability**: The "Explain This" concept is deeply ingrained in the UI; every automated decision leaves a cryptographically traceable audit trail (Risk Score, Budget State, ML Confidence) surfaced in the dashboard.
