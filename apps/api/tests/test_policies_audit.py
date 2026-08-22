
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_get_policies(async_client: AsyncClient, test_db_session, setup_test_data):
    response = await async_client.get("/policies/")
    assert response.status_code == 200
    data = response.json()
    assert "max_autonomous_amount_paise" in data

@pytest.mark.asyncio
async def test_audit_list(async_client: AsyncClient, test_db_session, setup_test_data):
    response = await async_client.get("/audit/")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
