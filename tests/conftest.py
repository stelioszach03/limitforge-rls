import asyncio
import os
import sys
import pytest
import pytest_asyncio
from typing import AsyncGenerator

# Ensure project root on path
sys.path.insert(0, os.getcwd())

import httpx
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.core.deps import (
    get_redis as _get_redis_dep,
    get_db as _get_db_dep,
    get_engine as _get_engine_dep,
)
from app.db.models import Base
from app.db import crud
from app.rl.engine import DecisionEngine


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture()
async def fake_redis():
    try:
        from fakeredis.aioredis import FakeRedis
    except Exception as e:
        pytest.skip(f"fakeredis not available: {e}")
    r = FakeRedis(decode_responses=True)
    await r.flushall()
    yield r
    await r.aclose()


@pytest.fixture(scope="session")
def pg_dsn() -> str:
    return (
        os.getenv("TEST_POSTGRES_DSN")
        or os.getenv("POSTGRES_DSN")
        or "sqlite+aiosqlite:///./test.db"
    )


@pytest_asyncio.fixture()
async def db(pg_dsn):
    engine = create_async_engine(pg_dsn, future=True)
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
    except Exception as e:
        pytest.skip(f"Cannot init DB: {e}")
    SessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with SessionLocal() as session:
        yield session
    await engine.dispose()


@pytest_asyncio.fixture()
async def async_client(fake_redis, pg_dsn):

    # Attach test redis to app state to avoid deepcopy of lock objects
    app.state._test_redis = fake_redis

    # Create a dedicated engine for this test client and reset schema
    from sqlalchemy.ext.asyncio import create_async_engine
    from sqlalchemy.orm import sessionmaker

    engine = create_async_engine(pg_dsn, future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    SessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    # Override dependencies
    from fastapi import Request

    async def _override_get_redis(request: Request):
        return request.app.state._test_redis

    async def _override_get_db() -> AsyncGenerator[AsyncSession, None]:
        async with SessionLocal() as session:
            yield session

    def _override_get_engine(request: Request):
        from app.core.config import settings as s

        return DecisionEngine(
            redis=request.app.state._test_redis, settings=s, crud_module=crud
        )

    app.dependency_overrides[_get_redis_dep] = _override_get_redis
    app.dependency_overrides[_get_db_dep] = _override_get_db
    app.dependency_overrides[_get_engine_dep] = _override_get_engine

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
