"""User management routes: R04 list, R05 create, R06 update."""

from __future__ import annotations

from typing import Annotated, Literal, cast
from uuid import UUID

import psycopg
from core.abh_core.audit import append as audit_append
from fastapi import APIRouter, Depends, Query

from services.api.authz import ScopedAuth, authorize, record_denied
from services.api.middleware import ApiError
from services.api.schemas import UserCreate, UserOut, UserUpdate
from services.api.security import hash_password

router = APIRouter(prefix="/users", tags=["users"])


def _row_to_user(row: tuple[object, ...]) -> UserOut:
    return UserOut(
        id=cast(UUID, row[0]),
        email=str(row[1]),
        role=cast(Literal["admin", "team_lead", "analyst", "auditor"], str(row[2])),
        team_id=cast(UUID | None, row[3]),
        disabled=bool(row[4]),
        created_at=str(row[5]),
    )


@router.get("")
def list_users(
    auth: Annotated[ScopedAuth, Depends(authorize("R04"))],
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    cursor: UUID | None = None,
) -> dict[str, object]:
    """List users in caller's scope (all for admin/auditor, own team for team_lead)."""
    where_parts = ["true"]
    params: list[object] = []
    if auth.scope == "team":
        where_parts.append("team_id = %s")
        params.append(auth.ctx.user.team_id)
    if cursor is not None:
        where_parts.append("id > %s")
        params.append(cursor)
    params.append(limit + 1)
    sql = (
        "SELECT id, email, role, team_id, disabled, "
        "to_char(created_at AT TIME ZONE 'UTC', 'YYYY-MM-DD\"T\"HH24:MI:SS\"Z\"') "
        f"FROM app_user WHERE {' AND '.join(where_parts)} ORDER BY id LIMIT %s"
    )
    with auth.ctx.transaction() as conn, conn.cursor() as cur:
        cur.execute(sql, params)
        rows = cur.fetchall()
    has_more = len(rows) > limit
    items = [_row_to_user(r) for r in rows[:limit]]
    return {"items": items, "next_cursor": str(items[-1].id) if has_more else None}


@router.post("", status_code=201, response_model=UserOut)
def create_user(
    body: UserCreate,
    auth: Annotated[ScopedAuth, Depends(authorize("R05"))],
) -> UserOut:
    """Create a user and record user.create atomically."""
    if (body.role in ("admin", "auditor")) != (body.team_id is None):
        raise ApiError("VALIDATION", 422, "Platform roles require team_id=null; team roles require team_id")
    email = body.email.strip().lower()
    pw_hash = hash_password(body.password)
    try:
        with auth.ctx.transaction() as conn, conn.cursor() as cur:
            cur.execute(
                "INSERT INTO app_user (email, password_hash, role, team_id) VALUES (%s, %s, %s, %s) "
                "RETURNING id, email, role, team_id, disabled, "
                "to_char(created_at AT TIME ZONE 'UTC', 'YYYY-MM-DD\"T\"HH24:MI:SS\"Z\"')",
                (email, pw_hash, body.role, body.team_id),
            )
            row = cur.fetchone()
            assert row is not None
            user = _row_to_user(row)
            audit_append(
                conn,
                actor=auth.ctx.actor,
                action="user.create",
                target_type="user",
                target_id=str(user.id),
                outcome="success",
                ip=auth.ctx.ip,
                request_id=auth.ctx.request_id,
                detail={"role": user.role},
            )
            return user
    except psycopg.errors.UniqueViolation as exc:
        record_denied(auth.ctx, auth.rule, target_type="user", target_id="", reason="duplicate_email")
        raise ApiError("CONFLICT", 409, "User email already exists") from exc


@router.patch("/{user_id}", response_model=UserOut)
def update_user(
    user_id: UUID,
    body: UserUpdate,
    auth: Annotated[ScopedAuth, Depends(authorize("R06"))],
) -> UserOut:
    """Update user role/team/disabled/password enforcing BR1 and BR2."""
    with auth.ctx.transaction() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT id, email, role, team_id, disabled, "
            "to_char(created_at AT TIME ZONE 'UTC', 'YYYY-MM-DD\"T\"HH24:MI:SS\"Z\"') "
            "FROM app_user WHERE id = %s FOR UPDATE",
            (user_id,),
        )
        row = cur.fetchone()
        if row is None:
            raise ApiError("NOT_FOUND", 404, "User not found")
        cur_role = str(row[2])
        cur_team = cast(UUID | None, row[3])
        cur_disabled = bool(row[4])

        new_role = body.role if body.role is not None else cur_role
        new_disabled = body.disabled if body.disabled is not None else cur_disabled
        new_team = body.team_id if "team_id" in body.model_fields_set else cur_team

        if user_id == auth.ctx.user.id and new_role != cur_role:
            record_denied(auth.ctx, auth.rule, target_type="user", target_id=str(user_id), reason="self_role_change")
            raise ApiError("SELF_ROLE_CHANGE", 409, "Cannot change your own role")
        if cur_role == "admin" and not cur_disabled and (new_role != "admin" or new_disabled):
            cur.execute("SELECT count(*) FROM app_user WHERE role = 'admin' AND NOT disabled AND id <> %s", (user_id,))
            cnt_row = cur.fetchone()
            if cnt_row is not None and cnt_row[0] == 0:
                record_denied(auth.ctx, auth.rule, target_type="user", target_id=str(user_id), reason="last_admin")
                raise ApiError("LAST_ADMIN", 409, "Cannot disable or demote the last enabled admin")
        if (new_role in ("admin", "auditor")) != (new_team is None):
            raise ApiError("VALIDATION", 422, "Platform roles require team_id=null; team roles require team_id")

        if body.password is not None:
            cur.execute("UPDATE app_user SET password_hash = %s WHERE id = %s", (hash_password(body.password), user_id))
        cur.execute(
            "UPDATE app_user SET role = %s, team_id = %s, disabled = %s WHERE id = %s "
            "RETURNING id, email, role, team_id, disabled, "
            "to_char(created_at AT TIME ZONE 'UTC', 'YYYY-MM-DD\"T\"HH24:MI:SS\"Z\"')",
            (new_role, new_team, new_disabled, user_id),
        )
        updated = cur.fetchone()
        assert updated is not None
        if new_disabled or new_role != cur_role:
            cur.execute("DELETE FROM session WHERE user_id = %s", (user_id,))
        audit_append(
            conn,
            actor=auth.ctx.actor,
            action="user.update",
            target_type="user",
            target_id=str(user_id),
            outcome="success",
            ip=auth.ctx.ip,
            request_id=auth.ctx.request_id,
            detail={"role": new_role, "disabled": new_disabled},
        )
        return _row_to_user(updated)
