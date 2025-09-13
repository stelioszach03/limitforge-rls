from __future__ import annotations

from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import BaseModel, Field


# Existing MVP request/response kept for compatibility
class CheckRequest(BaseModel):
    namespace: str
    subject: str
    strategy: str
    params: Optional[Dict[str, Any]] = None
    cost: Optional[int] = 1


class CheckResponse(BaseModel):
    allowed: bool
    remaining: int
    reset_ms: int


# New unified data-plane request/decision models
class CheckRequestV2(BaseModel):
    resource: str
    subject: str
    cost: int = 1
    plan_id: Optional[UUID] = None


class CheckDecision(BaseModel):
    allowed: bool
    remaining: int
    limit: int
    reset_at: int
    retry_after_ms: int
    algorithm: str
    headers: Dict[str, str] = Field(default_factory=dict)


# Admin DTOs
class TenantCreate(BaseModel):
    name: str


class PlanCreate(BaseModel):
    tenant_id: UUID
    name: str
    algorithm: str
    limit_per_window: Optional[int] = None
    window_seconds: Optional[int] = None
    bucket_capacity: Optional[int] = None
    refill_rate_per_sec: Optional[float] = None
    concurrency_limit: Optional[int] = None
    cost_per_call: int = 1
    burst_factor: float = 1.0


class ApiKeyCreate(BaseModel):
    tenant_id: UUID
    name: str


class ResourcePolicyCreate(BaseModel):
    tenant_id: UUID
    resource: str
    subject_type: str
    plan_id: UUID
