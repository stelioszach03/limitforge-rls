from __future__ import annotations

import time
from typing import Any, Dict, Tuple, Optional, Callable

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings as global_settings
from app.db.models import Plan, PlanAlgorithm, SubjectType
from app.rl.schemas import CheckDecision
from app.rl.keys import (
    rl_key_token_bucket,
    rl_key_fixed_window,
    rl_key_sliding,
    rl_key_conc,
)
from app.rl.strategies import token_bucket, fixed_window, sliding_window, concurrency
from app.observability.metrics import (
    DECISION_LATENCY_MS,
    REQUESTS_TOTAL,
    update_redis_pool_gauge,
)


class RateLimiter:
    def __init__(self, redis: Redis):
        self.redis = redis

    async def check(
        self,
        api_key: str,
        namespace: str,
        subject: str,
        strategy: str | None,
        params: Dict[str, Any],
        cost: int = 1,
    ) -> Tuple[bool, int, int]:
        strat = (strategy or global_settings.DEFAULT_STRATEGY).lower()
        if strat == "token_bucket":
            return await token_bucket.token_bucket_check(
                self.redis, api_key, namespace, subject, params, cost
            )
        if strat == "fixed_window":
            return await fixed_window.fixed_window_check(
                self.redis, api_key, namespace, subject, params, cost
            )
        if strat == "sliding_window":
            return await sliding_window.sliding_window_check(
                self.redis, api_key, namespace, subject, params, cost
            )
        if strat == "concurrency":
            return await concurrency.concurrency_check(
                self.redis, api_key, namespace, subject, params, cost
            )
        return await token_bucket.token_bucket_check(
            self.redis, api_key, namespace, subject, params, cost
        )


class DecisionEngine:
    def __init__(self, redis: Redis, settings, crud_module):
        self.redis = redis
        self.settings = settings
        self.crud = crud_module
        self._map: dict[str, Callable[..., CheckDecision]] = {
            "token_bucket": lambda redis, key, *, capacity, refill_rate_per_sec, cost=1: token_bucket.check(
                redis,
                key,
                capacity=capacity,
                refill_rate_per_sec=refill_rate_per_sec,
                cost=cost,
            ),
            "fixed_window": lambda redis, key, *, limit, window_sec, cost=1: fixed_window.check(
                redis, key, limit=limit, window_sec=window_sec, cost=cost
            ),
            "sliding_window": lambda redis, key, *, limit, window_sec, cost=1: sliding_window.check(
                redis, key, limit=limit, window_sec=window_sec, cost=cost
            ),
            "concurrency": lambda redis, key, *, limit, ttl_sec, cost=1: concurrency.acquire(
                redis, key, limit=limit, ttl_sec=ttl_sec, cost=cost
            ),
        }

    async def resolve_plan(
        self,
        db: AsyncSession,
        tenant_id,
        resource: str,
        subject_type: SubjectType | str,
        explicit_plan_id=None,
    ) -> Plan:
        if explicit_plan_id is not None:
            # require crud helper, fallback to direct select if not present
            if hasattr(self.crud, "get_plan_by_id"):
                plan = await self.crud.get_plan_by_id(db, explicit_plan_id)
            else:
                from sqlalchemy import select
                from app.db.models import Plan as PlanModel

                res = await db.execute(
                    select(PlanModel).where(PlanModel.id == explicit_plan_id)
                )
                plan = res.scalar_one_or_none()
        else:
            # normalize subject type
            st = (
                subject_type.value
                if isinstance(subject_type, SubjectType)
                else str(subject_type)
            )
            plan = await self.crud.get_plan_for(
                db, tenant_id, resource, SubjectType(st)
            )

        if not plan:
            raise LookupError("plan_not_found")
        return plan

    def build_key(
        self,
        *,
        tenant_id: str | bytes | Any,
        subject: str,
        resource: str,
        algorithm: str,
        plan: Optional[Plan] = None,
        now_ms: Optional[int] = None,
    ) -> str:
        alg = algorithm if isinstance(algorithm, str) else str(algorithm)
        tid = str(tenant_id)
        if alg == "token_bucket":
            return rl_key_token_bucket(tid, subject, resource)
        if alg == "fixed_window":
            if now_ms is None:
                now_ms = int(time.time() * 1000)
            window_sec = plan.window_seconds if plan and plan.window_seconds else 60  # type: ignore[attr-defined]
            window_start = (now_ms // 1000 // window_sec) * window_sec
            return rl_key_fixed_window(tid, subject, resource, int(window_start))
        if alg == "sliding_window":
            return rl_key_sliding(tid, subject, resource)
        if alg == "concurrency":
            return rl_key_conc(tid, subject, resource)
        return rl_key_token_bucket(tid, subject, resource)

    async def check(
        self,
        *,
        tenant_id,
        subject: str,
        resource: str,
        cost: int,
        plan: Plan,
    ) -> CheckDecision:
        alg = (
            plan.algorithm.value
            if isinstance(plan.algorithm, PlanAlgorithm)
            else str(plan.algorithm)
        )
        key = self.build_key(
            tenant_id=str(tenant_id),
            subject=subject,
            resource=resource,
            algorithm=alg,
            plan=plan,
        )
        start = time.perf_counter()
        try:
            if alg == "token_bucket":
                capacity = plan.bucket_capacity or (plan.limit_per_window or 0)
                refill = plan.refill_rate_per_sec or 0.0
                decision = await self._map[alg](
                    self.redis,
                    key,
                    capacity=int(capacity),
                    refill_rate_per_sec=float(refill),
                    cost=int(cost),
                )
            elif alg == "fixed_window":
                limit = plan.limit_per_window or (plan.bucket_capacity or 0)
                window_sec = plan.window_seconds or 60
                decision = await self._map[alg](
                    self.redis,
                    key,
                    limit=int(limit),
                    window_sec=int(window_sec),
                    cost=int(cost),
                )
            elif alg == "sliding_window":
                limit = plan.limit_per_window or (plan.bucket_capacity or 0)
                window_sec = plan.window_seconds or 60
                decision = await self._map[alg](
                    self.redis,
                    key,
                    limit=int(limit),
                    window_sec=int(window_sec),
                    cost=int(cost),
                )
            elif alg == "concurrency":
                limit = plan.concurrency_limit or 1
                ttl_sec = plan.window_seconds or 60
                decision = await self._map[alg](
                    self.redis,
                    key,
                    limit=int(limit),
                    ttl_sec=int(ttl_sec),
                    cost=int(cost),
                )
            else:
                capacity = plan.bucket_capacity or (plan.limit_per_window or 0)
                refill = plan.refill_rate_per_sec or 0.0
                decision = await self._map["token_bucket"](
                    self.redis,
                    key,
                    capacity=int(capacity),
                    refill_rate_per_sec=float(refill),
                    cost=int(cost),
                )
            return decision
        finally:
            dur_ms = (time.perf_counter() - start) * 1000.0
            DECISION_LATENCY_MS.observe(dur_ms)
            (
                REQUESTS_TOTAL.labels(route="engine.check", outcome="allowed").inc()
                if "decision" in locals() and decision.allowed
                else REQUESTS_TOTAL.labels(
                    route="engine.check", outcome="blocked"
                ).inc()
            )
            update_redis_pool_gauge(self.redis)

    @staticmethod
    def headers(decision: CheckDecision) -> dict[str, str]:
        return decision.headers
