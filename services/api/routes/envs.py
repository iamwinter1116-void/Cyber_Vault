"""Environment routes (R11-R17) and shared quota-admission helper."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Annotated, Literal, cast
from uuid import UUID

import psycopg
from core.abh_core.audit import append as audit_append
from core.abh_core.settings import Settings
from fastapi import APIRouter, Depends, Query

from services.api.authz import ScopedAuth, authorize, record_denied
from services.api.middleware import ApiError
from services.api.schemas import EnvCreate, EnvOut, ExecRequest, JobOut, MetricSampleOut

router = APIRouter(prefix="/envs", tags=["envs"])

SIZES: dict[str, tuple[int, int, int, int]] = {
    "S": (500, 256, 128, 128),
    "M": (1000, 512, 256, 256),
    "L": (2000, 1024, 512, 512),
}

_ENV_COLS = (
    "id, team_id, owner_id, name, template, size, cpu_millis, mem_mb, storage_mb, pids_limit, "
    "desired_state, observed_state, isolation_tier, failure_reason, "
    "to_char(expires_at AT TIME ZONE 'UTC', 'YYYY-MM-DD\"T\"HH24:MI:SS\"Z\"'), "
    "to_char(created_at AT TIME ZONE 'UTC', 'YYYY-MM-DD\"T\"HH24:MI:SS\"Z\"')"
)


def row_to_env(row: tuple[object, ...]) -> EnvOut:
    return EnvOut(
        id=cast(UUID, row[0]),
        team_id=cast(UUID, row[1]),
        owner_id=cast(UUID, row[2]),
        name=str(row[3]),
        template=cast(Literal["app-target", "file-analysis", "ai-redteam"], str(row[4])),
        size=cast(Literal["S", "M", "L"], str(row[5])),
        cpu_millis=int(cast(int, row[6])),
        mem_mb=int(cast(int, row[7])),
        storage_mb=int(cast(int, row[8])),
        pids_limit=int(cast(int, row[9])),
        desired_state=cast(Literal["running", "stopped", "destroyed"], str(row[10])),
        observed_state=cast(
            Literal["requested", "provisioning", "running", "stopped", "destroyed", "failed"], str(row[11])
        ),
        isolation_tier=cast(Literal["", "gvisor", "runc-hardened"], str(row[12])),
        failure_reason=str(row[13]),
        expires_at=str(row[14]),
        created_at=str(row[15]),
    )


def _host_capacity(settings: Settings) -> tuple[int, int]:
    cpu_total = (os.cpu_count() or 4) * 1000
    mem_total = 8192
    meminfo = Path("/proc/meminfo")
    if meminfo.exists():
        for line in meminfo.read_text(encoding="utf-8").splitlines():
            if line.startswith("MemTotal:"):
                mem_total = int(line.split()[1]) // 1024
                break
    return max(0, cpu_total - settings.host_reserved_cpu_millis), max(0, mem_total - settings.host_reserved_mem_mb)


def create_env_with_quota(
    conn: psycopg.Connection[tuple[object, ...]],
    auth: ScopedAuth,
    settings: Settings,
    *,
    name: str,
    template: str,
    size: str,
    ttl_minutes: int,
) -> EnvOut:
    """Lock team row, enforce team + host quotas, and insert env."""
    if auth.ctx.user.team_id is None:
        raise ApiError("FORBIDDEN", 403, "Team membership required")
    cpu, mem, storage, pids = SIZES[size]
    with conn.cursor() as cur:
        cur.execute(
            "SELECT quota_envs, quota_cpu_millis, quota_mem_mb, quota_storage_mb FROM team WHERE id = %s FOR UPDATE",
            (auth.ctx.user.team_id,),
        )
        qrow = cur.fetchone()
        if qrow is None:
            raise ApiError("NOT_FOUND", 404, "Team not found")
        cur.execute(
            "SELECT count(*), COALESCE(sum(cpu_millis),0), COALESCE(sum(mem_mb),0), COALESCE(sum(storage_mb),0) "
            "FROM env WHERE team_id = %s AND observed_state NOT IN ('destroyed', 'failed')",
            (auth.ctx.user.team_id,),
        )
        tu = cur.fetchone()
        assert tu is not None
        cur.execute(
            "SELECT COALESCE(sum(cpu_millis),0), COALESCE(sum(mem_mb),0) "
            "FROM env WHERE observed_state NOT IN ('destroyed', 'failed')"
        )
        hu = cur.fetchone()
        assert hu is not None
        max_cpu, max_mem = _host_capacity(settings)
        team_over = (
            int(cast(int, tu[0])) + 1 > int(cast(int, qrow[0]))
            or int(cast(int, tu[1])) + cpu > int(cast(int, qrow[1]))
            or int(cast(int, tu[2])) + mem > int(cast(int, qrow[2]))
            or int(cast(int, tu[3])) + storage > int(cast(int, qrow[3]))
        )
        host_over = int(cast(int, hu[0])) + cpu > max_cpu or int(cast(int, hu[1])) + mem > max_mem
        if team_over or host_over:
            record_denied(auth.ctx, auth.rule, target_type="env", target_id="", reason="quota_exceeded")
            raise ApiError("QUOTA_EXCEEDED", 409, "Team quota or host capacity exceeded")
        try:
            cur.execute(
                "INSERT INTO env (team_id, owner_id, name, template, size, cpu_millis, mem_mb, storage_mb, "
                "pids_limit, expires_at) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, "
                f"now() + make_interval(mins => %s)) RETURNING {_ENV_COLS}",
                (auth.ctx.user.team_id, auth.ctx.user.id, name, template, size, cpu, mem, storage, pids, ttl_minutes),
            )
        except psycopg.errors.UniqueViolation as exc:
            record_denied(auth.ctx, auth.rule, target_type="env", target_id="", reason="duplicate_name")
            raise ApiError("CONFLICT", 409, "Environment name already exists") from exc
        row = cur.fetchone()
        assert row is not None
        return row_to_env(row)


def _load_scoped_env(
    conn: psycopg.Connection[tuple[object, ...]],
    env_id: UUID,
    auth: ScopedAuth,
    *,
    for_update: bool = False,
) -> EnvOut:
    suffix = " FOR UPDATE" if for_update else ""
    with conn.cursor() as cur:
        cur.execute(f"SELECT {_ENV_COLS} FROM env WHERE id = %s{suffix}", (env_id,))
        row = cur.fetchone()
    if row is None:
        raise ApiError("NOT_FOUND", 404, "Not found")
    env = row_to_env(row)
    if auth.scope in ("team", "own") and env.team_id != auth.ctx.user.team_id:
        record_denied(auth.ctx, auth.rule, target_type="env", target_id=str(env_id), reason="cross_team")
        raise ApiError("NOT_FOUND", 404, "Not found")
    if auth.scope == "own" and env.owner_id != auth.ctx.user.id:
        record_denied(auth.ctx, auth.rule, target_type="env", target_id=str(env_id), reason="not_owner")
        raise ApiError("FORBIDDEN", 403, "Forbidden")
    return env


@router.get("")
def list_envs(
    auth: Annotated[ScopedAuth, Depends(authorize("R11"))],
    team_id: UUID | None = None,
    state: str | None = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    cursor: UUID | None = None,
) -> dict[str, object]:
    """List environments in caller's scope."""
    where_parts = ["true"]
    params: list[object] = []
    if auth.scope == "team":
        where_parts.append("team_id = %s")
        params.append(auth.ctx.user.team_id)
    elif team_id is not None:
        where_parts.append("team_id = %s")
        params.append(team_id)
    if state is not None:
        where_parts.append("observed_state = %s")
        params.append(state)
    if cursor is not None:
        where_parts.append("id > %s")
        params.append(cursor)
    params.append(limit + 1)
    sql = f"SELECT {_ENV_COLS} FROM env WHERE {' AND '.join(where_parts)} ORDER BY id LIMIT %s"
    with auth.ctx.transaction() as conn, conn.cursor() as cur:
        cur.execute(sql, params)
        rows = cur.fetchall()
    has_more = len(rows) > limit
    items = [row_to_env(r) for r in rows[:limit]]
    return {"items": items, "next_cursor": str(items[-1].id) if has_more else None}


