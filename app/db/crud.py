from __future__ import annotations

import secrets
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import hash_api_key
from .models import Tenant, Plan, ApiKey, ResourcePolicy, PlanAlgorithm, SubjectType


async def create_tenant(db: AsyncSession, name: str) -> Tenant:
    tenant = Tenant(name=name)
    db.add(tenant)
    await db.commit()
    await db.refresh(tenant)
    return tenant


async def create_plan(
    db: AsyncSession,
    tenant_id,
    *,
    name: str,
    algorithm: PlanAlgorithm,
    limit_per_window: Optional[int] = None,
    window_seconds: Optional[int] = None,
    bucket_capacity: Optional[int] = None,
    refill_rate_per_sec: Optional[float] = None,
    concurrency_limit: Optional[int] = None,
    cost_per_call: int = 1,
    burst_factor: float = 1.0,
) -> Plan:
    plan = Plan(
        tenant_id=tenant_id,
        name=name,
        algorithm=algorithm,
        limit_per_window=limit_per_window,
        window_seconds=window_seconds,
        bucket_capacity=bucket_capacity,
        refill_rate_per_sec=refill_rate_per_sec,
        concurrency_limit=concurrency_limit,
        cost_per_call=cost_per_call,
        burst_factor=burst_factor,
    )
    db.add(plan)
    await db.commit()
    await db.refresh(plan)
    return plan


async def create_api_key(db: AsyncSession, tenant_id, name: str) -> tuple[str, str]:
    raw = secrets.token_urlsafe(32)
    key_hash = hash_api_key(raw, settings.APIKEY_HASH_SALT)
    ak = ApiKey(tenant_id=tenant_id, name=name, key_hash=key_hash, active=True)
    db.add(ak)
    await db.commit()
    return raw, key_hash


async def create_resource_policy(
    db: AsyncSession,
    tenant_id,
    *,
    resource: str,
    subject_type: SubjectType,
    plan_id,
) -> ResourcePolicy:
    rp = ResourcePolicy(
        tenant_id=tenant_id,
        resource=resource,
        subject_type=subject_type,
        plan_id=plan_id,
    )
    db.add(rp)
    await db.commit()
    await db.refresh(rp)
    return rp


async def get_plan_for(
    db: AsyncSession,
    tenant_id,
    resource: str,
    subject_type: SubjectType,
) -> Optional[Plan]:
    q = (
        select(Plan)
        .join(ResourcePolicy, ResourcePolicy.plan_id == Plan.id)
        .where(
            Plan.tenant_id == tenant_id,
            ResourcePolicy.tenant_id == tenant_id,
            ResourcePolicy.resource == resource,
            ResourcePolicy.subject_type == subject_type,
        )
        .order_by(Plan.created_at.desc())
    )
    res = await db.execute(q)
    return res.scalars().first()


async def get_api_key_by_hash(db: AsyncSession, key_hash: str) -> Optional[ApiKey]:
    res = await db.execute(select(ApiKey).where(ApiKey.key_hash == key_hash))
    return res.scalar_one_or_none()


async def get_plan_by_id(db: AsyncSession, plan_id) -> Optional[Plan]:
    res = await db.execute(select(Plan).where(Plan.id == plan_id))
    return res.scalar_one_or_none()
