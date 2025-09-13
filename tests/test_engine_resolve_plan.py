import pytest
from app.rl.engine import DecisionEngine
from app.db import crud
from app.db.models import PlanAlgorithm, SubjectType


@pytest.mark.asyncio
async def test_resolve_plan_explicit_id(db, fake_redis):
    from app.core.config import settings as s

    t = await crud.create_tenant(db, name="T1")
    p = await crud.create_plan(db, tenant_id=t.id, name="P", algorithm=PlanAlgorithm.token_bucket, bucket_capacity=1, refill_rate_per_sec=1.0)
    eng = DecisionEngine(redis=fake_redis, settings=s, crud_module=crud)
    plan = await eng.resolve_plan(db=db, tenant_id=t.id, resource="GET:/r", subject_type=SubjectType.api_key, explicit_plan_id=p.id)
    assert str(plan.id) == str(p.id)


@pytest.mark.asyncio
async def test_resolve_plan_policy_path(db, fake_redis):
    from app.core.config import settings as s

    t = await crud.create_tenant(db, name="T2")
    p = await crud.create_plan(db, tenant_id=t.id, name="P2", algorithm=PlanAlgorithm.fixed_window, limit_per_window=1, window_seconds=60)
    await crud.create_resource_policy(db, tenant_id=t.id, resource="GET:/r2", subject_type=SubjectType.api_key, plan_id=p.id)
    eng = DecisionEngine(redis=fake_redis, settings=s, crud_module=crud)
    plan = await eng.resolve_plan(db=db, tenant_id=t.id, resource="GET:/r2", subject_type=SubjectType.api_key)
    assert str(plan.id) == str(p.id)


@pytest.mark.asyncio
async def test_resolve_plan_not_found_raises(db, fake_redis):
    from app.core.config import settings as s

    t = await crud.create_tenant(db, name="T3")
    eng = DecisionEngine(redis=fake_redis, settings=s, crud_module=crud)
    with pytest.raises(LookupError):
        await eng.resolve_plan(db=db, tenant_id=t.id, resource="GET:/none", subject_type=SubjectType.api_key)

