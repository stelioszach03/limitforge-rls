import time
import math
from pathlib import Path
from typing import Dict, Any, Tuple
from redis.asyncio import Redis
from app.rl.keys import bucket_key
from app.rl.schemas import CheckDecision

_SCRIPT = None
_SCRIPT_TEXT = None


def _get_script_text() -> str:
    global _SCRIPT_TEXT
    if _SCRIPT_TEXT is None:
        path = Path(__file__).resolve().parent.parent / "scripts" / "token_bucket.lua"
        _SCRIPT_TEXT = path.read_text(encoding="utf-8")
    return _SCRIPT_TEXT


async def _eval_script(redis: Redis, keys: list[str], args: list):
    script_text = _get_script_text()
    # Special-case fakeredis which often lacks evalsha/register_script
    if "fakeredis" in type(redis).__module__:
        return await redis.eval(script_text, len(keys), *keys, *args)
    # Prefer register_script if available
    reg = getattr(redis, "register_script", None)
    if callable(reg):
        script = reg(script_text)
        return await script(keys=keys, args=args)
    # Fallback to evalsha if supported
    load = getattr(redis, "script_load", None)
    evalsha = getattr(redis, "evalsha", None)
    if callable(load) and callable(evalsha):
        sha = await load(script_text)
        return await evalsha(sha, len(keys), *keys, *args)
    # Last resort: EVAL every time
    return await redis.eval(script_text, len(keys), *keys, *args)


async def check(
    redis: Redis,
    key: str,
    *,
    capacity: int,
    refill_rate_per_sec: float,
    cost: int = 1,
    now_ms: int | None = None,
) -> CheckDecision:
    if now_ms is None:
        now_ms = int(time.time() * 1000)
    # Fallback pure-Python path for fakeredis (no Lua support)
    if "fakeredis" in type(redis).__module__:
        data = await redis.hgetall(key)
        tokens = float(data.get("tokens", capacity) if data else capacity)
        ts = int(data.get("ts", now_ms) if data else now_ms)
        elapsed_ms = max(0, now_ms - ts)
        tokens = min(capacity, tokens + (elapsed_ms / 1000.0) * refill_rate_per_sec)
        allowed = tokens >= cost
        if allowed:
            tokens -= cost
        retry_after_ms = 0
        if not allowed and refill_rate_per_sec > 0:
            missing = max(0.0, cost - tokens)
            retry_after_ms = int((missing / refill_rate_per_sec) * 1000.0 + 0.5)
        await redis.hset(key, mapping={"tokens": tokens, "ts": now_ms})
        ttl_sec = (
            int((capacity / refill_rate_per_sec) + 5)
            if refill_rate_per_sec > 0
            else 3600
        )
        await redis.expire(key, ttl_sec)
        limit = int(capacity)
        remaining = int(tokens)
        reset_at_s = math.ceil((now_ms + retry_after_ms) / 1000)
        headers = {
            "X-RateLimit-Limit": str(limit),
            "X-RateLimit-Remaining": str(remaining),
            "X-RateLimit-Reset": str(reset_at_s),
            "Retry-After": str(math.ceil(retry_after_ms / 1000)),
        }
        return CheckDecision(
            allowed=allowed,
            remaining=remaining,
            limit=limit,
            reset_at=reset_at_s,
            retry_after_ms=retry_after_ms,
            algorithm="token_bucket",
            headers=headers,
        )

    res = await _eval_script(
        redis, keys=[key], args=[capacity, refill_rate_per_sec, now_ms, cost]
    )
    # res: [allowed, remaining, capacity, retry_after_ms]
    allowed = int(res[0]) == 1
    remaining = int(res[1])
    limit = int(res[2])
    retry_after_ms = int(res[3])
    reset_at_s = math.ceil((now_ms + retry_after_ms) / 1000)
    headers = {
        "X-RateLimit-Limit": str(limit),
        "X-RateLimit-Remaining": str(remaining),
        "X-RateLimit-Reset": str(reset_at_s),
        "Retry-After": str(math.ceil(retry_after_ms / 1000)),
    }
    return CheckDecision(
        allowed=allowed,
        remaining=remaining,
        limit=limit,
        reset_at=reset_at_s,
        retry_after_ms=retry_after_ms,
        algorithm="token_bucket",
        headers=headers,
    )


# Backward compatible wrapper used by current engine
async def token_bucket_check(
    redis: Redis,
    api_key: str,
    namespace: str,
    subject: str,
    params: Dict[str, Any],
    cost: int,
) -> Tuple[bool, int, int]:
    capacity = int(params.get("capacity", 10))
    refill_rate = float(params.get("refill_rate", 5))
    name = params.get("name", "default")
    key = bucket_key(namespace, subject, f"tb:{name}")
    decision = await check(
        redis,
        key,
        capacity=capacity,
        refill_rate_per_sec=refill_rate,
        cost=cost,
    )
    return decision.allowed, decision.remaining, decision.retry_after_ms
