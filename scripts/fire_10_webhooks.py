import asyncio
import httpx
import uuid
import json
import hmac
import hashlib
import time
import random

WEBHOOK_SECRET = "test_webhook_secret_123"
API_URL = "http://localhost:8000/webhooks/razorpay"

def generate_signature(payload: bytes, secret: str) -> str:
    return hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()

def get_payment_failed_payload(customer_name: str, amount: int, error_reason: str, is_captured_mock: bool = False) -> dict:
    pay_prefix = "pay_captured_" if is_captured_mock else "pay_mock_"
    return {
        "entity": "event",
        "account_id": "acc_mock_123",
        "event": "payment.failed",
        "contains": ["payment"],
        "payload": {
            "payment": {
                "entity": {
                    "id": f"{pay_prefix}{uuid.uuid4().hex[:8]}",
                    "entity": "payment",
                    "amount": amount,
                    "currency": "INR",
                    "status": "failed",
                    "order_id": f"order_mock_{uuid.uuid4().hex[:8]}",
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

async def fire_webhook(client, index):
    # Variety for the load test to get different recoverability scores
    amounts = [10000, 25000, 50000, 75000, 100000, 300000] # Random amounts
    reasons = [
        "network_error",      # TEMPORARY (high recoverability)
        "insufficient_funds", # PAYMENT_METHOD (medium)
        "card_expired",       # PERSISTENT (low recoverability)
        "timeout"             # TEMPORARY (high recoverability)
    ]
    
    amount = random.choice(amounts)
    reason = random.choice(reasons)
    
    # Force cases 0 and 1 to be high recoverability, low amount for AUTONOMOUS
    if index < 2:
        amount = 5000 # 50 INR
        reason = "network_error"
        
    payload = get_payment_failed_payload(f"Customer {index}", amount, reason, is_captured_mock=(index == 9))
    event_id = f"batch_mock_{uuid.uuid4().hex[:8]}"
    payload_bytes = json.dumps(payload, separators=(',', ':')).encode("utf-8")
    signature = generate_signature(payload_bytes, WEBHOOK_SECRET)
    headers = {
        "Content-Type": "application/json",
        "X-Razorpay-Signature": signature,
        "X-Razorpay-Event-Id": event_id,
    }
    
    response = await client.post(API_URL, content=payload_bytes, headers=headers)
    print(f"Webhook {index} fired ({amount} paise, {reason}) -> Status: {response.status_code}")
    return response.status_code

async def main():
    async with httpx.AsyncClient() as client:
        tasks = [fire_webhook(client, i) for i in range(10)]
        results = await asyncio.gather(*tasks)
        print("Completed 10 webhooks!")

if __name__ == "__main__":
    asyncio.run(main())
