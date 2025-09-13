import pytest

from app.rl.engine import DecisionEngine
from app.db import crud
from app.db.models import PlanAlgorithm, SubjectType


class CrudNoGetById:
    # Provide only what resolve_plan needs in policy path (unused here)
    async def get_plan_for(self, *args, **kwargs):
        return None


@pytest.mark.asyncio
async def test_resolve_plan_explicit_id_fallback_select(db, fake_redis):
    from app.core.config import settings as s

    t = await crud.create_tenant(db, name="Tfallback")
    p = await crud.create_plan(
        db,
        tenant_id=t.id,
        name="Pfb",
        algorithm=PlanAlgorithm.token_bucket,
        bucket_capacity=1,
        refill_rate_per_sec=1.0,
    )
    # Engine with crud module missing get_plan_by_id forces select() branch
    eng = DecisionEngine(redis=fake_redis, settings=s, crud_module=CrudNoGetById())
    plan = await eng.resolve_plan(
        db=db,
        tenant_id=t.id,
        resource="GET:/r",
        subject_type=SubjectType.api_key,
        explicit_plan_id=p.id,
    )
    assert str(plan.id) == str(p.id)
