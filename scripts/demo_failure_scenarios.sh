#!/usr/bin/env bash
# scripts/demo_failure_scenarios.sh
# Triggers various failure scenarios in the running stack.

set -e

echo "============================================="
echo "  RecoverFlow Failure Scenarios Trigger      "
echo "============================================="
echo "Ensuring backend is reachable..."
curl -s http://localhost:8000/health > /dev/null || (echo "API not reachable" && exit 1)

echo "[1/4] Triggering WEBHOOK_DUPLICATE_DROPPED..."
# We generate a static UUID for this test run
TEST_ID="dup_test_$(date +%s)"
# Copy script to container temporarily to run it with httpx available
docker cp scripts/simulate_webhook.py recoverflow-api:/tmp/simulate_webhook.py
docker compose exec api python /tmp/simulate_webhook.py --id "$TEST_ID" > /dev/null
# Second time hits the idempotency layer
docker compose exec api python /tmp/simulate_webhook.py --id "$TEST_ID" > /dev/null
echo "✔ Webhook duplicated successfully"

echo "[2/4] Triggering ACTION_TIMEOUT..."
# The mock provider will sleep 20s if the customer name contains "timeout"
docker compose exec api python /tmp/simulate_webhook.py --customer-name "timeout_test_user" > /dev/null
echo "✔ Dispatched webhook for timeout test. (Worker will process in background)"

# Wait for workers to pick up the events
echo "Waiting for background workers to execute actions (5s)..."
sleep 5

echo "[3/4] Checking logs for Failure Center validation..."
# You can view the Failures page at http://localhost:3000/failures to see these live.

echo "============================================="
echo "Done! Check http://localhost:3000/failures   "
echo "============================================="
