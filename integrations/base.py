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

    async def create_invoice(self, amount_paise: int, currency: str, customer_details: dict, reference_id: str) -> str:
        """
        Create and send an invoice. Returns external provider's unique ID for the invoice.
        """
        ...

    async def fetch_invoice(self, invoice_id: str) -> dict:
        """
        Fetch details of an existing invoice.
        """
        ...

    async def send_payment_method_update(self, customer_id: str, reference_id: str) -> str:
        """
        Send a payment method update request. Returns reference ID.
        """
        ...

    async def fetch_payment_method_update(self, update_id: str) -> dict:
        """
        Fetch status of a payment method update request.
        """
        ...

    async def send_reminder(self, customer_details: dict, reference_id: str) -> str:
        """
        Send a payment reminder. Returns reference ID.
        """
        ...

    async def fetch_reminder(self, reminder_id: str) -> dict:
        """
        Fetch status of a sent reminder.
        """
        ...
