#!/usr/bin/env python3
"""
RecoverFlow — Webhook Simulator

Why this script exists:
  Provides a fast, local way to test the webhook ingestion and normalisation
  pipeline without needing a real Razorpay sandbox account or ngrok.
  It computes the correct HMAC signature using the local secret so the API
  accepts it as a legitimate request.
"""

import argparse
import hashlib
import hmac
import json
import time
import uuid

import httpx

# Default to the same REPLACE_ME value in .env.example
WEBHOOK_SECRET = "REPLACE_ME"
API_URL = "http://localhost:8000/webhooks/razorpay"


def generate_signature(payload: bytes, secret: str) -> str:
    return hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()


def get_payment_failed_payload() -> dict:
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


def main():
    parser = argparse.ArgumentParser(description="Simulate Razorpay Webhooks.")
    parser.add_argument("--url", default=API_URL, help="Target API URL")
    parser.add_argument("--secret", default=WEBHOOK_SECRET, help="Webhook secret")
    parser.add_argument("--event", choices=["payment.failed"], default="payment.failed", help="Event type to simulate")
    parser.add_argument("--id", help="Override the event ID (useful for testing idempotency)")
    args = parser.parse_args()

    if args.event == "payment.failed":
        payload = get_payment_failed_payload()
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
