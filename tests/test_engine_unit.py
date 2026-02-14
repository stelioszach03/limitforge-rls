import types
import pytest

from app.rl.engine import DecisionEngine
from app.db import crud


def _fake_plan(algorithm: str, **kwargs):
    # Minimal object with attributes accessed by engine.check/build_key
    obj = types.SimpleNamespace()
    obj.algorithm = algorithm
    # Common fields with sensible defaults
    obj.bucket_capacity = kwargs.get("bucket_capacity")
    obj.refill_rate_per_sec = kwargs.get("refill_rate_per_sec")
    obj.limit_per_window = kwargs.get("limit_per_window")
    obj.window_seconds = kwargs.get("window_seconds")
    obj.concurrency_limit = kwargs.get("concurrency_limit")
    return obj


@pytest.mark.asyncio
async def test_build_key_variants(fake_redis):
    from app.core.config import settings as s

    eng = DecisionEngine(redis=fake_redis, settings=s, crud_module=crud)
    tid = "t1"
    k_tb = eng.build_key(
        tenant_id=tid, subject="u:1", resource="GET:/r", algorithm="token_bucket"
    )
    k_fw = eng.build_key(
        tenant_id=tid,
        subject="u:1",
        resource="GET:/r",
        algorithm="fixed_window",
        plan=_fake_plan("fixed_window", window_seconds=60),
        now_ms=1700000000000,
    )
    k_sw = eng.build_key(
        tenant_id=tid, subject="u:1", resource="GET:/r", algorithm="sliding_window"
    )
    k_cc = eng.build_key(
        tenant_id=tid, subject="u:1", resource="GET:/r", algorithm="concurrency"
    )

    assert k_tb.startswith("lf:tb:")
    assert ":win:" not in k_fw and k_fw.startswith("lf:fw:")
    assert k_sw.startswith("lf:sw:")
    assert k_cc.startswith("lf:cc:")


@pytest.mark.asyncio
async def test_engine_check_token_bucket_allows_then_blocks(fake_redis):
    from app.core.config import settings as s

    eng = DecisionEngine(redis=fake_redis, settings=s, crud_module=crud)
    plan = _fake_plan("token_bucket", bucket_capacity=2, refill_rate_per_sec=0.0)
    # First two allowed
    d1 = await eng.check(
        tenant_id="t1", subject="u:1", resource="GET:/x", cost=1, plan=plan
    )
    d2 = await eng.check(
        tenant_id="t1", subject="u:1", resource="GET:/x", cost=1, plan=plan
    )
    # Third blocks
    d3 = await eng.check(
        tenant_id="t1", subject="u:1", resource="GET:/x", cost=1, plan=plan
    )
    assert d1.allowed and d2.allowed and not d3.allowed


@pytest.mark.asyncio
async def test_engine_check_fixed_window(fake_redis):
    from app.core.config import settings as s

    eng = DecisionEngine(redis=fake_redis, settings=s, crud_module=crud)
    plan = _fake_plan("fixed_window", limit_per_window=1, window_seconds=60)
    d1 = await eng.check(
        tenant_id="t1", subject="u:1", resource="GET:/y", cost=1, plan=plan
    )
    d2 = await eng.check(
        tenant_id="t1", subject="u:1", resource="GET:/y", cost=1, plan=plan
    )
    assert d1.allowed and not d2.allowed


@pytest.mark.asyncio
async def test_engine_check_concurrency(fake_redis):
    from app.core.config import settings as s

    eng = DecisionEngine(redis=fake_redis, settings=s, crud_module=crud)
    plan = _fake_plan("concurrency", concurrency_limit=1, window_seconds=1)
    d1 = await eng.check(
        tenant_id="t1", subject="u:1", resource="GET:/c", cost=1, plan=plan
    )
    d2 = await eng.check(
        tenant_id="t1", subject="u:1", resource="GET:/c", cost=1, plan=plan
    )
    assert d1.allowed and not d2.allowed
