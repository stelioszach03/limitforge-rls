import pytest
from app.rl.strategies import sliding_window as sw


@pytest.mark.asyncio
async def test_sliding_window_allows_then_blocks(fake_redis):
    key = "test:sw"
    # window=1000ms, limit=2
    d1 = await sw.check(fake_redis, key, limit=2, window_sec=1, cost=1, now_ms=0)
    assert d1.allowed
    d2 = await sw.check(fake_redis, key, limit=2, window_sec=1, cost=1, now_ms=10)
    assert d2.allowed
    d3 = await sw.check(fake_redis, key, limit=2, window_sec=1, cost=1, now_ms=20)
    assert not d3.allowed
    assert "X-RateLimit-Remaining" in d3.headers
