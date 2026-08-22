# RecoverFlow

**AI Revenue Recovery Control Plane** — Razorpay /buildathon · Track 03

> RecoverFlow turns payment failure from a reactive operations problem into an intelligent, measurable and governed revenue-optimization loop.

[![CI](https://github.com/RazzGourav/RecoverFlow/actions/workflows/ci.yml/badge.svg)](https://github.com/RazzGourav/RecoverFlow/actions/workflows/ci.yml)
![Phase](https://img.shields.io/badge/Phase-0%20Foundation-brightgreen)
![Stack](https://img.shields.io/badge/Stack-FastAPI%20%7C%20Next.js%2014%20%7C%20PostgreSQL%20%7C%20Redis-blue)

---

## What is RecoverFlow?

RecoverFlow is an AI-powered decision system that answers five questions for every failed payment:

1. **What revenue is currently at risk?**
2. **Why is it at risk?**
3. **Which customers/payments are actually recoverable?**
4. **What is the safest and most valuable intervention?**
5. **Did the intervention actually recover money?**

Rather than retrying every failed payment identically, RecoverFlow computes:

```
Recoverability × intervention effectiveness × financial value × customer risk × policy constraints
```

…before acting.

---

## System Architecture

```
                         ┌────────────────────────┐
                         │   Razorpay Test Mode   │
                         │ APIs + Webhooks        │
                         └────────────┬───────────┘
                                      │
                                      ▼
                         ┌────────────────────────┐
                         │ Webhook Gateway        │
                         │ Signature Validation   │
                         └────────────┬───────────┘
                                      │
                                      ▼
                         ┌────────────────────────┐
                         │ Event / Case Manager   │
                         │ Idempotency + State    │
                         └────────────┬───────────┘
                                      │
             ┌────────────────────────┼─────────────────────────┐
             │                        │                         │
             ▼                        ▼                         ▼
     ┌───────────────┐        ┌──────────────┐         ┌──────────────┐
     │ Feature Store │        │ Risk Engine  │         │ Audit Log    │
     └───────┬───────┘        └──────┬───────┘         └──────────────┘
             │                       │
             ▼                       │
     ┌───────────────┐               │
     │ ML Recovery   │               │
     │ Predictor     │               │
     └───────┬───────┘               │
             │                       │
             └──────────┬────────────┘
                        ▼
              ┌─────────────────────┐
              │ Decision Orchestrator│
              └──────────┬──────────┘
                         │
                    ┌────┴────┐
                    ▼         ▼
             ┌──────────┐ ┌───────────┐
             │ LLM      │ │ Policy    │
             │ Reasoner │ │ Engine    │
             └────┬─────┘ └─────┬─────┘
                  │             │
                  └──────┬──────┘
                         ▼
                ┌──────────────────┐
                │ Approval Router  │
                └────────┬─────────┘
                         │
                 ┌───────┴─────────┐
                 ▼                 ▼
          Autonomous           Human Review
                 │                 │
                 └────────┬────────┘
                          ▼
                  ┌───────────────┐
                  │ Action Layer  │
                  └──────┬────────┘
                         │
                         ▼
                    Razorpay API
                         │
                         ▼
                ┌─────────────────┐
                │ Outcome Verifier│
                └────────┬────────┘
                         │
                         ▼
                ┌──────────────────┐
                │ Finance Truth    │
                │ / Reconciliation │
                └────────┬─────────┘
                         │
                         ▼
                     Evaluation
                         │
                         ▼
                 Dashboard / Reports
```

---

## Repository Structure

```
recoverflow/
├── apps/
│   ├── web/              Next.js 14 App Router frontend
│   └── api/              FastAPI backend
├── ai/                   ML models and LLM inference (Phase 3–5)
├── domain/               Business logic domain modules (Phase 4+)
├── integrations/         Razorpay + Mock provider abstraction (Phase 1)
├── workers/              Background task workers (Phase 1+)
├── data/                 Synthetic and raw datasets (Phase 2)
├── evaluation/           Metrics, baselines, reports (Phase 3+)
├── tests/                Unit, integration, reliability, security, eval
├── infra/                Docker configs and CI helpers
├── docs/                 Architecture, PRD, threat model, backlog
├── scripts/              Developer scripts (smoke_test.sh)
├── docker-compose.yml
├── Dockerfile.api
├── Dockerfile.web
├── Dockerfile.worker
├── .env.example
├── Makefile
└── README.md
```

---

## Local Development

### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) ≥ 4.x
- Git

### Run from a clean clone

```bash
git clone https://github.com/RazzGourav/RecoverFlow.git
cd RecoverFlow
cp .env.example .env
docker compose up --build
```

That's it. No additional steps.

### What you get

| URL | Service |
|---|---|
| `http://localhost:3000` | Next.js frontend (landing page) |
| `http://localhost:8000/docs` | FastAPI Swagger UI |
| `http://localhost:8000/health` | Health check (JSON) |
| `localhost:5432` | PostgreSQL (user: recoverflow, pass: recoverflow) |
| `localhost:6379` | Redis |

### Alembic migrations

Migrations run **automatically** when the API container starts (`alembic upgrade head`).

To run manually:

```bash
make migrate
# or
docker compose exec api alembic upgrade head
```

### Developer commands

```bash
make up          # Start all services
make down        # Stop services
make test        # Run pytest
make lint        # Run ruff
make typecheck   # Run mypy
make smoke       # Run smoke tests
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 14, TypeScript (strict), Tailwind CSS |
| Backend | FastAPI, Python 3.12, Pydantic v2, structlog |
| Database | PostgreSQL 16, SQLAlchemy 2 (async), Alembic |
| Queue | Redis 7, arq |
| ML (Phase 3+) | XGBoost, LightGBM, scikit-learn |
| LLM (Phase 5+) | OpenAI / Anthropic / Gemini / Mock |
| Containers | Docker Compose |
| CI | GitHub Actions |

---

## Phase Status

| Phase | Name | Status | Description |
|---|---|---|---|
| Phase 0 | Foundation & Structure | ✅ Complete | Repository skeleton, Docker Compose, DB schemas, CI pipeline |
| Phase 1 | Payment Events | ✅ Complete | Webhook signature validation, idempotency, failure mapping, PaymentProvider abstractions |
| Phase 2 | Recovery Data Engine | ✅ Complete | Synthetic dataset, dataset card, DB seeding |
| Phase 3 | ML Engine | ✅ Complete | Recoverability predictor, action effectiveness, risk firewall |
| 4 | Decision Engine | ✅ Complete | Deterministic policy engine, expected value ranking, audit logger |
| 5 | LLM Reasoning | ✅ Complete | AI explanation layer with strict schema validation and mutation safety |
| 6 | Risk Firewall | ✅ Complete | PRD Module D: defense-only safety layer with five risk checks |
| 7 | Action Layer | ✅ Done | |
| 7.5 | Validation Layer | ✅ Done | |
| 8 | Finance Truth Layer | ✅ Done | |
| 8.5 | Budget Optimizer | ✅ Done | |
| 9 | Funnel Infrastructure | ✅ Done | |
| 9.5 | Revenue Leak Graph | ✅ Done | Full funnel visualization with drill-through |
| 10 | Dashboard | ✅ Done | Control tower, Cases, Intelligence, Policy Studio, Audit |
| 11 | Simulation Lab | ✅ Done | |
| 12 | Failure Center | ✅ Done | Dashboard for blocked, dropped, and failed cases |
| 13 | Product Polish | ✅ Done | |
| 14 | Evaluation Freeze | 🔲 Upcoming | |
| 15 | Pre-Demo Audit | 🔲 Upcoming | |
| 16 | Demo Execution | 🔲 Upcoming | |

---

## Safety Principles

> **The LLM never directly triggers an action.**

Every money-moving action passes through:
1. ML prediction
2. Risk Firewall (ALLOW / REVIEW / BLOCK)
3. Deterministic Policy Engine
4. Idempotency check
5. Audit log write

This means RecoverFlow can always answer:  
*"Here is what the system predicted, here is what it was allowed to do, here is what it actually did, here is what happened financially, and here is how that compares with a simpler alternative."*

---

## Contributing

See [AGENTS.md](./AGENTS.md) for engineering rules, commit conventions, and pre-push checks. Every agent session and human contributor must follow those rules without exception.

---

## Buildathon

- **Event:** Razorpay /buildathon
- **Track:** 03 — AI Revenue Recovery
- **Build Window:** 20 August – 5 September 2026
