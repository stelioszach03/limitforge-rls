import pytest
from app.rl.strategies import fixed_window as fw


@pytest.mark.asyncio
async def test_fixed_window_counts_and_retry(fake_redis):
    key = "test:fw"
    # window 1s, limit 2
    d1 = await fw.check(fake_redis, key, limit=2, window_sec=1, cost=1, now_ms=0)
    assert d1.allowed and d1.remaining == 1
    d2 = await fw.check(fake_redis, key, limit=2, window_sec=1, cost=1, now_ms=10)
    assert d2.allowed and d2.remaining == 0
    d3 = await fw.check(fake_redis, key, limit=2, window_sec=1, cost=1, now_ms=20)
    assert not d3.allowed and d3.retry_after_ms >= 0
    assert "X-RateLimit-Limit" in d3.headers
