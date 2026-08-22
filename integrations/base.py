"""
RecoverFlow API — Payment Provider Base Interface

Why this file exists:
  Defines the strict `PaymentProvider` contract. The application core MUST NOT
  import Razorpay SDK directly. All payment-related capabilities must be exposed
  through this Protocol. This enables deterministic testing via the MockProvider.
"""

from typing import Protocol, runtime_checkable


@runtime_checkable
class PaymentProvider(Protocol):
    """
    Standard interface for payment operations.
    All implementations (Razorpay, Mock) must conform to this Protocol.
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
        """
        Create a payment link for a specific amount.
        Returns the external provider's unique ID for the created link.
        """
        ...

    async def fetch_payment_link(self, payment_link_id: str) -> dict:
        """
        Fetch details of an existing payment link.
        """
        ...

    async def cancel_payment_link(self, payment_link_id: str) -> bool:
        """
        Cancel an active payment link.
        Returns True if cancelled successfully.
        """
        ...

    async def fetch_subscription(self, subscription_id: str) -> dict:
        """
        Fetch details of a subscription.
        """
        ...

    async def fetch_payment(self, payment_id: str) -> dict:
        """
        Fetch details of a specific payment.
        """
        ...
