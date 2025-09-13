import os
import pytest


@pytest.mark.asyncio
@pytest.mark.parametrize("alg", ["fixed_window", "token_bucket"])
async def test_admin_provisioning_flow(async_client, alg):
    admin = os.getenv("ADMIN_BEARER_TOKEN", "change-me-admin-token")
    headers = {"Authorization": f"Bearer {admin}"}

    r = await async_client.post(
        "/v1/admin/tenants", json={"name": "acme"}, headers=headers
    )
    assert r.status_code == 200
    tenant_id = r.json()["id"]

    plan_payload = {
        "tenant_id": tenant_id,
        "name": "basic",
        "algorithm": alg,
        "limit_per_window": 2,
        "window_seconds": 60,
        "bucket_capacity": 2,
        "refill_rate_per_sec": 1.0,
    }
    r = await async_client.post("/v1/admin/plans", json=plan_payload, headers=headers)
    assert r.status_code == 200
    plan_id = r.json()["id"]

    r = await async_client.post(
        "/v1/admin/keys", json={"tenant_id": tenant_id, "name": "k1"}, headers=headers
    )
    assert r.status_code == 200
    assert "key" in r.json()

    r = await async_client.post(
        "/v1/admin/policies",
        json={
            "tenant_id": tenant_id,
            "resource": "GET:/demo",
            "subject_type": "api_key",
            "plan_id": plan_id,
        },
        headers=headers,
    )
    assert r.status_code == 200

    r = await async_client.get(
        f"/v1/admin/tenants/{tenant_id}/summary", headers=headers
    )
    assert r.status_code == 200
    data = r.json()
    assert data["plans"] >= 1 and data["policies"] >= 1 and data["keys"] >= 1
