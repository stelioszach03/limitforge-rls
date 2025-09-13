from __future__ import annotations

from prometheus_client import Counter, Histogram, Gauge

# Legacy counters (kept for compatibility)
RL_ALLOWED = Counter("rl_allowed_total", "Allowed rate limit decisions")
RL_BLOCKED = Counter("rl_blocked_total", "Blocked rate limit decisions")

# New metrics
REQUESTS_TOTAL = Counter(
    "requests_total",
    "Total requests",
    labelnames=("route", "outcome"),
)

DECISION_LATENCY_MS = Histogram(
    "decision_latency_ms",
    "Decision latency in milliseconds",
)

REDIS_POOL_IN_USE = Gauge(
    "redis_pool_in_use",
    "Approximate number of Redis pool connections in use",
)


def update_redis_pool_gauge(redis_client) -> None:
    try:
        pool = getattr(redis_client, "connection_pool", None)
        if pool is None:
            return
        in_use = 0
        # Best-effort across redis-py versions
        if hasattr(pool, "_in_use_connections"):
            in_use = len(pool._in_use_connections)  # type: ignore[attr-defined]
        elif hasattr(pool, "_created_connections") and hasattr(
            pool, "_available_connections"
        ):
            created = len(pool._created_connections)  # type: ignore[attr-defined]
            available = len(pool._available_connections)  # type: ignore[attr-defined]
            in_use = max(created - available, 0)
        REDIS_POOL_IN_USE.set(in_use)
    except Exception:
        # Optional metric; ignore failures
        pass
