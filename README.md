# RecoverFlow

**AI Revenue Recovery Control Plane** 

> RecoverFlow turns payment failure from a reactive operations problem into an intelligent, measurable, and governed revenue-optimization loop.

[![CI](https://github.com/RazzGourav/RecoverFlow/actions/workflows/ci.yml/badge.svg)](https://github.com/RazzGourav/RecoverFlow/actions/workflows/ci.yml)
![Stack](https://img.shields.io/badge/Stack-FastAPI%20%7C%20Next.js%2014%20%7C%20PostgreSQL%20%7C%20Redis-blue)

---

## 🛑 Problem Statement/ Theme

Failed payments and involuntary churn represent a massive, silent leak in recurring revenue for SaaS and subscription businesses. Traditional recovery methods are primitive and reactive:
- **Blind Retries**: Trying the same card identically every 24 hours until it hard-declines.
- **Wasted Margins**: Offering discounts to users who would have paid anyway, or spending expensive SMS/Call center budget on unrecoverable accounts.
- **Operational Silos**: Finance sees a failed payment, engineering sees a webhook error, and marketing sees a lost subscriber, but there is no centralized intelligence connecting the dots.

Businesses need a system that treats revenue recovery as a dynamic optimization problem, intercepting failures and intelligently calculating the best recovery strategy in real-time.

## 🎯 Themes & Goals

1. **Intelligent Capital Efficiency**: Spend recovery budget (discounts, SMS costs) only on users where it maximizes expected value.
2. **Defensive Safety**: Never execute a stale recovery action, never double-charge a user, and never violate hard compliance policies.
3. **Full Visibility**: Track the complete lifecycle of a recovery attempt—from webhook ingestion to final financial reconciliation—providing a transparent Revenue Leak Graph.

---

## 💡 Solution & Features

RecoverFlow is an AI-powered decision system that answers five questions for every failed payment:
1. **What revenue is currently at risk?**
2. **Why is it at risk?**
3. **Which customers/payments are actually recoverable?**
4. **What is the safest and most valuable intervention?**
5. **Did the intervention actually recover money?**

Instead of retrying every failed payment identically, RecoverFlow computes:
`Recoverability × intervention effectiveness × financial value × customer risk × policy constraints` before taking any action.

### Key Features
- **AI Budget Optimizer**: Formulates recovery as a Knapsack problem, selecting the optimal combination of recovery actions to maximize Expected Value (EV) under a strict monthly budget cap.
- **Risk Firewall**: A rule-based and ML-powered safety layer that intercepts fraudulent or high-risk cases before any money is spent on recovery.
- **LLM Reasoning Fallback**: Uses Large Language Models to dynamically reason about edge cases and explain complex policy decisions with strict JSON validation.
- **Validation & Reconciliation Layer**: Pre-execution checks guarantee we never recover a payment that was resolved externally. Post-execution workers poll the payment provider to align internal state with ground truth.
- **Simulation Lab & Event Replay**: A dry-run environment allowing historical replay and counterfactual strategy testing (e.g., *"What if we offered a 5% discount instead?"*) with zero financial side effects via nested transaction rollbacks.
- **Revenue Leak Graph**: A visual dashboard providing full funnel visibility from drop-off to successful recovery.

---

## 🛠️ Working Tech Stack

| Layer | Technology |
|---|---|
| **Frontend** | Next.js 14, TypeScript (strict), Tailwind CSS, Recharts |
| **Backend API** | FastAPI, Python 3.12, Pydantic v2, structlog |
| **Database** | PostgreSQL 16, SQLAlchemy 2 (async), Alembic |
| **Message Queue** | Redis 7, arq (background workers) |
| **Machine Learning** | XGBoost, scikit-learn (Risk Scoring & Intervention Prediction) |
| **LLM Reasoning** | OpenAI / Gemini (Fallback explanation engines) |
| **Infrastructure** | Docker Compose |
| **CI/CD** | GitHub Actions |

---

## 🚀 How to Run Locally

### Prerequisites
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) ≥ 4.x
- Git

### Quickstart
Run the entire stack from a clean clone using Docker Compose:

```bash
git clone https://github.com/RazzGourav/RecoverFlow.git
cd RecoverFlow
cp .env.example .env
docker compose up --build
```
*That's it. No additional steps. Migrations run automatically when the API container starts.*

### Available Services
| URL | Service |
|---|---|
| `http://localhost:3000` | Next.js frontend (Revenue Control Tower) |
| `http://localhost:8000/docs` | FastAPI Swagger UI |
| `http://localhost:8000/health` | Health check (JSON) |
| `localhost:5432` | PostgreSQL (user: `recoverflow`, pass: `recoverflow`) |
| `localhost:6379` | Redis |

---

## 🧪 How to Test

We enforce a strict pre-push sequence to guarantee system integrity. 

### Automated Test Suite
From the root directory, you can utilize the Makefile commands to run tests across the stack:
```bash
make lint        # Run ruff (Python linter)
make typecheck   # Run mypy (Python static typing)
make test        # Run pytest (Unit, Integration, and Simulation tests)
make smoke       # Run smoke_test.sh to verify API health
```

### Running Simulations & Benchmarks
The Simulation Lab allows testing of ML models and rule policies. To run a benchmark against the held-out test set:
```bash
# Inside the API container
python /app/scripts/run_final_benchmark.py
```
This script bypasses database mutations using transaction rollbacks and generates a report comparing AI optimal routing against baseline rule strategies.

### Managing Failures
All unexpected states (e.g., Duplicate Webhooks, Budget Exhaustion, Stale Validation Blocks) are recorded as `AuditEvent` rows and surfaced in the **Failure Center** dashboard. When debugging, always check the `correlation_id` in structured logs to trace a request from the webhook entrypoint through the ARQ workers.

---

## 🔒 Safety Principles

> **The AI/LLM never directly triggers an action.**

Every money-moving action passes through:
1. ML prediction
2. Risk Firewall (ALLOW / REVIEW / BLOCK)
3. Deterministic Policy Engine
4. Idempotency check
5. Audit log write

This means RecoverFlow can always answer:  
*"Here is what the system predicted, here is what it was allowed to do, here is what it actually did, here is what happened financially, and here is how that compares with a simpler alternative."*

## 📁 System Architecture Details
For a deep dive into the architectural sub-systems, decoupled layers, and integrations, see the [System Design Document](./systemdesign.md) in the root directory.
