"""
RecoverFlow API — Payment Provider Factory

Why this file exists:
  Central point for instantiating the correct PaymentProvider based on the 
  environment configuration. Ensures the app only knows about PaymentProvider.
"""

from config import settings

from integrations.base import PaymentProvider


def get_provider() -> PaymentProvider:
    """
    Returns the configured PaymentProvider instance.
    """
    if settings.payment_provider.lower() == "razorpay":
        from integrations.razorpay.provider import RazorpayProvider
        return RazorpayProvider()
    elif settings.payment_provider.lower() == "mock":
        from integrations.mock.provider import MockProvider
        return MockProvider()
    else:
        raise ValueError(
            f"Unsupported PAYMENT_PROVIDER: {settings.payment_provider}"
        )
