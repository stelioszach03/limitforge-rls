import pytest


@pytest.mark.asyncio
async def test_check_missing_api_key(async_client):
    resp = await async_client.post("/v1/check", json={"resource": "GET:/x", "subject": "u:1", "cost": 1})
    assert resp.status_code == 401
    body = resp.json()
    assert body["detail"].lower().startswith("missing x-api-key".split()[0])


@pytest.mark.asyncio
async def test_check_invalid_api_key(async_client):
    resp = await async_client.post(
        "/v1/check",
        headers={"X-API-Key": "not-a-real-key"},
        json={"resource": "GET:/x", "subject": "u:1", "cost": 1},
    )
    assert resp.status_code == 403
    body = resp.json()
    assert body["detail"].lower().startswith("invalid api key".split()[0])

