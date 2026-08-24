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

def get_payment_failed_payload(customer_name: str, amount: int, error_reason: str) -> dict:
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

async def fire_webhook(client, index, action_type):
    # Base amount is 5000 paise (50 INR) so it's always AUTONOMOUS (< 250000 limit)
    base_amount = 5000
    amount = base_amount + index + 1 # +1 because modulo index starts at 1
    
    reason = "network_error"
        
    payload = get_payment_failed_payload(f"Customer {index}", amount, reason)
    event_id = f"batch_mock_{uuid.uuid4().hex[:8]}"
    payload_bytes = json.dumps(payload, separators=(',', ':')).encode("utf-8")
    signature = generate_signature(payload_bytes, WEBHOOK_SECRET)
    headers = {
        "Content-Type": "application/json",
        "X-Razorpay-Signature": signature,
        "X-Razorpay-Event-Id": event_id,
    }
    
    response = await client.post(API_URL, content=payload_bytes, headers=headers)
    print(f"Webhook fired: {action_type} (amount: {amount}) -> Status: {response.status_code}")
    return response.status_code

async def main():
    async with httpx.AsyncClient() as client:
        tasks = []
        for index, action_type in enumerate(ACTION_TYPES):
            tasks.append(fire_webhook(client, index, action_type))
            
        results = await asyncio.gather(*tasks)
        print("Completed all action type webhooks!")

if __name__ == "__main__":
    asyncio.run(main())
