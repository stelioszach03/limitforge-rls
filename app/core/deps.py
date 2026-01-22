from functools import lru_cache
from typing import Optional

from fastapi import Request, Depends
from redis.asyncio import Redis

from app.core.config import settings, get_settings
from app.core.security import (
    verify_admin,
    get_api_key_from_header,
    hash_api_key,
    verify_api_key as _verify_api_key,
)
from app.db.session import AsyncSessionLocal
from sqlalchemy.ext.asyncio import AsyncSession
from app.rl.engine import DecisionEngine
from app.db import crud


@lru_cache()
def _redis_client() -> Redis:
    return Redis.from_url(settings.REDIS_URL, decode_responses=True)


async def get_redis() -> Redis:
    return _redis_client()


async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session


def get_settings_dep():
    return get_settings()


_engine_singleton: Optional[DecisionEngine] = None


def get_engine(redis: Redis = Depends(get_redis)) -> DecisionEngine:
    global _engine_singleton
    if _engine_singleton is None:
        _engine_singleton = DecisionEngine(
            redis=redis, settings=settings, crud_module=crud
        )
    return _engine_singleton


async def require_api_key(
    request: Request,
    redis: Redis = Depends(get_redis),
):
    raw = get_api_key_from_header(request)
    key_hash = hash_api_key(raw, settings.APIKEY_HASH_SALT)
    # Lazily open DB only after header presence is confirmed
    async with AsyncSessionLocal() as db:
        await _verify_api_key(db, redis, key_hash)
    return raw


# Re-export admin verifier
require_admin = verify_admin