@router.post("", status_code=201, response_model=EnvOut)
def create_env(body: EnvCreate, auth: Annotated[ScopedAuth, Depends(authorize("R12"))]) -> EnvOut:
    """Create an app-target environment with quota admission and audit."""
    ttl = body.ttl_minutes if body.ttl_minutes is not None else 60
    with auth.ctx.transaction() as conn:
        env = create_env_with_quota(
            conn, auth, Settings(), name=body.name, template=body.template, size=body.size, ttl_minutes=ttl
        )
        audit_append(
            conn,
            actor=auth.ctx.actor,
            action="env.create",
            target_type="env",
            target_id=str(env.id),
            outcome="success",
            ip=auth.ctx.ip,
            request_id=auth.ctx.request_id,
            detail={"template": env.template, "size": env.size},
        )
        return env


@router.get("/{env_id}", response_model=EnvOut)
def get_env(env_id: UUID, auth: Annotated[ScopedAuth, Depends(authorize("R13"))]) -> EnvOut:
    with auth.ctx.transaction() as conn:
        return _load_scoped_env(conn, env_id, auth)


@router.post("/{env_id}/stop", status_code=202, response_model=EnvOut)
def stop_env(env_id: UUID, auth: Annotated[ScopedAuth, Depends(authorize("R14"))]) -> EnvOut:
    with auth.ctx.transaction() as conn:
        _load_scoped_env(conn, env_id, auth, for_update=True)
        with conn.cursor() as cur:
            cur.execute(
                f"UPDATE env SET desired_state = 'stopped', updated_at = now() WHERE id = %s RETURNING {_ENV_COLS}",
                (env_id,),
            )
            row = cur.fetchone()
            assert row is not None
        audit_append(
            conn,
            actor=auth.ctx.actor,
            action="env.stop",
            target_type="env",
            target_id=str(env_id),
            outcome="success",
            ip=auth.ctx.ip,
            request_id=auth.ctx.request_id,
        )
        return row_to_env(row)


