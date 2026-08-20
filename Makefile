# =============================================================================
# RecoverFlow Makefile
# =============================================================================
# Convenience targets for common developer workflows.
# All targets print what they're doing so engineers new to the repo can follow.
# =============================================================================

.PHONY: help up down build logs migrate test lint typecheck clean smoke

# Default target — show help.
help:
	@echo ""
	@echo "  RecoverFlow — Developer Commands"
	@echo "  ================================"
	@echo ""
	@echo "  make up          Start all services (build if needed)"
	@echo "  make build       Force rebuild all Docker images"
	@echo "  make down        Stop and remove containers"
	@echo "  make logs        Tail logs from all services"
	@echo "  make migrate     Run Alembic migrations against running Postgres"
	@echo "  make test        Run backend pytest suite"
	@echo "  make lint        Run ruff linter on the API"
	@echo "  make typecheck   Run mypy type checker on the API"
	@echo "  make smoke       Run smoke test script"
	@echo "  make clean       Remove all containers, volumes, and images"
	@echo "  make seed-db     Seed the local database with synthetic cases"
	@echo "  make train       Train ML models and save artifacts"
	@echo ""

# Start services (attach mode — Ctrl+C stops them).
up:
	@echo ">>> Starting RecoverFlow..."
	docker compose up --build

# Build images without starting.
build:
	@echo ">>> Building Docker images..."
	docker compose build

# Stop services.
down:
	@echo ">>> Stopping RecoverFlow..."
	docker compose down

# Tail logs.
logs:
	docker compose logs -f

# Run Alembic migrations against the running Postgres container.
migrate:
	@echo ">>> Running Alembic migrations..."
	docker compose exec api alembic upgrade head

# Run backend tests.
test:
	@echo ">>> Running backend tests..."
	docker compose exec api pytest -q /app/../../tests/

# Seed the database with synthetic cases for local dev.
seed-db:
	@echo ">>> Generating synthetic dataset (if missing) and seeding DB..."
	docker compose exec api python /app/../../data/synthetic/generate.py
	docker compose exec api python /app/../../scripts/seed_db.py

# Train ML models.
train:
	@echo ">>> Training Recovery Model..."
	docker compose exec api python /app/../../ai/models/recovery/train.py
	@echo ">>> Training Action Effectiveness Model..."
	docker compose exec api python /app/../../ai/models/intervention/train.py

# Run linter.
lint:
	@echo ">>> Running ruff linter..."
	docker compose exec api ruff check .

# Run type checker.
typecheck:
	@echo ">>> Running mypy..."
	docker compose exec api mypy .

# Run smoke test.
smoke:
	@echo ">>> Running smoke tests..."
	bash scripts/smoke_test.sh

# Nuke everything — including volumes (destroys DB data).
clean:
	@echo ">>> WARNING: Removing all containers and volumes..."
	docker compose down -v --rmi local
	@echo ">>> Done."
