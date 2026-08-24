# RecoverFlow — System Design & Architecture

## Overview
RecoverFlow is an AI-native Revenue Recovery Control Plane designed to automate the resolution of failed payments for merchants. It transitions the merchant's operational posture from reactive retries to proactive, policy-driven interventions by combining an ML inference engine, an LLM reasoning layer, and a deterministic Risk Firewall into an autonomous agent pipeline.

## Core Architecture

RecoverFlow is built as a modular monolith utilizing a microservices-inspired asynchronous task architecture.

### 1. Ingestion Layer (Webhooks)
- **Component:** FastAPI Webhook Receiver (`apps/api/routes/webhooks.py`)
- **Function:** Ingests live payloads (e.g., Razorpay `payment.failed` events), verifies HMAC signatures, and deduplicates identical events (idempotency checks).
- **Storage:** Persists raw data into `payment_events` with `RECEIVED` status.
- **Queueing:** Enqueues the event ID to Redis via the ARQ worker queue for background processing. This guarantees low latency for the external webhook provider.

### 2. Normalization & Event Processing
- **Component:** Event Worker (`workers/event_worker/worker.py`)
- **Function:** Parses the raw payload from the database and maps provider-specific error codes (e.g., `BAD_REQUEST_ERROR`, `insufficient_funds`) into a canonical internal `FailureType` (TEMPORARY, PERSISTENT, PAYMENT_METHOD, CUSTOMER_ACTION).
- **Output:** Creates a unified `RecoveryCase` in PostgreSQL and kicks off the decision pipeline.

### 3. Decision Pipeline (The "Brain")
Orchestrated by `domain/policies/pipeline.py`, this is the core pipeline that evaluates a case and generates an executable Action.

#### A. AI Inference Engine (`ai/inference/predict.py`)
- Extracts hundreds of features from the case and historical data.
- Executes an **XGBoost Classifier** to determine `recoverability_score` (0.0 to 1.0).
- Executes a **Logistic Regression** model to predict the optimal `recommended_action` (e.g., `RETRY_LATER`, `CONTACT_CUSTOMER`, `OFFER_DISCOUNT`).

#### B. LLM Reasoning Layer (`ai/inference/llm.py`)
- Takes the raw case data + ML predictions and feeds it to an LLM (OpenAI/Gemini).
- Provides a human-readable `explanation` for *why* the ML model recommended its action, allowing for explainable AI.
- Includes a Circuit Breaker pattern to gracefully fallback to a heuristic mock if the LLM provider times out.

#### C. Risk Firewall (`domain/risk/firewall.py`)
- A deterministic safety net. The LLM NEVER executes actions directly.
- The recommended action is evaluated against predefined pure functions (e.g., checking frequency limits, high-value transaction rules, and fraud vectors).
- Generates a `risk_level` (LOW, MEDIUM, HIGH) and determines if the action requires `HUMAN_APPROVAL` or can be executed autonomously (`APPROVED`).

### 4. Action Execution Layer
- **Component:** Recovery Worker (`workers/recovery_worker/worker.py`) & Finance Executor (`domain/finance/executor.py`)
- **Function:** Picks up `APPROVED` actions. For monetary operations, it routes the request through the `RazorpayProvider` to issue retries, generate payment links, or apply discounts.
- **Auditability:** Every step writes a structured log to the `audit_events` table for compliance and debugging.

### 5. Reconciliation & Loop Closure
- **Component:** Reconciliation Worker (`workers/reconciliation_worker/worker.py`)
- **Function:** Polls the payment provider to verify if a previously executed action (like a retry) actually resulted in captured funds.
- **Output:** Closes the loop by marking the action as `COMPLETED` and updating the `RecoveryCase` status to `RECOVERED` or `FAILED_FINAL`.

## Data Model

- **PaymentEvent:** The raw, immutable inbound webhook payload.
- **RecoveryCase:** The canonical, normalized representation of a failed payment.
- **Action:** The proposed, executing, or completed intervention (linked to a case).
- **AuditEvent:** An append-only ledger of everything that happened to a case (who approved it, when it ran, why the firewall blocked it).
- **FunnelEvent:** Analytical tracking events from the merchant's frontend (used to construct the Revenue Leak Graph).

## Tech Stack
- **Backend:** Python 3.12, FastAPI, SQLAlchemy (Async), ARQ (Redis Queue)
- **Data & ML:** PostgreSQL 16 (Relational DB), Redis 7 (Message Broker), Scikit-Learn, XGBoost, Joblib (Model Artifacts)
- **Frontend:** Next.js 14 (App Router), React, Tailwind CSS (via UI libraries)
- **Integrations:** Razorpay API (Mockable via internal architecture)
- **Infrastructure:** Docker Compose (local dev), Uvicorn

## Observability & Simulation
- **Simulation Core:** RecoverFlow ships with a unique `ai/evaluation/simulation_core.py` which intercepts database commits and external API calls. This allows the system to run complex counterfactual dry-runs of the entire Policy Engine against historical data without mutating the live database or spending actual funds.
