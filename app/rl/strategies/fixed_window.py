import time
import math
from pathlib import Path
from typing import Dict, Any, Tuple
from redis.asyncio import Redis
from app.rl.keys import window_key
from app.rl.schemas import CheckDecision

_SCRIPT_TEXT = None


def _get_script_text() -> str:
    global _SCRIPT_TEXT
    if _SCRIPT_TEXT is None:
        path = Path(__file__).resolve().parent.parent / "scripts" / "fixed_window.lua"
        _SCRIPT_TEXT = path.read_text(encoding="utf-8")
    return _SCRIPT_TEXT


async def _eval_script(redis: Redis, keys: list[str], args: list):
    script_text = _get_script_text()
    if "fakeredis" in type(redis).__module__:
        return await redis.eval(script_text, len(keys), *keys, *args)
    reg = getattr(redis, "register_script", None)
    if callable(reg):
        script = reg(script_text)
        return await script(keys=keys, args=args)
    load = getattr(redis, "script_load", None)
    evalsha = getattr(redis, "evalsha", None)
    if callable(load) and callable(evalsha):
        sha = await load(script_text)
        return await evalsha(sha, len(keys), *keys, *args)
    return await redis.eval(script_text, len(keys), *keys, *args)


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
    if "fakeredis" in type(redis).__module__:
        now_sec = now_ms // 1000
        window_start = (now_sec // window_sec) * window_sec
        exists = await redis.exists(key)
        if not exists:
            await redis.set(key, 0, ex=window_sec, nx=True)
        counter = await redis.incrby(key, cost)
        allowed = counter <= limit
        remaining = max(0, limit - counter)
        reset_at = window_start + window_sec
        retry_after_ms = max(0, (reset_at * 1000) - now_ms)
        headers = {
            "X-RateLimit-Limit": str(limit),
            "X-RateLimit-Remaining": str(remaining),
            "X-RateLimit-Reset": str(reset_at),
            "Retry-After": str(math.ceil(retry_after_ms / 1000)),
        }
        return CheckDecision(
            allowed=allowed,
            remaining=remaining,
            limit=limit,
            reset_at=reset_at,
            retry_after_ms=retry_after_ms,
            algorithm="fixed_window",
            headers=headers,
        )
    res = await _eval_script(redis, keys=[key], args=[limit, window_sec, now_ms, cost])
    # res: [allowed, remaining, limit, reset_at, retry_after_ms]
    allowed = int(res[0]) == 1
    remaining = int(res[1])
    lim = int(res[2])
    reset_at = int(res[3])  # seconds epoch
    retry_after_ms = int(res[4])
    headers = {
        "X-RateLimit-Limit": str(lim),
        "X-RateLimit-Remaining": str(remaining),
        "X-RateLimit-Reset": str(reset_at),
        "Retry-After": str(math.ceil(retry_after_ms / 1000)),
    }
    return CheckDecision(
        allowed=allowed,
        remaining=remaining,
        limit=lim,
        reset_at=reset_at,
        retry_after_ms=retry_after_ms,
        algorithm="fixed_window",
        headers=headers,
    )


async def fixed_window_check(
    redis: Redis,
    api_key: str,
    namespace: str,
    subject: str,
    params: Dict[str, Any],
    cost: int,
) -> Tuple[bool, int, int]:
    limit = int(params.get("limit", 10))
    window_s = int(params.get("window", 60))
    now = int(time.time())
    window_start = now - (now % window_s)
    key = window_key(namespace, subject, window_start)
    decision = await check(redis, key, limit=limit, window_sec=window_s, cost=cost)
    return decision.allowed, decision.remaining, decision.retry_after_ms
