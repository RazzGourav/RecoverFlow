"""
Load test: 7 diverse action types + 1 case with 'captured' payment_id
to verify the validation discriminator blocks appropriately.

The mock provider's fetch_payment returns status='captured' when
'captured' is in the payment_id, causing validation to block any
non-NO_ACTION action type.
"""

import asyncio
import httpx
import uuid
import json
import hmac
import hashlib
import time

WEBHOOK_SECRET = "test_webhook_secret_123"
API_URL = "http://localhost:8000/webhooks/razorpay"

ACTION_TYPES = [
    "RETRY",
    "PAYMENT_LINK",
    "INVOICE",
    "PAYMENT_METHOD_UPDATE",
    "REMINDER",
    "HUMAN_ESCALATION",
    "NO_ACTION",
]

def generate_signature(payload: bytes, secret: str) -> str:
    return hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()

def get_payment_failed_payload(customer_name: str, amount: int, error_reason: str, payment_id: str | None = None) -> dict:
    pid = payment_id or f"pay_mock_{uuid.uuid4().hex[:8]}"
    return {
        "entity": "event",
        "account_id": "acc_mock_123",
        "event": "payment.failed",
        "contains": ["payment"],
        "payload": {
            "payment": {
                "entity": {
                    "id": pid,
                    "entity": "payment",
                    "amount": amount,
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
                    "error_description": "Payment failed.",
                    "error_source": "customer",
                    "error_step": "payment_authorization",
                    "error_reason": error_reason,
                    "created_at": int(time.time()),
                }
            }
        },
        "created_at": int(time.time()),
    }

async def fire_webhook(client, label, amount, payment_id=None):
    reason = "network_error"
    payload = get_payment_failed_payload(f"Customer {label}", amount, reason, payment_id=payment_id)
    event_id = f"batch_val_{uuid.uuid4().hex[:8]}"
    payload_bytes = json.dumps(payload, separators=(',', ':')).encode("utf-8")
    signature = generate_signature(payload_bytes, WEBHOOK_SECRET)
    headers = {
        "Content-Type": "application/json",
        "X-Razorpay-Signature": signature,
        "X-Razorpay-Event-Id": event_id,
    }

    response = await client.post(API_URL, content=payload_bytes, headers=headers)
    print(f"  [{label}] amount={amount}, payment_id={payload['payload']['payment']['entity']['id']} -> HTTP {response.status_code}")
    return response.status_code

async def main():
    async with httpx.AsyncClient() as client:
        tasks = []

        # 7 normal action-type cases (amounts 5001-5007, ones digit triggers testing hook)
        print("Firing 7 normal action-type webhooks:")
        for index, action_type in enumerate(ACTION_TYPES):
            base_amount = 5000
            amount = base_amount + index + 1
            tasks.append(fire_webhook(client, f"{action_type}", amount))

        # 8th case: payment_id contains 'captured' to trip validation discriminator
        # Using amount 5008 (ones digit 8 -> no matching action in testing hook, but
        # the important thing is the payment_id causes fetch_payment to return 'captured')
        print("Firing 1 validation-discriminator webhook (payment_id contains 'captured'):")
        tasks.append(fire_webhook(
            client,
            "VALIDATION_BLOCK_TEST",
            5002,  # ones digit 2 -> PAYMENT_LINK via testing hook
            payment_id=f"pay_captured_{uuid.uuid4().hex[:8]}"
        ))

        results = await asyncio.gather(*tasks)
        print(f"\nAll {len(results)} webhooks fired. Waiting for async processing...")

if __name__ == "__main__":
    asyncio.run(main())
