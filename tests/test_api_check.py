import pytest
from app.db import crud
from app.db.models import PlanAlgorithm, SubjectType


@pytest.mark.asyncio
async def test_api_check_allows_then_429(async_client, db, fake_redis):
    # Seed tenant, plan, policy, and api key
    tenant = await crud.create_tenant(db, name="acme")
    plan = await crud.create_plan(
        db,
        tenant_id=tenant.id,
        name="basic",
        algorithm=PlanAlgorithm.fixed_window,
        limit_per_window=2,
        window_seconds=60,
    )
    await crud.create_resource_policy(
        db,
        tenant_id=tenant.id,
        resource="GET:/demo",
        subject_type=SubjectType.api_key,
        plan_id=plan.id,
    )
    raw_key, _ = await crud.create_api_key(db, tenant_id=tenant.id, name="k1")

    # First two allowed
    for i in range(2):
        r = await async_client.post(
            "/v1/check",
            json={"resource": "GET:/demo", "subject": "user:1", "cost": 1},
            headers={"X-API-Key": raw_key},
        )
        assert r.status_code == 200, r.text
        assert r.json()["allowed"] is True
        assert "X-RateLimit-Limit" in r.headers

    # Third should be 429
    r3 = await async_client.post(
        "/v1/check",
        json={"resource": "GET:/demo", "subject": "user:1", "cost": 1},
        headers={"X-API-Key": raw_key},
    )
    assert r3.status_code == 429
    body = r3.json()
    assert body["allowed"] is False
    assert "Retry-After" in r3.headers
