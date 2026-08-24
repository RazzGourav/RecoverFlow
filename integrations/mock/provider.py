"""
RecoverFlow API — Mock Provider Implementation

Why this file exists:
  Provides a deterministic simulation of the Razorpay APIs. 
  Used when PAYMENT_PROVIDER=mock (e.g. local dev, CI tests) to prevent 
  actual network calls while fulfilling the PaymentProvider Protocol.
"""

import uuid

from integrations.base import PaymentProvider


class MockProvider(PaymentProvider):
    """
    Mock Provider simulating Razorpay responses deterministically.
    """

    async def create_payment_link(
        self,
        amount_paise: int,
        currency: str,
        description: str,
        customer_details: dict,
        reference_id: str,
        expire_by: int | None = None,
    ) -> str:
        import asyncio
        if "timeout" in customer_details.get("name", "").lower():
            await asyncio.sleep(20)
            
        # Simulate payment link creation
        mock_id = f"plink_mock_{uuid.uuid4().hex[:8]}"
        return mock_id

    async def fetch_payment_link(self, payment_link_id: str) -> dict:
        return {
            "id": payment_link_id,
            "status": "paid",
            "amount": 50000,
        }

    async def cancel_payment_link(self, payment_link_id: str) -> bool:
        return True

    async def fetch_subscription(self, subscription_id: str) -> dict:
        return {
            "id": subscription_id,
            "status": "active",
            "plan_id": "plan_mock_123",
            "customer_id": "cust_mock_456",
        }

    async def fetch_payment(self, payment_id: str) -> dict:
        status = "captured" if ("captured" in payment_id.lower() or "retry" in payment_id.lower()) else "failed"
        return {
            "id": payment_id,
            "status": status,
            "amount": 50000,
            "currency": "INR",
        }

    async def create_invoice(self, amount_paise: int, currency: str, customer_details: dict, reference_id: str) -> str:
        return f"inv_mock_{uuid.uuid4().hex[:8]}"

    async def fetch_invoice(self, invoice_id: str) -> dict:
        return {
            "id": invoice_id,
            "status": "paid",
            "amount": 50000,
        }

    async def send_payment_method_update(self, customer_id: str, reference_id: str) -> str:
        return f"pmu_mock_{uuid.uuid4().hex[:8]}"

    async def fetch_payment_method_update(self, update_id: str) -> dict:
        return {
            "id": update_id,
            "status": "updated",
        }

    async def send_reminder(self, customer_details: dict, reference_id: str) -> str:
        return f"rem_mock_{uuid.uuid4().hex[:8]}"

    async def fetch_reminder(self, reminder_id: str) -> dict:
        return {
            "id": reminder_id,
            "status": "sent",
        }
