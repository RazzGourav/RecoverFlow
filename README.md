<h1 align="center">RecoverFlow</h1>

<p align="center">
  <strong>An AI-native Revenue Recovery Control Plane</strong>
</p>

---

## 🛑 The Problem: Reactive Revenue Leakage
In the modern digital economy, failed payments are a silent killer of merchant revenue. Whether due to insufficient funds, network timeouts, or overzealous fraud filters, perfectly good transactions are blocked every second. 

Currently, merchants rely on **reactive retries** (dumbing hitting the payment gateway until it works) or **blind discounts**. These legacy systems lack context, treat all customers the same, and often run afoul of frequency limits or anger high-value users.

## 💡 The Solution: Autonomous & Policy-Driven Recovery
**RecoverFlow** shifts the paradigm from reactive retries to **proactive, policy-driven interventions**. 

It acts as an autonomous agent that sits between the merchant and the payment gateway. When a webhook signals a failed payment, RecoverFlow intercepts it, enriches it, and deploys machine learning to decide the absolute optimal recovery strategy (e.g., immediate retry, delayed retry, human intervention, or automated discount offering) — all while being tightly constrained by a deterministic Risk Firewall.

## ✨ Key Features
- **Intelligent Inference Pipeline:** Uses XGBoost and Logistic Regression to predict the recoverability score and recommend the optimal intervention.
- **Explainable AI (XAI):** Employs an LLM Reasoning Layer (OpenAI/Gemini) to generate human-readable explanations for *why* an action was chosen.
- **Deterministic Risk Firewall:** Safety is paramount. Every AI recommendation is strictly vetted against frequency, transaction, and behavioral constraints before execution.
- **Budget-Aware Optimization:** Allocates promotional discounts using a greedy knapsack algorithm to maximize ROI without burning through the merchant's margin.
- **Counterfactual Simulation Engine:** Allows merchants to dry-run new policies on historical data to see the financial impact *before* deploying to production.
- **Full-Stack Observability:** A Next.js Control Tower dashboard that visualizes the Revenue Leak Funnel and tracks the real-time status of every single recovery case.

## 🛠️ Technology Stack
- **Backend Core:** Python 3.12, FastAPI
- **Databases:** PostgreSQL 16 (Relational state), Redis 7 (Task Queues & Caching)
- **Background Workers:** ARQ (Async Redis Queues)
- **Machine Learning:** Scikit-Learn, XGBoost, Joblib
- **Frontend:** Next.js 14 (App Router), React, Tailwind CSS
- **Infrastructure:** Docker & Docker Compose

---

## 🚀 Quickstart Guide

Getting RecoverFlow running on your local machine is designed to be frictionless. No manual database setup or complex dependency chains required.

### Prerequisites
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running.
- Git.

### 1. Clone & Configure
```bash
git clone https://github.com/RazzGourav/RecoverFlow.git
cd RecoverFlow

# Copy the example environment variables
cp .env.example .env
```
*(Note: The default `.env.example` comes pre-configured with a mock LLM provider and mock Razorpay secrets so it runs perfectly out of the box).*

### 2. Boot the System
```bash
docker compose up --build -d
```
Docker Compose will automatically:
- Spin up PostgreSQL and Redis.
- Wait for the databases to become healthy.
- Run Alembic migrations to construct the database schema.
- Boot the FastAPI backend, the three ARQ background workers, and the Next.js frontend.

### 3. Access the Platforms
- **Dashboard UI:** [http://localhost:3000](http://localhost:3000)
- **API Swagger Docs:** [http://localhost:8000/docs](http://localhost:8000/docs)

---

## 🧪 Testing the System

### Run the Test Suite
The codebase is heavily tested. To execute the unit and integration tests inside the running API container:
```bash
docker compose exec api pytest -q
```

### End-to-End Simulation
To observe the entire pipeline working live, simulate a failed payment webhook from Razorpay:
```bash
# This will inject a mock webhook into the system
docker compose exec api python scripts/simulate_webhook.py --id my-test-event-1 --secret test_webhook_secret_123
```
Watch the worker logs to see the AI inference engine and Risk Firewall process the event:
```bash
docker compose logs -f worker
```

---

## 📜 Architecture Diagram
*(See [system-design.md](./system-design.md) for a comprehensive deep dive into the system's asynchronous architecture and data flows).*
