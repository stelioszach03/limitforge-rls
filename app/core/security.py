import hashlib
import hmac
from typing import Optional

from fastapi import Header, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.models import ApiKey


def hash_api_key(raw: str, salt: str) -> str:
    # Deterministic HMAC-SHA256 using provided salt (pepper)
    return hmac.new(
        salt.encode("utf-8"), raw.encode("utf-8"), hashlib.sha256
    ).hexdigest()


def constant_time_equals(a: str, b: str) -> bool:
    return hmac.compare_digest(a, b)


def get_api_key_from_header(request: Request) -> str:
    key = request.headers.get("X-API-Key")
    if not key:
        raise HTTPException(status_code=401, detail="Missing X-API-Key")
    return key


async def verify_api_key(db: AsyncSession, redis, key_hash: str) -> ApiKey:
    # Redis cache check
    cache_key = f"api_key:{key_hash}"
    cached = await redis.get(cache_key)
    if cached == "1":
        # Fast path; trust cached validity (active & not revoked)
        res = await db.execute(select(ApiKey).where(ApiKey.key_hash == key_hash))
        obj = res.scalar_one_or_none()
        if obj is not None and obj.active and obj.revoked_at is None:
            return obj

    # DB validation
    res = await db.execute(select(ApiKey).where(ApiKey.key_hash == key_hash))
    obj: Optional[ApiKey] = res.scalar_one_or_none()
    if obj is None or not obj.active or obj.revoked_at is not None:
        raise HTTPException(status_code=403, detail="Invalid API key")

    # cache positive validation
    await redis.setex(cache_key, 60, "1")
    return obj


async def verify_admin(authorization: str | None = Header(None)) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    token = authorization.split(" ", 1)[1]
    if token != settings.ADMIN_BEARER_TOKEN:
        raise HTTPException(status_code=403, detail="Invalid admin token")
    return token
