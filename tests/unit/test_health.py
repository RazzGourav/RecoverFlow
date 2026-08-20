"""Unit tests for the /health endpoint and /webhooks/razorpay stub."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_returns_200(client: AsyncClient) -> None:
    """Health endpoint must return 200 regardless of DB state."""
    response = await client.get("/health")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_health_response_schema(client: AsyncClient) -> None:
    """Health response must include required fields."""
    response = await client.get("/health")
    data = response.json()

    assert "status" in data
    assert "database" in data
    assert "service" in data
    assert data["service"] == "recoverflow-api"


@pytest.mark.asyncio
async def test_health_status_values(client: AsyncClient) -> None:
    """Health status must be 'ok' or 'degraded', never anything else."""
    response = await client.get("/health")
    data = response.json()

    assert data["status"] in {"ok", "degraded"}
    assert data["database"] in {"connected", "unavailable"}


@pytest.mark.asyncio
async def test_health_phase_field(client: AsyncClient) -> None:
    """Health response must report the current build phase."""
    response = await client.get("/health")
    data = response.json()

    assert "phase" in data
    assert data["phase"] == "0-foundation"


@pytest.mark.asyncio
async def test_webhook_endpoint_returns_501(client: AsyncClient) -> None:
    """Webhook endpoint must return 501 in Phase 0 (not yet implemented)."""
    response = await client.post(
        "/webhooks/razorpay",
        json={"event": "payment.failed", "payload": {}},
    )
    assert response.status_code == 501


@pytest.mark.asyncio
async def test_webhook_response_has_detail(client: AsyncClient) -> None:
    """Webhook 501 response must explain why it's not implemented."""
    response = await client.post("/webhooks/razorpay", json={})
    data = response.json()

    assert "detail" in data
    assert "Phase 1" in data["detail"]
