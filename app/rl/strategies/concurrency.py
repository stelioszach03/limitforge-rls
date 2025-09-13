import time
from typing import Dict, Any, Tuple
from redis.asyncio import Redis
from app.rl.keys import concurrency_key
from app.rl.schemas import CheckDecision


async def acquire(
    redis: Redis,
    key: str,
    *,
    limit: int,
    ttl_sec: int = 60,
    cost: int = 1,
) -> CheckDecision:
    now_s = int(time.time())
    current = await redis.incrby(key, cost)
    # ensure TTL exists
    ttl = await redis.ttl(key)
    if ttl is None or ttl < 0:
        await redis.expire(key, ttl_sec)
        ttl = ttl_sec

    if current <= limit:
        remaining = max(0, limit - current)
        reset_at = now_s + (ttl if ttl and ttl > 0 else ttl_sec)
        headers = {
            "X-RateLimit-Limit": str(limit),
            "X-RateLimit-Remaining": str(remaining),
            "X-RateLimit-Reset": str(reset_at),
            "Retry-After": "0",
        }
        return CheckDecision(
            allowed=True,
            remaining=remaining,
            limit=limit,
            reset_at=reset_at,
            retry_after_ms=0,
            algorithm="concurrency",
            headers=headers,
        )

    # rollback if over limit
    await redis.decrby(key, cost)
    ttl = await redis.ttl(key)
    ttl = ttl if ttl and ttl > 0 else 0
    headers = {
        "X-RateLimit-Limit": str(limit),
        "X-RateLimit-Remaining": "0",
        "X-RateLimit-Reset": str(now_s + ttl),
        "Retry-After": str(ttl),
    }
    return CheckDecision(
        allowed=False,
        remaining=0,
        limit=limit,
        reset_at=now_s + ttl,
        retry_after_ms=ttl * 1000,
        algorithm="concurrency",
        headers=headers,
    )


async def release(redis: Redis, key: str, *, cost: int = 1) -> int:
    # prevent negative values
    new_val = await redis.decrby(key, cost)
    if new_val < 0:
        await redis.delete(key)
        return 0
    return new_val


async def concurrency_check(
    redis: Redis,
    api_key: str,
    namespace: str,
    subject: str,
    params: Dict[str, Any],
    cost: int,
) -> Tuple[bool, int, int]:
    limit = int(params.get("limit", 5))
    ttl = int(params.get("ttl", 60))
    key = concurrency_key(namespace, subject)
    decision = await acquire(redis, key, limit=limit, ttl_sec=ttl, cost=cost)
    return decision.allowed, decision.remaining, decision.retry_after_ms
