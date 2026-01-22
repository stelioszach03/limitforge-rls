from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings


def _to_async_dsn(dsn: str) -> str:
    if dsn.startswith("postgresql+psycopg"):
        return dsn.replace("postgresql+psycopg", "postgresql+asyncpg", 1)
    return dsn


DATABASE_URL = _to_async_dsn(settings.POSTGRES_DSN)

engine = create_async_engine(DATABASE_URL, echo=False, future=True)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session
