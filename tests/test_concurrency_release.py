import pytest
from fakeredis.aioredis import FakeRedis

from app.rl.strategies.concurrency import release


@pytest.mark.asyncio
async def test_concurrency_release_non_negative():
    r = FakeRedis(decode_responses=True)
    await r.set("k", 2)
    val = await release(r, "k", cost=1)
    assert val == 1


@pytest.mark.asyncio
async def test_concurrency_release_negative_resets():
    r = FakeRedis(decode_responses=True)
    await r.set("k", 0)
    val = await release(r, "k", cost=2)
    assert val == 0
    assert await r.get("k") is None
