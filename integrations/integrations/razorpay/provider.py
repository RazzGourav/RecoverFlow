"""
RecoverFlow API — Razorpay Provider Implementation

Why this file exists:
  Implements the PaymentProvider Protocol using the official Razorpay Python SDK.
  It interacts with Razorpay APIs using the credentials provided in config.
"""

import asyncio
from concurrent.futures import ThreadPoolExecutor

import razorpay
from config import settings

from integrations.integrations.base import PaymentProvider


class RazorpayProvider(PaymentProvider):
    """
    Razorpay SDK Wrapper.
    Uses a ThreadPoolExecutor to make synchronous SDK calls asynchronous.
    """

    def __init__(self):
        # We only want to instantiate this in TEST mode for now, per requirements.
        # But we rely on the keys being test mode keys ("rzp_test_...").
        if not settings.razorpay_key_id.startswith("rzp_test_") and settings.razorpay_key_id != "REPLACE_ME":
            import structlog
            logger = structlog.get_logger()
            logger.warning("RazorpayProvider initialized with non-test keys!")

        self.client = razorpay.Client(
            auth=(settings.razorpay_key_id, settings.razorpay_key_secret)
        )
        # Thread pool to run blocking SDK calls
        self.executor = ThreadPoolExecutor(max_workers=5)

    async def _run_in_executor(self, func, *args, **kwargs):
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            self.executor, lambda: func(*args, **kwargs)
        )

    async def create_payment_link(
        self,
        amount_paise: int,
        currency: str,
        description: str,
        customer_details: dict,
        reference_id: str,
        expire_by: int | None = None,
    ) -> str:
        payload = {
            "amount": amount_paise,
            "currency": currency,
            "accept_partial": False,
            "description": description,
            "customer": customer_details,
            "notify": {"sms": False, "email": False},
            "reminder_enable": False,
            "reference_id": reference_id,
        }
        if expire_by:
            payload["expire_by"] = expire_by

        response = await self._run_in_executor(
            self.client.payment_link.create, payload
        )
        return response["id"]

    async def fetch_payment_link(self, payment_link_id: str) -> dict:
        return await self._run_in_executor(
            self.client.payment_link.fetch, payment_link_id
        )

    async def cancel_payment_link(self, payment_link_id: str) -> bool:
        response = await self._run_in_executor(
            self.client.payment_link.cancel, payment_link_id
        )
        return response.get("status") == "cancelled"

    async def fetch_subscription(self, subscription_id: str) -> dict:
        return await self._run_in_executor(
            self.client.subscription.fetch, subscription_id
        )

    async def fetch_payment(self, payment_id: str) -> dict:
        return await self._run_in_executor(
            self.client.payment.fetch, payment_id
        )
