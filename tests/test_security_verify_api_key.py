import pytest

from app.core.security import verify_api_key
from app.db import crud


@pytest.mark.asyncio
async def test_verify_api_key_db_and_cache(db, fake_redis):
    tenant = await crud.create_tenant(db, name="Tcache")
    raw, h = await crud.create_api_key(db, tenant_id=tenant.id, name="k")
    # First call hits DB and caches
    obj1 = await verify_api_key(db, fake_redis, h)
    assert obj1 is not None and obj1.active
    # Second call should use cache fast path
    obj2 = await verify_api_key(db, fake_redis, h)
    assert obj2 is not None and obj2.active
