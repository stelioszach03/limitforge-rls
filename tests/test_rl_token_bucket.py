import pytest
from app.rl.strategies import token_bucket as tb


@pytest.mark.asyncio
async def test_token_bucket_refill_and_retry_after(fake_redis):
    key = "test:tb"
    # Drain bucket at t=0
    dec = await tb.check(
        fake_redis, key, capacity=5, refill_rate_per_sec=2.0, cost=5, now_ms=0
    )
    assert dec.allowed and dec.remaining == 0

    # Too soon: at 100ms, not enough tokens for cost=1
    dec2 = await tb.check(
        fake_redis, key, capacity=5, refill_rate_per_sec=2.0, cost=1, now_ms=100
    )
    assert not dec2.allowed
    # ~0.4s to wait; allow generous bounds due to rounding
    assert 200 <= dec2.retry_after_ms <= 600

    # After 1000ms, ~2 tokens available; cost=1 allowed
    dec3 = await tb.check(
        fake_redis, key, capacity=5, refill_rate_per_sec=2.0, cost=1, now_ms=1000
    )
    assert dec3.allowed and dec3.remaining >= 0

    # Long time later, tokens should clamp to capacity
    dec4 = await tb.check(
        fake_redis, key, capacity=5, refill_rate_per_sec=2.0, cost=0, now_ms=10000
    )
    assert dec4.remaining == 5
