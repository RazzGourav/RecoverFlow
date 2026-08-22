# RecoverFlow — System Architecture & Design

## Overview
RecoverFlow is an AI-powered revenue recovery control plane designed to intelligently intercept failed payments and orchestrate recovery strategies using machine learning, mitigating churn while respecting budget constraints. 

## High-Level Architecture

The system is composed of several decoupled layers:

1. **Frontend (Next.js)**: A standalone React application rendering the Control Tower dashboard, Case Intelligence UI, and Leak Graph.
2. **Backend API (FastAPI)**: The central orchestration engine handling webhook ingestion, case management, policy execution, and frontend queries.
3. **Machine Learning Pipeline (XGBoost/scikit-learn)**: Two models - a Risk Scorer for fraud/firewalling, and an Intervention Optimizer to predict the success probability of specific actions (e.g., offering a 10% discount).
4. **Data Persistence**: PostgreSQL handles core relational models (`cases`, `actions`, `funnel_events`, `audit_events`), while Redis acts as the message broker for ARQ background workers and caching.
5. **Background Workers (ARQ)**: Asynchronous workers for handling non-blocking tasks like provider reconciliation and bulk payment webhook processing.

## Sub-Systems & Interactions

- **Webhook Ingestion (Phase 1)**: Ingests `payment.failed` events. Uses idempotency keys to prevent duplicate processing.
- **Funnel Infrastructure (Phase 9)**: Tracks the complete lifecycle of a recovery attempt (Ingested -> Scored -> Policy Executed -> Reconciled) for visibility via the Revenue Leak Graph.
- **Risk Firewall (Phase 6)**: A rule-based + ML classifier that intercepts high-risk or unrecoverable cases (e.g., fraudulent accounts, persistent failures) before any money is spent on recovery.
- **Decision Engine (Phase 4)**: Evaluates candidate actions using the ML models. If the system is unsure, it triggers an LLM fallback (Phase 5) to dynamically reason about complex edge cases.
- **Budget Optimizer (Phase 8.5)**: Formulates recovery as a Knapsack problem, selecting the optimal combination of recovery actions across a batch of cases to maximize Expected Value (EV) under a strict monthly budget cap.
- **Validation & Reconciliation (Phase 7.5 & 8)**: 
  - *Validation*: A pre-execution check to ensure a case hasn't already been recovered externally (stale state) before taking action.
  - *Reconciliation*: A post-execution worker that polls the payment provider to align internal state with ground truth.
- **Simulation Core (Phase 11 & 11.5)**: A dry-run environment allowing historical replay and counterfactual strategy testing (e.g., "What if we offered a 5% discount instead?") without financial side effects.

## Hardcoded / Simulated Components

For the purposes of this implementation and demo, several external dependencies are simulated:

1. **Synthetic Data**: The historical data used to train the ML models (`train.csv`, `test.csv`) is synthetically generated to mimic real-world SaaS payment failure patterns. The top-of-funnel volume metrics shown in the Leak Graph are derived from this simulated seed data.
2. **Payment Providers**: The integration layer (`integrations.mock.provider`) fakes Razorpay API calls. Generating payment links and checking payment status return deterministic mock responses rather than hitting the real live network.
3. **LLM Fallback**: In the test environments, the LLM reasoning step may be bypassed or simulated to preserve API quotas and ensure deterministic testing.

## Security & Reliability

- **Zero-Mutation Execution**: The Simulation Core forces a PostgreSQL nested transaction rollback to guarantee zero side effects when evaluating counterfactuals.
- **Strict Typing**: All backend models leverage Pydantic/SQLAlchemy 2.0 type hints, and the frontend operates in strict TypeScript mode.
