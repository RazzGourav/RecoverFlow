import pytest
from httpx import AsyncClient
import uuid

@pytest.mark.asyncio
async def test_cases_list(async_client: AsyncClient, test_db_session, setup_test_data):
    response = await async_client.get("/cases/")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)

@pytest.mark.asyncio
async def test_dashboard_feed(async_client: AsyncClient, test_db_session, setup_test_data):
    response = await async_client.get("/dashboard/feed")
    assert response.status_code == 200
    data = response.json()
    assert "recent_cases" in data
    assert "high_risk_alerts" in data
