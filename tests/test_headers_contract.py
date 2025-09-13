import pytest
from app.db import crud
from app.db.models import PlanAlgorithm, SubjectType


@pytest.mark.asyncio
async def test_headers_present_on_decision(async_client, db, fake_redis):
    tenant = await crud.create_tenant(db, name="hdrs")
    plan = await crud.create_plan(
        db,
        tenant_id=tenant.id,
        name="hdr-plan",
        algorithm=PlanAlgorithm.fixed_window,
        limit_per_window=1,
        window_seconds=60,
    )
    await crud.create_resource_policy(
        db,
        tenant_id=tenant.id,
        resource="GET:/h",
        subject_type=SubjectType.api_key,
        plan_id=plan.id,
    )
    raw_key, _ = await crud.create_api_key(db, tenant_id=tenant.id, name="k1")

    r1 = await async_client.post(
        "/v1/check",
        json={"resource": "GET:/h", "subject": "u", "cost": 1},
        headers={"X-API-Key": raw_key},
    )
    assert r1.status_code == 200
    for h in ["X-RateLimit-Limit", "X-RateLimit-Remaining", "X-RateLimit-Reset"]:
        assert h in r1.headers
    r2 = await async_client.post(
        "/v1/check",
        json={"resource": "GET:/h", "subject": "u", "cost": 1},
        headers={"X-API-Key": raw_key},
    )
    assert r2.status_code == 429
    assert "Retry-After" in r2.headers
