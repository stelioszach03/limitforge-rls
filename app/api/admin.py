from __future__ import annotations

import uuid
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.deps import get_db, require_admin
from app.core.logging import get_logger
from app.db import crud
from app.db.models import (
    Plan,
    ApiKey,
    ResourcePolicy,
    PlanAlgorithm,
    SubjectType,
)
from app.rl.schemas import TenantCreate, PlanCreate, ApiKeyCreate, ResourcePolicyCreate


router = APIRouter(prefix="/v1/admin")
log = get_logger("api.admin")


@router.post("/tenants")
async def create_tenant(
    payload: TenantCreate,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(require_admin),
):
    t = await crud.create_tenant(db, payload.name)
    log.bind(tenant=str(t.id)).info("admin.create_tenant")
    return {"id": str(t.id), "name": t.name, "created_at": str(t.created_at)}


@router.post("/plans")
async def create_plan(
    payload: PlanCreate,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(require_admin),
):
    alg = PlanAlgorithm(payload.algorithm)
    p = await crud.create_plan(
        db,
        tenant_id=payload.tenant_id,
        name=payload.name,
        algorithm=alg,
        limit_per_window=payload.limit_per_window,
        window_seconds=payload.window_seconds,
        bucket_capacity=payload.bucket_capacity,
        refill_rate_per_sec=payload.refill_rate_per_sec,
        concurrency_limit=payload.concurrency_limit,
        cost_per_call=payload.cost_per_call,
        burst_factor=payload.burst_factor,
    )
    log.bind(plan=str(p.id), tenant=str(p.tenant_id), alg=p.algorithm.value).info(
        "admin.create_plan"
    )
    return {
        "id": str(p.id),
        "tenant_id": str(p.tenant_id),
        "name": p.name,
        "algorithm": p.algorithm.value,
        "created_at": str(p.created_at),
    }


@router.post("/keys")
async def create_key(
    payload: ApiKeyCreate,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(require_admin),
):
    raw, key_hash = await crud.create_api_key(
        db, tenant_id=payload.tenant_id, name=payload.name
    )
    log.bind(tenant=str(payload.tenant_id)).info("admin.create_key")
    return {"key": raw, "key_hash": key_hash}


@router.post("/policies")
async def create_policy(
    payload: ResourcePolicyCreate,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(require_admin),
):
    st = SubjectType(payload.subject_type)
    rp = await crud.create_resource_policy(
        db,
        tenant_id=payload.tenant_id,
        resource=payload.resource,
        subject_type=st,
        plan_id=payload.plan_id,
    )
    log.bind(policy=str(rp.id), tenant=str(rp.tenant_id)).info("admin.create_policy")
    return {
        "id": str(rp.id),
        "tenant_id": str(rp.tenant_id),
        "resource": rp.resource,
        "subject_type": rp.subject_type.value,
        "plan_id": str(rp.plan_id),
    }


@router.get("/tenants/{tenant_id}/summary")
async def tenant_summary(
    tenant_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(require_admin),
):
    plans_count = (
        await db.execute(
            select(func.count()).select_from(Plan).where(Plan.tenant_id == tenant_id)
        )
    ).scalar()
    keys_count = (
        await db.execute(
            select(func.count())
            .select_from(ApiKey)
            .where(ApiKey.tenant_id == tenant_id)
        )
    ).scalar()
    policies_count = (
        await db.execute(
            select(func.count())
            .select_from(ResourcePolicy)
            .where(ResourcePolicy.tenant_id == tenant_id)
        )
    ).scalar()
    log.bind(tenant=str(tenant_id)).info("admin.tenant_summary")
    return {
        "tenant_id": str(tenant_id),
        "plans": plans_count or 0,
        "keys": keys_count or 0,
        "policies": policies_count or 0,
    }
