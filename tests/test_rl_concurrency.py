import pytest
from app.rl.strategies import concurrency as cc


@pytest.mark.asyncio
async def test_concurrency_acquire_release(fake_redis):
    key = "test:cc"
    # limit 2
    d1 = await cc.acquire(fake_redis, key, limit=2, ttl_sec=1, cost=1)
    d2 = await cc.acquire(fake_redis, key, limit=2, ttl_sec=1, cost=1)
    d3 = await cc.acquire(fake_redis, key, limit=2, ttl_sec=1, cost=1)
    assert d1.allowed and d2.allowed and not d3.allowed
    # release 1 and try again
    await cc.release(fake_redis, key, cost=1)
    d4 = await cc.acquire(fake_redis, key, limit=2, ttl_sec=1, cost=1)
    assert d4.allowed
