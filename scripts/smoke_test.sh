#!/usr/bin/env bash
# =============================================================================
# RecoverFlow Smoke Test
# =============================================================================
# Runs after `docker compose up --build -d` to verify the system is alive.
# Called by: make smoke, CI pipeline, pre-push check.
# Exits 0 on success, 1 on any failure.
# =============================================================================
set -euo

API_URL="${API_URL:-http://localhost:8000}"
FRONTEND_URL="${FRONTEND_URL:-http://localhost:3000}"
MAX_RETRIES=20
RETRY_DELAY=5

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
log()  { echo "[smoke] $*"; }
fail() { echo "[smoke] FAIL: $*" >&2; exit 1; }
pass() { echo "[smoke] PASS: $*"; }

wait_for() {
    local url="$1" label="$2" attempts=0
    log "Waiting for $label at $url ..."
    until curl -sf "$url" > /dev/null 2>&1; do
        attempts=$((attempts + 1))
        if [[ $attempts -ge $MAX_RETRIES ]]; then
            fail "$label not reachable after $((MAX_RETRIES * RETRY_DELAY))s"
        fi
        sleep "$RETRY_DELAY"
    done
    pass "$label is reachable"
}

# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------
log "Starting smoke tests..."

# 1. API health
wait_for "${API_URL}/health" "API /health"
HEALTH=$(curl -sf "${API_URL}/health")
echo "$HEALTH" | grep -q '"status"' || fail "Health response missing 'status' field"
pass "API health endpoint returned valid JSON"

# 2. API docs
wait_for "${API_URL}/docs" "API /docs (Swagger UI)"
pass "API /docs is reachable"

# 3. Frontend
wait_for "${FRONTEND_URL}" "Frontend"
pass "Frontend is reachable"

# 4. Database connectivity (via health endpoint reporting db=connected)
echo "$HEALTH" | grep -q '"database":"connected"' \
    || fail "API health reports database not connected"
pass "Database is connected per health endpoint"

log ""
log "All smoke tests passed."