@router.delete("/{env_id}", status_code=202, response_model=EnvOut)
def destroy_env(env_id: UUID, auth: Annotated[ScopedAuth, Depends(authorize("R15"))]) -> EnvOut:
    with auth.ctx.transaction() as conn:
        _load_scoped_env(conn, env_id, auth, for_update=True)
        with conn.cursor() as cur:
            cur.execute(
                f"UPDATE env SET desired_state = 'destroyed', updated_at = now() WHERE id = %s RETURNING {_ENV_COLS}",
                (env_id,),
            )
            row = cur.fetchone()
            assert row is not None
        audit_append(
            conn,
            actor=auth.ctx.actor,
            action="env.destroy",
            target_type="env",
            target_id=str(env_id),
            outcome="success",
            ip=auth.ctx.ip,
            request_id=auth.ctx.request_id,
        )
        return row_to_env(row)


@router.get("/{env_id}/metrics")
def get_env_metrics(
    env_id: UUID,
    auth: Annotated[ScopedAuth, Depends(authorize("R16"))],
    minutes: Annotated[int, Query(ge=1, le=60)] = 15,
) -> dict[str, list[MetricSampleOut]]:
    with auth.ctx.transaction() as conn:
        _load_scoped_env(conn, env_id, auth)
        with conn.cursor() as cur:
            cur.execute(
                "SELECT to_char(ts AT TIME ZONE 'UTC', 'YYYY-MM-DD\"T\"HH24:MI:SS\"Z\"'), "
                "cpu_pct, mem_mb, storage_mb, pids, net_rx_bytes, net_tx_bytes "
                "FROM metric_sample WHERE env_id = %s AND ts >= now() - make_interval(mins => %s) ORDER BY ts",
                (env_id, minutes),
            )
            rows = cur.fetchall()
    items = [
        MetricSampleOut(
            ts=str(r[0]),
            cpu_pct=float(cast(float, r[1])),
            mem_mb=float(cast(float, r[2])),
            storage_mb=float(cast(float, r[3])),
            pids=int(cast(int, r[4])),
            net_rx_bytes=int(cast(int, r[5])),
            net_tx_bytes=int(cast(int, r[6])),
        )
        for r in rows
    ]
    return {"items": items}


@router.post("/{env_id}/exec", status_code=202, response_model=JobOut)
def exec_in_env(
    env_id: UUID,
    body: ExecRequest,
    auth: Annotated[ScopedAuth, Depends(authorize("R17"))],
) -> JobOut:
    """Queue an exec job if env.observed_state == 'running' (BR4)."""
    import json

    with auth.ctx.transaction() as conn:
        env = _load_scoped_env(conn, env_id, auth, for_update=True)
        if env.observed_state != "running":
            record_denied(auth.ctx, auth.rule, target_type="env", target_id=str(env_id), reason="env_not_running")
            raise ApiError("ENV_NOT_RUNNING", 409, "Environment is not running")
        job_input: dict[str, object] = {"command": body.command, "container": body.container}
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO job (kind, env_id, team_id, requested_by, input) VALUES ('exec', %s, %s, %s, %s::jsonb) "
                "RETURNING id, kind, env_id, team_id, requested_by, input, status, result, "
                "to_char(created_at AT TIME ZONE 'UTC', 'YYYY-MM-DD\"T\"HH24:MI:SS\"Z\"'), "
                "to_char(started_at AT TIME ZONE 'UTC', 'YYYY-MM-DD\"T\"HH24:MI:SS\"Z\"'), "
                "to_char(finished_at AT TIME ZONE 'UTC', 'YYYY-MM-DD\"T\"HH24:MI:SS\"Z\"')",
                (env_id, env.team_id, auth.ctx.user.id, json.dumps(job_input)),
            )
            jrow = cur.fetchone()
            assert jrow is not None
        audit_append(
            conn,
            actor=auth.ctx.actor,
            action="env.exec",
            target_type="env",
            target_id=str(env_id),
            outcome="success",
            ip=auth.ctx.ip,
            request_id=auth.ctx.request_id,
            detail={
                "command_sha256": hashlib.sha256(body.command.encode("utf-8")).hexdigest(),
                "command_prefix": body.command[:200],
            },
        )
        return JobOut(
            id=cast(UUID, jrow[0]),
            kind="exec",
            env_id=cast(UUID, jrow[2]),
            team_id=cast(UUID, jrow[3]),
            requested_by=cast(UUID, jrow[4]),
            input=cast(dict[str, object], jrow[5]),
            status=cast(Literal["queued", "running", "done", "timeout", "error"], str(jrow[6])),
            result=cast(dict[str, object], jrow[7]),
            created_at=str(jrow[8]),
            started_at=cast(str | None, jrow[9]),
            finished_at=cast(str | None, jrow[10]),
        )
