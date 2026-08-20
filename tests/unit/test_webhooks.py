"""
RecoverFlow API — Unit tests for the webhook receiver.
"""

from __future__ import annotations

import hashlib
import hmac
import json
from unittest.mock import AsyncMock

import pytest
from httpx import AsyncClient
from sqlalchemy.exc import IntegrityError

from config import settings


def generate_signature(payload: bytes, secret: str) -> str:
    return hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()


@pytest.fixture
def valid_payload() -> dict:
    return {
        "event": "payment.failed",
        "payload": {
            "payment": {
                "entity": {
                    "id": "pay_mock_123",
                    "amount": 50000,
                }
            }
        }
    }


@pytest.mark.asyncio
async def test_missing_signature(client: AsyncClient, valid_payload: dict) -> None:
    # Ensure secret is not REPLACE_ME so validation actually runs
    settings.razorpay_webhook_secret = "test_secret"
    
    response = await client.post(
        "/webhooks/razorpay",
        json=valid_payload,
        headers={"X-Razorpay-Event-Id": "ev_123"},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid webhook signature"


@pytest.mark.asyncio
async def test_invalid_signature(client: AsyncClient, valid_payload: dict) -> None:
    settings.razorpay_webhook_secret = "test_secret"
    
    response = await client.post(
        "/webhooks/razorpay",
        json=valid_payload,
        headers={
            "X-Razorpay-Event-Id": "ev_123",
            "X-Razorpay-Signature": "invalid_signature",
        },
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid webhook signature"


@pytest.mark.asyncio
async def test_valid_signature(client: AsyncClient, valid_payload: dict) -> None:
    settings.razorpay_webhook_secret = "test_secret"
    
    payload_bytes = json.dumps(valid_payload).encode("utf-8")
    # For httpx test client, json= serializes with no spaces (separators=(',', ':')) by default
    # but to be safe we'll send content directly
    payload_bytes = json.dumps(valid_payload, separators=(',', ':')).encode("utf-8")
    sig = generate_signature(payload_bytes, "test_secret")
    
    response = await client.post(
        "/webhooks/razorpay",
        content=payload_bytes,
        headers={
            "X-Razorpay-Event-Id": "ev_123",
            "X-Razorpay-Signature": sig,
            "Content-Type": "application/json",
        },
    )
    assert response.status_code == 200
    assert response.json()["status"] == "received"


@pytest.mark.asyncio
async def test_malformed_payload(client: AsyncClient) -> None:
    settings.razorpay_webhook_secret = "test_secret"
    
    payload_bytes = b"not_json"
    sig = generate_signature(payload_bytes, "test_secret")
    
    response = await client.post(
        "/webhooks/razorpay",
        content=payload_bytes,
        headers={
            "X-Razorpay-Event-Id": "ev_123",
            "X-Razorpay-Signature": sig,
            "Content-Type": "application/json",
        },
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid JSON payload"


@pytest.mark.asyncio
async def test_idempotency_duplicate_event(client: AsyncClient, valid_payload: dict) -> None:
    """Test that a duplicate event (IntegrityError) is handled gracefully (returns 200)."""
    settings.razorpay_webhook_secret = "test_secret"
    
    payload_bytes = json.dumps(valid_payload, separators=(',', ':')).encode("utf-8")
    sig = generate_signature(payload_bytes, "test_secret")
    
    # We need to mock the DB to raise IntegrityError on commit
    from main import app
    from dependencies.db import get_db
    from collections.abc import AsyncGenerator
    from sqlalchemy.ext.asyncio import AsyncSession
    
    async def _mock_db_integrity_error() -> AsyncGenerator[AsyncSession, None]:
        mock = AsyncMock(spec=AsyncSession)
        mock.execute.return_value = AsyncMock()
        mock.commit.side_effect = IntegrityError("mock error", params=None, orig=Exception())
        yield mock

    app.dependency_overrides[get_db] = _mock_db_integrity_error

    response = await client.post(
        "/webhooks/razorpay",
        content=payload_bytes,
        headers={
            "X-Razorpay-Event-Id": "ev_dup_123",
            "X-Razorpay-Signature": sig,
            "Content-Type": "application/json",
        },
    )
    
    # Must return 200 OK so Razorpay doesn't retry, but status is 'duplicate'
    assert response.status_code == 200
    assert response.json()["status"] == "duplicate"
