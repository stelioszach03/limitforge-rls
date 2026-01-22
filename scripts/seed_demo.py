import asyncio

from app.core.config import settings
from app.db.session import AsyncSessionLocal
from app.db.models import Base, PlanAlgorithm, SubjectType
from app.db import crud


async def main():
    # Ensure tables exist (useful for local dev without running migrations)
    try:
        from sqlalchemy.ext.asyncio import create_async_engine

        engine = create_async_engine(settings.POSTGRES_DSN, future=True)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        await engine.dispose()
    except Exception:
        pass

    async with AsyncSessionLocal() as db:  # type: AsyncSession
        # Tenant
        tenant = await crud.create_tenant(db, name="DemoCo")

        # Plan (token bucket)
        plan = await crud.create_plan(
            db,
            tenant_id=tenant.id,
            name="demo-token-bucket",
            algorithm=PlanAlgorithm.token_bucket,
            bucket_capacity=100,
            refill_rate_per_sec=50.0,
        )

        # API key
        raw_key, key_hash = await crud.create_api_key(
            db, tenant_id=tenant.id, name="demo-key"
        )

        # Policy mapping for resource "orders"
        await crud.create_resource_policy(
            db,
            tenant_id=tenant.id,
            resource="orders",
            subject_type=SubjectType.api_key,
            plan_id=plan.id,
        )

        print("Seed complete:\n- tenant:", str(tenant.id))
        print("- plan:", str(plan.id), plan.algorithm.value)
        print("- api key (save this raw key):", raw_key)
        print("- key_hash:", key_hash)
        print("- policy resource: orders (subject_type=api_key)")


if __name__ == "__main__":
    asyncio.run(main())
