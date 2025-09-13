import pytest
from fakeredis.aioredis import FakeRedis

from app.rl.strategies import token_bucket, fixed_window


@pytest.mark.asyncio
async def test_token_bucket_wrapper():
    r = FakeRedis(decode_responses=True)
    allowed, remaining, retry_ms = await token_bucket.token_bucket_check(
        r,
        api_key="k",
        namespace="ns",
        subject="sub",
        params={"capacity": 2, "refill_rate": 0},
        cost=1,
    )
    assert allowed and remaining == 1 and retry_ms == 0


@pytest.mark.asyncio
async def test_fixed_window_wrapper():
    r = FakeRedis(decode_responses=True)
    allowed, remaining, retry_ms = await fixed_window.fixed_window_check(
        r,
        api_key="k",
        namespace="ns",
        subject="sub",
        params={"limit": 1, "window": 60},
        cost=1,
    )
    assert allowed and remaining == 0 and retry_ms >= 0


@pytest.mark.asyncio
async def test_concurrency_wrapper():
    from app.rl.strategies.concurrency import concurrency_check

    r = FakeRedis(decode_responses=True)
    ok, rem, retry = await concurrency_check(
        r, api_key="k", namespace="ns", subject="s", params={"limit": 1, "ttl": 1}, cost=1
    )
    assert ok and rem == 0 and retry == 0


@pytest.mark.asyncio
async def test_sliding_window_wrapper():
    from app.rl.strategies.sliding_window import sliding_window_check

    r = FakeRedis(decode_responses=True)
    ok, rem, retry = await sliding_window_check(
        r, api_key="k", namespace="ns", subject="s", params={"limit": 2, "window": 1}, cost=1
    )
    assert ok and rem == 1 and retry >= 0
