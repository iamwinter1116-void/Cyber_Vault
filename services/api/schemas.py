"""Canonical Pydantic request and response schemas (docs/04_CONTRACTS.md sec 3-4)."""

from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class _InputModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ErrorDetail(BaseModel):
    code: str
    message: str
    request_id: str


class ErrorResponse(BaseModel):
    error: ErrorDetail


class UserOut(BaseModel):
    id: UUID
    email: str
    role: Literal["admin", "team_lead", "analyst", "auditor"]
    team_id: UUID | None
    disabled: bool
    created_at: str


class LoginRequest(_InputModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=256)


class AuthSessionOut(BaseModel):
    user: UserOut
    csrf_token: str


class UserCreate(_InputModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=12, max_length=256)
    role: Literal["admin", "team_lead", "analyst", "auditor"]
    team_id: UUID | None = None


class UserUpdate(_InputModel):
    role: Literal["admin", "team_lead", "analyst", "auditor"] | None = None
    team_id: UUID | None = None
    disabled: bool | None = None
    password: str | None = Field(default=None, min_length=12, max_length=256)


class TeamUsageOut(BaseModel):
    envs: int
    cpu_millis: int
    mem_mb: int
    storage_mb: int


class TeamOut(BaseModel):
    id: UUID
    name: str
    quota_envs: int
    quota_cpu_millis: int
    quota_mem_mb: int
    quota_storage_mb: int
    usage: TeamUsageOut


class TeamCreate(_InputModel):
    name: str = Field(pattern=r"^[a-z0-9-]{3,32}$")
    quota_envs: int | None = Field(default=None, ge=0)
    quota_cpu_millis: int | None = Field(default=None, ge=0)
    quota_mem_mb: int | None = Field(default=None, ge=0)
    quota_storage_mb: int | None = Field(default=None, ge=0)


class TeamQuotaUpdate(_InputModel):
    quota_envs: int | None = Field(default=None, ge=0)
    quota_cpu_millis: int | None = Field(default=None, ge=0)
    quota_mem_mb: int | None = Field(default=None, ge=0)
    quota_storage_mb: int | None = Field(default=None, ge=0)


class TemplateOut(BaseModel):
    name: str
    title: str
    description: str
    containers: list[str]
    sizes: list[Literal["S", "M", "L"]]


class EnvOut(BaseModel):
    id: UUID
    team_id: UUID
    owner_id: UUID
    name: str
    template: Literal["app-target", "file-analysis", "ai-redteam"]
    size: Literal["S", "M", "L"]
    cpu_millis: int
    mem_mb: int
    storage_mb: int
    pids_limit: int
    desired_state: Literal["running", "stopped", "destroyed"]
    observed_state: Literal["requested", "provisioning", "running", "stopped", "destroyed", "failed"]
    isolation_tier: Literal["", "gvisor", "runc-hardened"]
    failure_reason: str
    expires_at: str
    created_at: str


class EnvCreate(_InputModel):
    name: str = Field(pattern=r"^[a-z0-9-]{3,32}$")
    template: Literal["app-target"]
    size: Literal["S", "M", "L"]
    ttl_minutes: int | None = Field(default=None, ge=1, le=240)


class MetricSampleOut(BaseModel):
    ts: str
    cpu_pct: float
    mem_mb: float
    storage_mb: float
    pids: int
    net_rx_bytes: int
    net_tx_bytes: int


class JobOut(BaseModel):
    id: UUID
    kind: Literal["exec", "file_analysis", "ai_scan"]
    env_id: UUID
    team_id: UUID
    requested_by: UUID
    input: dict[str, object]
    status: Literal["queued", "running", "done", "timeout", "error"]
    result: dict[str, object]
    created_at: str
    started_at: str | None
    finished_at: str | None


class ExecRequest(_InputModel):
    command: str = Field(min_length=1, max_length=4096)
    container: Literal["toolbox", "target"] = "toolbox"


class AiScanRequest(_InputModel):
    target: Literal["stub-vulnerable", "stub-guarded"]
    probe_set: Literal["quick", "full"]


class ActivityEventOut(BaseModel):
    id: int
    ts: str
    team_id: UUID | None
    env_id: UUID | None
    severity: Literal["info", "warn", "critical"]
    kind: str
    message: str
    data: dict[str, object]


class AuditRecordOut(BaseModel):
    v: int
    seq: int
    ts: str
    actor_type: Literal["user", "service", "system"]
    actor_id: str
    actor_role: str
    team_id: str
    action: str
    target_type: str
    target_id: str
    outcome: Literal["success", "denied", "error"]
    ip: str
    request_id: str
    detail: dict[str, object]
    prev_hash: str
    hash: str


class CheckpointOut(BaseModel):
    v: int
    log_id: str
    tree_size: int
    root_hash: str
    head_hash: str
    ts: str
    signature: str


class VerifyResultOut(BaseModel):
    ok: bool
    verdict: str
    at: int | None
    records: int
    checkpoints: int
    unanchored_tail: int
    checked_at: str


class HealthzOut(BaseModel):
    status: Literal["ok"]
    db: bool


class KillSwitchRequest(_InputModel):
    team_id: UUID | None = None


class KillSwitchResponse(BaseModel):
    affected: int
