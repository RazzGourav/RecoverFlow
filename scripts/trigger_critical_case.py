#!/usr/bin/env python3
"""
Trigger a critical high-value case for demo purposes.
"""

import hashlib
import hmac
import json
import time
import uuid

import httpx

WEBHOOK_SECRET = "REPLACE_ME"
API_URL = "http://localhost:8000/webhooks/razorpay"


def generate_signature(payload: bytes, secret: str) -> str:
    return hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()

def main():
    payload = {
        "entity": "event",
        "account_id": "acc_mock_123",
        "event": "payment.failed",
        "contains": ["payment"],
        "payload": {
            "payment": {
                "entity": {
                    "id": f"pay_mock_{uuid.uuid4().hex[:8]}",
                    "entity": "payment",
                    "amount": 3000000, # 30,000 INR - trips HUMAN_APPROVAL
                    "currency": "INR",
                    "status": "failed",
                    "order_id": f"order_mock_{uuid.uuid4().hex[:8]}",
                    "customer_id": f"cust_mock_{uuid.uuid4().hex[:8]}",
                    "email": "high-risk@example.com",
                    "contact": "+919876543210",
                    "notes": {
                        "customer_name": "High Value Demo Customer",
                    },
                    "error_code": "BAD_REQUEST_ERROR",
                    "error_description": "Payment failed.",
                    "created_at": int(time.time()),
                }
            }
        },
        "created_at": int(time.time()),
    }

    event_id = f"ev_mock_{uuid.uuid4().hex[:8]}"
    payload_bytes = json.dumps(payload, separators=(',', ':')).encode("utf-8")
    signature = generate_signature(payload_bytes, WEBHOOK_SECRET)

    headers = {
        "Content-Type": "application/json",
        "X-Razorpay-Signature": signature,
        "X-Razorpay-Event-Id": event_id,
    }

    print(f"Triggering high-risk case to {API_URL}")
    response = httpx.post(API_URL, content=payload_bytes, headers=headers)
    print(f"Status: {response.status_code}")
    print(response.json())

if __name__ == "__main__":
    main()
