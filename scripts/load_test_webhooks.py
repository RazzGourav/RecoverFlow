#!/usr/bin/env python3
"""
RecoverFlow — Load Test: fire N webhooks in quick succession.

Sends 10 payment.failed webhooks concurrently, then queries the DB
to verify that all produce RecoveryCase + Action rows.

Usage inside API container:
  python3 /tmp/load_test_webhooks.py

Requires: httpx already installed in the API container.
"""

import asyncio
import hashlib
import hmac
import json
import os
import time
import uuid

import httpx

WEBHOOK_SECRET = os.environ.get("RAZORPAY_WEBHOOK_SECRET", "test_webhook_secret_123")
API_URL = "http://localhost:8000"
N_WEBHOOKS = 10


def make_payment_failed_payload(idx: int) -> tuple[str, bytes]:
    """Return (event_id, payload_bytes) for one payment.failed event."""
    event_id = f"ev_loadtest_{idx}_{uuid.uuid4().hex[:6]}"
    payload = {
        "entity": "event",
        "account_id": "acc_loadtest",
        "event": "payment.failed",
        "contains": ["payment"],
        "payload": {
            "payment": {
                "entity": {
                    "id": f"pay_loadtest_{uuid.uuid4().hex[:8]}",
                    "entity": "payment",
                    "amount": 75000 + idx * 100,
                    "currency": "INR",
                    "status": "failed",
                    "order_id": f"order_loadtest_{uuid.uuid4().hex[:8]}",
                    "customer_id": f"cust_loadtest_{idx}",
                    "email": f"loadtest{idx}@example.com",
                    "contact": "+919876543210",
                    "notes": {
                        "customer_name": f"Load Test User {idx}",
                        "customer_email": f"loadtest{idx}@example.com",
                    },
                    "invoice_id": None,
                    "international": False,
                    "method": "card",
                    "amount_refunded": 0,
                    "refund_status": None,
                    "captured": False,
                    "description": f"Load test payment {idx}",
                    "card_id": "card_loadtest",
                    "error_code": "BAD_REQUEST_ERROR",
                    "error_description": "Payment failed due to insufficient funds.",
                    "error_source": "customer",
                    "error_step": "payment_authorization",
                    "error_reason": "payment_failed",
                    "created_at": int(time.time()),
                }
            }
        },
        "created_at": int(time.time()),
    }
    body = json.dumps(payload, separators=(",", ":")).encode()
    return event_id, body


def sign(body: bytes, secret: str) -> str:
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


async def send_one(client: httpx.AsyncClient, idx: int) -> dict:
    event_id, body = make_payment_failed_payload(idx)
    sig = sign(body, WEBHOOK_SECRET)
    headers = {
        "Content-Type": "application/json",
        "X-Razorpay-Signature": sig,
        "X-Razorpay-Event-Id": event_id,
    }
    try:
        r = await client.post(f"{API_URL}/webhooks/razorpay", content=body, headers=headers, timeout=30)
        return {"idx": idx, "status": r.status_code, "event_id": event_id, "body": r.text[:200]}
    except Exception as e:
        return {"idx": idx, "status": "ERROR", "error": str(e)}


async def main() -> None:
    print(f"Firing {N_WEBHOOKS} webhooks concurrently to {API_URL}...")
    t0 = time.time()
    async with httpx.AsyncClient() as client:
        tasks = [send_one(client, i) for i in range(N_WEBHOOKS)]
        results = await asyncio.gather(*tasks)
    elapsed = time.time() - t0

    ok = sum(1 for r in results if r.get("status") == 200)
    fail = len(results) - ok

    print(f"\nResults ({elapsed:.2f}s total):")
    for r in results:
        print(f"  [{r['idx']}] status={r['status']} event={r.get('event_id','?')}")
    
    print(f"\nSummary: {ok}/{N_WEBHOOKS} succeeded, {fail} failed")

    # Give worker time to process
    print("\nWaiting 8s for worker to process jobs...")
    await asyncio.sleep(8)

    # Query DB for cases and actions created in the last 60 seconds
    import subprocess
    result = subprocess.run(
        [
            "psql",
            "-U", "recoverflow",
            "-d", "recoverflow",
            "-c",
            """
            SELECT
              (SELECT count(*) FROM recovery_cases
               WHERE created_at > NOW() - INTERVAL '120 seconds') AS new_cases,
              (SELECT count(*) FROM actions
               WHERE created_at > NOW() - INTERVAL '120 seconds') AS new_actions;
            """
        ],
        capture_output=True, text=True
    )
    print("\nDB query output:")
    print(result.stdout or result.stderr)


if __name__ == "__main__":
    asyncio.run(main())
