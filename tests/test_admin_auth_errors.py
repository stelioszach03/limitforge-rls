import pytest


@pytest.mark.asyncio
async def test_admin_create_tenant_missing_bearer(async_client):
    resp = await async_client.post("/v1/admin/tenants", json={"name": "X"})
    assert resp.status_code == 401
    assert resp.json()["detail"].lower().startswith("missing bearer token".split()[0])


@pytest.mark.asyncio
async def test_admin_create_tenant_invalid_bearer(async_client):
    resp = await async_client.post(
        "/v1/admin/tenants",
        headers={"Authorization": "Bearer wrong"},
        json={"name": "X"},
    )
    assert resp.status_code == 403
    assert resp.json()["detail"].lower().startswith("invalid admin token".split()[0])
