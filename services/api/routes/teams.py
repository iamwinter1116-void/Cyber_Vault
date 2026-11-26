"""Team and quota routes: R07 list, R08 create, R09 quota update."""

from __future__ import annotations

from typing import Annotated, cast
from uuid import UUID

import psycopg
from core.abh_core.audit import append as audit_append
from fastapi import APIRouter, Depends, Query

from services.api.authz import ScopedAuth, authorize, record_denied
from services.api.middleware import ApiError
from services.api.schemas import TeamCreate, TeamOut, TeamQuotaUpdate, TeamUsageOut

router = APIRouter(prefix="/teams", tags=["teams"])

_TEAM_SELECT = (
    "SELECT t.id, t.name, t.quota_envs, t.quota_cpu_millis, t.quota_mem_mb, t.quota_storage_mb, "
    "COALESCE(count(e.id), 0), COALESCE(sum(e.cpu_millis), 0), "
    "COALESCE(sum(e.mem_mb), 0), COALESCE(sum(e.storage_mb), 0) "
    "FROM team t LEFT JOIN env e ON e.team_id = t.id AND e.observed_state NOT IN ('destroyed', 'failed') "
)


def _row_to_team(row: tuple[object, ...]) -> TeamOut:
    return TeamOut(
        id=cast(UUID, row[0]),
        name=str(row[1]),
        quota_envs=int(cast(int, row[2])),
        quota_cpu_millis=int(cast(int, row[3])),
        quota_mem_mb=int(cast(int, row[4])),
        quota_storage_mb=int(cast(int, row[5])),
        usage=TeamUsageOut(
            envs=int(cast(int, row[6])),
            cpu_millis=int(cast(int, row[7])),
            mem_mb=int(cast(int, row[8])),
            storage_mb=int(cast(int, row[9])),
        ),
    )


@router.get("")
def list_teams(
    auth: Annotated[ScopedAuth, Depends(authorize("R07"))],
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    cursor: UUID | None = None,
) -> dict[str, object]:
    """List teams and live usage in caller's scope."""
    where_parts = ["true"]
    params: list[object] = []
    if auth.scope == "team":
        where_parts.append("t.id = %s")
        params.append(auth.ctx.user.team_id)
    if cursor is not None:
        where_parts.append("t.id > %s")
        params.append(cursor)
    params.append(limit + 1)
    sql = f"{_TEAM_SELECT} WHERE {' AND '.join(where_parts)} GROUP BY t.id ORDER BY t.id LIMIT %s"
    with auth.ctx.transaction() as conn, conn.cursor() as cur:
        cur.execute(sql, params)
        rows = cur.fetchall()
    has_more = len(rows) > limit
    items = [_row_to_team(r) for r in rows[:limit]]
    return {"items": items, "next_cursor": str(items[-1].id) if has_more else None}


@router.post("", status_code=201, response_model=TeamOut)
def create_team(
    body: TeamCreate,
    auth: Annotated[ScopedAuth, Depends(authorize("R08"))],
) -> TeamOut:
    """Create a team with optional quotas and record team.create atomically."""
    try:
        with auth.ctx.transaction() as conn, conn.cursor() as cur:
            cur.execute(
                "INSERT INTO team (name, quota_envs, quota_cpu_millis, quota_mem_mb, quota_storage_mb) "
                "VALUES (%s, COALESCE(%s, 4), COALESCE(%s, 2000), COALESCE(%s, 2048), COALESCE(%s, 1024)) "
                "RETURNING id, name, quota_envs, quota_cpu_millis, quota_mem_mb, quota_storage_mb, 0, 0, 0, 0",
                (body.name, body.quota_envs, body.quota_cpu_millis, body.quota_mem_mb, body.quota_storage_mb),
            )
            row = cur.fetchone()
            assert row is not None
            team = _row_to_team(row)
            audit_append(
                conn,
                actor=auth.ctx.actor,
                action="team.create",
                target_type="team",
                target_id=str(team.id),
                outcome="success",
                ip=auth.ctx.ip,
                request_id=auth.ctx.request_id,
                detail={"name": team.name},
            )
            return team
    except psycopg.errors.UniqueViolation as exc:
        record_denied(auth.ctx, auth.rule, target_type="team", target_id="", reason="duplicate_name")
        raise ApiError("CONFLICT", 409, "Team name already exists") from exc


@router.patch("/{team_id}", response_model=TeamOut)
def update_team_quota(
    team_id: UUID,
    body: TeamQuotaUpdate,
    auth: Annotated[ScopedAuth, Depends(authorize("R09"))],
) -> TeamOut:
    """Update team quota fields and record team.quota_update atomically."""
    with auth.ctx.transaction() as conn, conn.cursor() as cur:
        cur.execute(
            "UPDATE team SET "
            "quota_envs = COALESCE(%s, quota_envs), "
            "quota_cpu_millis = COALESCE(%s, quota_cpu_millis), "
            "quota_mem_mb = COALESCE(%s, quota_mem_mb), "
            "quota_storage_mb = COALESCE(%s, quota_storage_mb) "
            "WHERE id = %s RETURNING id",
            (body.quota_envs, body.quota_cpu_millis, body.quota_mem_mb, body.quota_storage_mb, team_id),
        )
        if cur.fetchone() is None:
            raise ApiError("NOT_FOUND", 404, "Team not found")
        cur.execute(f"{_TEAM_SELECT} WHERE t.id = %s GROUP BY t.id", (team_id,))
        row = cur.fetchone()
        assert row is not None
        team = _row_to_team(row)
        audit_append(
            conn,
            actor=auth.ctx.actor,
            action="team.quota_update",
            target_type="team",
            target_id=str(team_id),
            outcome="success",
            ip=auth.ctx.ip,
            request_id=auth.ctx.request_id,
            detail={
                "quota_envs": team.quota_envs,
                "quota_cpu_millis": team.quota_cpu_millis,
                "quota_mem_mb": team.quota_mem_mb,
                "quota_storage_mb": team.quota_storage_mb,
            },
        )
        return team
