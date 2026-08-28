#!/usr/bin/env python3
"""
RecoverFlow — Webhook Simulator

Why this script exists:
  Provides a fast, local way to test the webhook ingestion and normalisation
  pipeline without needing a real Razorpay sandbox account or ngrok.
  It computes the correct HMAC signature using the local secret so the API
  accepts it as a legitimate request.

Usage:
  # From host (auto-reads local .env if present):
  python3 scripts/simulate_webhook.py

  # Override secret directly:
  python3 scripts/simulate_webhook.py --secret test_webhook_secret_123
"""

import argparse
import hashlib
import hmac
import json
import os
import time
import uuid

import httpx

# Read secret from environment so the script works without hardcoding.
# RAZORPAY_WEBHOOK_SECRET must match what the running API container uses.
WEBHOOK_SECRET = os.environ.get("RAZORPAY_WEBHOOK_SECRET", "REPLACE_ME")
API_URL = "http://localhost:8000/webhooks/razorpay"


def generate_signature(payload: bytes, secret: str) -> str:
    """Compute HMAC-SHA256 signature that the Razorpay webhook handler validates."""
    return hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()


def get_payment_failed_payload(customer_name: str = "Customer") -> dict:
    return {
        "entity": "event",
        "account_id": "acc_mock_123",
        "event": "payment.failed",
        "contains": ["payment"],
        "payload": {
            "payment": {
                "entity": {
                    "id": f"pay_mock_{uuid.uuid4().hex[:8]}",
                    "entity": "payment",
                    "amount": 50000,
                    "currency": "INR",
                    "status": "failed",
                    "order_id": f"order_mock_{uuid.uuid4().hex[:8]}",
                    "customer_id": f"cust_mock_{uuid.uuid4().hex[:8]}",
                    "email": "test@example.com",
                    "contact": "+919876543210",
                    "notes": {
                        "customer_name": customer_name,
                        "customer_email": "test@example.com"
                    },
                    "invoice_id": None,
                    "international": False,
                    "method": "card",
                    "amount_refunded": 0,
                    "refund_status": None,
                    "captured": False,
                    "description": "Subscription payment",
                    "card_id": "card_mock_123",
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


def main() -> None:  # noqa: D103
    parser = argparse.ArgumentParser(
        description="Simulate Razorpay Webhooks against the local RecoverFlow API."
    )
    parser.add_argument("--url", default=API_URL, help="Target API URL (default: %(default)s)")
    parser.add_argument(
        "--secret",
        default=WEBHOOK_SECRET,
        help="Webhook HMAC secret. Defaults to RAZORPAY_WEBHOOK_SECRET env var.",
    )
    parser.add_argument(
        "--event",
        choices=["payment.failed"],
        default="payment.failed",
        help="Event type to simulate (default: %(default)s)",
    )
    parser.add_argument("--id", help="Override the event ID (useful for testing idempotency)")
    parser.add_argument("--customer-name", default="Customer", help="Set the customer name in notes")
    args = parser.parse_args()

    if args.secret == "REPLACE_ME":
        print(
            "WARNING: Using placeholder secret 'REPLACE_ME'. "
            "Set RAZORPAY_WEBHOOK_SECRET in your environment or pass --secret."
        )

    if args.event == "payment.failed":
        payload = get_payment_failed_payload(args.customer_name)
    else:
        print(f"Event {args.event} not implemented in simulator yet.")
        return

    event_id = args.id if args.id else f"ev_mock_{uuid.uuid4().hex[:8]}"

    payload_bytes = json.dumps(payload, separators=(',', ':')).encode("utf-8")
    signature = generate_signature(payload_bytes, args.secret)

    headers = {
        "Content-Type": "application/json",
        "X-Razorpay-Signature": signature,
        "X-Razorpay-Event-Id": event_id,
    }

    print(f"Sending {args.event} to {args.url}")
    print(f"Event ID: {event_id}")
    print(f"Signature: {signature}")

    try:
        response = httpx.post(args.url, content=payload_bytes, headers=headers)
        print(f"\nResponse: {response.status_code}")
        print(response.json())
    except Exception as e:
        print(f"\nRequest failed: {e}")


if __name__ == "__main__":
    main()
