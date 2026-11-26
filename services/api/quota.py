"""Team and host-capacity admission control for environment creation."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Literal, cast
from uuid import UUID

import psycopg

from core.abh_core.settings import Settings
from services.api.authz import ScopedAuth
from services.api.middleware import ApiError
from services.api.schemas import EnvOut

SIZES: dict[str, tuple[int, int, int, int]] = {
    "S": (500, 256, 128, 128),
    "M": (1000, 512, 256, 256),
    "L": (2000, 1024, 512, 512),
}

ENV_COLS = (
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
            raise ApiError("QUOTA_EXCEEDED", 409, "Team quota or host capacity exceeded")
        try:
            cur.execute(
                "INSERT INTO env (team_id, owner_id, name, template, size, cpu_millis, mem_mb, storage_mb, "
                "pids_limit, expires_at) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, "
                f"now() + make_interval(mins => %s)) RETURNING {ENV_COLS}",
                (auth.ctx.user.team_id, auth.ctx.user.id, name, template, size, cpu, mem, storage, pids, ttl_minutes),
            )
        except psycopg.errors.UniqueViolation as exc:
            raise ApiError("CONFLICT", 409, "Environment name already exists") from exc
        row = cur.fetchone()
        assert row is not None
        return row_to_env(row)
