from functools import lru_cache
from typing import Literal, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Application
    APP_NAME: str = "LimitForge RLS"
    APP_ENV: Literal["dev", "prod"] = "dev"
    APP_VERSION: str = "0.1.0"

    # Backing services
    POSTGRES_DSN: str = (
        "postgresql+psycopg://postgres:postgres@localhost:5432/limitforge"
    )
    REDIS_URL: str = "redis://localhost:6379/0"

    # Ops
    LOG_LEVEL: str = "INFO"

    # Auth / Secrets
    ADMIN_BEARER_TOKEN: str = "change-me-admin-token"
    APIKEY_HASH_SALT: str = "change-me-salt"

    # Observability
    OTEL_EXPORTER_OTLP_ENDPOINT: Optional[str] = None
    METRICS_NAMESPACE: str = "limitforge"

    # Back-compat/derived fields for existing code paths
    DEFAULT_STRATEGY: str = "token_bucket"

    model_config = SettingsConfigDict(env_file=".env", env_prefix="")

    # Derived aliases to avoid breaking callers
    @property
    def OTEL_SERVICE_NAME(self) -> str:  # type: ignore
        return self.APP_NAME

    @property
    def ADMIN_TOKEN(self) -> str:  # type: ignore
        return self.ADMIN_BEARER_TOKEN


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
