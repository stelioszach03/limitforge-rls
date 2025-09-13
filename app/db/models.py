from __future__ import annotations

import uuid
from enum import Enum
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import (
    String,
    Boolean,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Integer,
    Float,
)
from sqlalchemy.sql import func
from sqlalchemy.types import TypeDecorator
from sqlalchemy.dialects.postgresql import UUID as PGUUID


class GUID(TypeDecorator):
    impl = String(36)
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(PGUUID(as_uuid=True))
        return dialect.type_descriptor(String(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        if isinstance(value, uuid.UUID):
            return str(value) if dialect.name != "postgresql" else value
        return str(value)


class Base(DeclarativeBase):
    pass


class PlanAlgorithm(str, Enum):
    token_bucket = "token_bucket"
    fixed_window = "fixed_window"
    sliding_window = "sliding_window"
    concurrency = "concurrency"


class SubjectType(str, Enum):
    api_key = "api_key"
    ip = "ip"
    user_id = "user_id"


class Tenant(Base):
    __tablename__ = "tenants"
    id: Mapped[uuid.UUID] = mapped_column(
        "id", GUID(), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    plans: Mapped[list[Plan]] = relationship(back_populates="tenant")  # type: ignore[name-defined]
    api_keys: Mapped[list[ApiKey]] = relationship(back_populates="tenant")  # type: ignore[name-defined]
    policies: Mapped[list[ResourcePolicy]] = relationship(back_populates="tenant")  # type: ignore[name-defined]


class Plan(Base):
    __tablename__ = "plans"
    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    algorithm: Mapped[PlanAlgorithm] = mapped_column(
        SAEnum(PlanAlgorithm, name="plan_algorithm"), nullable=False
    )
    limit_per_window: Mapped[int | None] = mapped_column(Integer, nullable=True)
    window_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    bucket_capacity: Mapped[int | None] = mapped_column(Integer, nullable=True)
    refill_rate_per_sec: Mapped[float | None] = mapped_column(Float, nullable=True)
    concurrency_limit: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cost_per_call: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="1"
    )
    burst_factor: Mapped[float] = mapped_column(
        Float, nullable=False, server_default="1.0"
    )
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    tenant: Mapped[Tenant] = relationship(back_populates="plans")
    policies: Mapped[list[ResourcePolicy]] = relationship(back_populates="plan")  # type: ignore[name-defined]


class ApiKey(Base):
    __tablename__ = "api_keys"
    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    key_hash: Mapped[str] = mapped_column(
        String(128), unique=True, index=True, nullable=False
    )
    active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    revoked_at: Mapped[DateTime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    tenant: Mapped[Tenant] = relationship(back_populates="api_keys")


class ResourcePolicy(Base):
    __tablename__ = "resource_policies"
    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    resource: Mapped[str] = mapped_column(String(300), nullable=False)
    subject_type: Mapped[SubjectType] = mapped_column(
        SAEnum(SubjectType, name="subject_type"), nullable=False
    )
    plan_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("plans.id", ondelete="CASCADE"), nullable=False
    )
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    tenant: Mapped[Tenant] = relationship(back_populates="policies")
    plan: Mapped[Plan] = relationship(back_populates="policies")
