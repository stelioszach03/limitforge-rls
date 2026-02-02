import pytest


@pytest.mark.asyncio
async def test_health(async_client):
    r = await async_client.get("/v1/health")
    assert r.status_code == 200
    assert r.json().get("status") == "ok"

