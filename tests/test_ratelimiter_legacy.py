import pytest
from fakeredis.aioredis import FakeRedis

from app.rl.engine import RateLimiter


@pytest.mark.asyncio
async def test_ratelimiter_token_bucket_and_fixed_window():
    r = FakeRedis(decode_responses=True)
    rl = RateLimiter(redis=r)

    # Token bucket allow then block
    ok, rem, _ = await rl.check(
        api_key="k",
        namespace="ns",
        subject="s",
        strategy="token_bucket",
        params={"capacity": 1, "refill_rate": 0},
        cost=1,
    )
    assert ok and rem == 0
    ok2, rem2, _ = await rl.check(
        api_key="k",
        namespace="ns",
        subject="s",
        strategy="token_bucket",
        params={"capacity": 1, "refill_rate": 0},
        cost=1,
    )
    assert not ok2 and rem2 == 0

    # Fixed window allow then block
    ok3, rem3, _ = await rl.check(
        api_key="k2",
        namespace="ns",
        subject="s",
        strategy="fixed_window",
        params={"limit": 1, "window": 60},
        cost=1,
    )
    assert ok3 and rem3 == 0
    ok4, rem4, _ = await rl.check(
        api_key="k2",
        namespace="ns",
        subject="s",
        strategy="fixed_window",
        params={"limit": 1, "window": 60},
        cost=1,
    )
    assert not ok4 and rem4 == 0
