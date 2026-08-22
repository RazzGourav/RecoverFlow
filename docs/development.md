# RecoverFlow — Development Guide

## End-to-End Pipeline

RecoverFlow was built iteratively across 14 phases, evolving from a simple API to a full-fledged AI control plane with ML inference, budget optimization, and a reactive frontend.

### 1. Local Setup
To run RecoverFlow locally from scratch:
1. Copy `.env.example` to `.env`.
2. Ensure Docker is installed and running.
3. Run `docker compose up --build -d` to spin up the API, Frontend, PostgreSQL, Redis, and ARQ workers.
4. Execute `./scripts/smoke_test.sh` to verify system health.

### 2. The Development Flow
- **Backend (FastAPI)**: Code resides in `apps/api/`. Any changes to database models require an Alembic migration (`alembic revision --autogenerate -m "..."` followed by `alembic upgrade head`). 
- **Frontend (Next.js)**: Code resides in `apps/web/`. It uses Tailwind CSS and shadcn/ui components. Run `npm run dev` in the web directory for hot-reloading outside of Docker.
- **Machine Learning (XGBoost)**: Code in `ai/`. Run `python scripts/seed_db.py` to generate the synthetic data and populate the development database.

### 3. CI/CD Pipeline
Every pull request is subjected to the Pre-Push Check sequence defined in GitHub Actions (`.github/workflows/ci.yml`):
- **Backend Checks**: `ruff check .` (Linting), `mypy .` (Static Typing), and `pytest -q` (Unit & Integration tests).
- **Frontend Checks**: `npm run lint` (ESLint), `npm run typecheck` (TypeScript compiler), and `npm test` (Vitest components).
- **Docker Validation**: The pipeline builds the production Docker images to guarantee the environment is reproducible.

### 4. Running Benchmarks & Simulations
The Simulation Lab allows testing of new ML models and rule policies. To run a benchmark against the held-out test set:
```bash
# Inside the API container
python /app/scripts/run_final_benchmark.py
```
This script will bypass database mutations and generate a markdown report (`evaluation/reports/final-benchmark.md`) comparing AI optimal routing against baseline rule strategies.

### 5. Managing Failures
All unexpected states (e.g., Duplicate Webhooks, Budget Exhaustion, Stale Validation Blocks) are recorded as `AuditEvent` rows and surfaced in the **Failure Center** dashboard. When debugging, always check the `correlation_id` in structured logs to trace a request from the webhook entrypoint through the ARQ workers.
