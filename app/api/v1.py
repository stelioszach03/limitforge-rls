from fastapi import APIRouter, Depends, Response, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_redis, get_db, get_engine
from app.rl.engine import DecisionEngine
from app.rl.schemas import CheckRequestV2, CheckDecision
from app.observability.metrics import RL_ALLOWED, RL_BLOCKED, REQUESTS_TOTAL
from app.core.logging import get_logger
from app.core.config import settings
from app.core.security import (
    get_api_key_from_header,
    hash_api_key,
    verify_api_key as verify_api_key_db,
)
from app.db.models import SubjectType

router = APIRouter()
log = get_logger("api.v1")


@router.get("/health")
async def health():
    log.info("health")
    REQUESTS_TOTAL.labels(route="/v1/health", outcome="success").inc()
    return {"status": "ok", "version": settings.APP_VERSION}


@router.post("/check", response_model=CheckDecision)
async def check_rate_limit(
    payload: CheckRequestV2,
    response: Response,
    request: Request,
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
    engine: DecisionEngine = Depends(get_engine),
):
    raw_key = get_api_key_from_header(request)
    key_hash = hash_api_key(raw_key, settings.APIKEY_HASH_SALT)
    api_key_row = await verify_api_key_db(db, redis, key_hash)

    plan = await engine.resolve_plan(
        db=db,
        tenant_id=api_key_row.tenant_id,
        resource=payload.resource,
        subject_type=SubjectType.api_key,
        explicit_plan_id=payload.plan_id,
    )

    decision = await engine.check(
        tenant_id=api_key_row.tenant_id,
        subject=payload.subject,
        resource=payload.resource,
        cost=payload.cost or 1,
        plan=plan,
    )

    for k, v in decision.headers.items():
        response.headers[k] = v

    if decision.allowed:
        RL_ALLOWED.inc()
        REQUESTS_TOTAL.labels(route="/v1/check", outcome="allowed").inc()
    else:
        RL_BLOCKED.inc()
        REQUESTS_TOTAL.labels(route="/v1/check", outcome="blocked").inc()
        response.status_code = 429

    log.bind(
        resource=payload.resource,
        sub=payload.subject,
        alg=decision.algorithm,
        allowed=decision.allowed,
        remaining=decision.remaining,
    ).info("check")
    return decision
