import time
import math
from typing import Dict, Any, Tuple
from redis.asyncio import Redis
from app.rl.keys import bucket_key
from app.rl.schemas import CheckDecision


async def check(
    redis: Redis,
    key: str,
    *,
    limit: int,
    window_sec: int,
    cost: int = 1,
    now_ms: int | None = None,
) -> CheckDecision:
    if now_ms is None:
        now_ms = int(time.time() * 1000)
    min_score = now_ms - window_sec * 1000

    await redis.zremrangebyscore(key, 0, min_score)
    count = await redis.zcard(key)
    allowed = (count + cost) <= limit

    retry_after_ms = 0
    earliest_ms = None
    if not allowed:
        first = await redis.zrange(key, 0, 0, withscores=True)
        if first:
            earliest_ms = int(first[0][1])
            retry_after_ms = max(0, (earliest_ms + window_sec * 1000) - now_ms)

    if allowed:
        pipe = redis.pipeline()
        for i in range(cost):
            score = now_ms + i
            pipe.zadd(key, {f"evt:{score}": score})
        pipe.pexpire(key, window_sec * 1000 + 1000)
        await pipe.execute()

    used = count + (cost if allowed else 0)
    remaining = max(0, limit - used)
    # reset_at based on earliest event in the window after mutation
    if earliest_ms is None:
        # fetch earliest after write
        first_after = await redis.zrange(key, 0, 0, withscores=True)
        if first_after:
            earliest_ms = int(first_after[0][1])
    reset_at_s = math.ceil(((earliest_ms or now_ms) + window_sec * 1000) / 1000)

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
        algorithm="sliding_window",
        headers=headers,
    )


async def sliding_window_check(
    redis: Redis,
    api_key: str,
    namespace: str,
    subject: str,
    params: Dict[str, Any],
    cost: int,
) -> Tuple[bool, int, int]:
    limit = int(params.get("limit", 10))
    window_s = int(params.get("window", 60))
    name = params.get("name", "default")
    key = bucket_key(namespace, subject, f"sw:{name}")
    decision = await check(redis, key, limit=limit, window_sec=window_s, cost=cost)
    return decision.allowed, decision.remaining, decision.retry_after_ms
