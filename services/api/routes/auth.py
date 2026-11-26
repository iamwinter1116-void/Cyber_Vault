"""Authentication routes: R01 login, R02 logout, R03 me."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal, cast
from uuid import UUID

import psycopg
from core.abh_core.audit import Actor
from core.abh_core.audit import append as audit_append
from fastapi import APIRouter, Depends, Request, Response

from services.api.deps import (
    SESSION_COOKIE,
    AuthContext,
    client_ip,
    get_pool,
    get_request_id,
    get_settings,
    require_session,
)
from services.api.middleware import ApiError
from services.api.schemas import AuthSessionOut, LoginRequest, UserOut
from services.api.security import (
    generate_csrf_token,
    generate_session_token,
    hash_password,
    hash_session_token,
    verify_dummy,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["auth"])
_MAX_FAILS = 5
_LOCK_MINUTES = 15


def _audit_login_denied(
    conn: psycopg.Connection[tuple[object, ...]],
    *,
    actor: Actor,
    target_id: str,
    ip: str,
    rid: str,
    reason: str,
) -> None:
    audit_append(
        conn,
        actor=actor,
        action="auth.login",
        target_type="user",
        target_id=target_id,
        outcome="denied",
        ip=ip,
        request_id=rid,
        detail={"reason": reason},
    )


def _attempt_login(
    conn: psycopg.Connection[tuple[object, ...]],
    *,
    email: str,
    password: str,
    ip: str,
    rid: str,
    ua: str,
    abs_hours: int,
) -> tuple[AuthSessionOut | None, str | None, ApiError | None]:
    """Execute login DB work inside a committed transaction; return (result, raw_token, error)."""
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id, email, password_hash, role, team_id, disabled, failed_logins, locked_until, "
            "now(), to_char(created_at AT TIME ZONE 'UTC', 'YYYY-MM-DD\"T\"HH24:MI:SS\"Z\"') "
            "FROM app_user WHERE email = %s FOR UPDATE",
            (email,),
        )
        row = cur.fetchone()
        if row is None:
            verify_dummy(password)
            _audit_login_denied(
                conn, actor=Actor(type="user", id="anonymous"), target_id="", ip=ip, rid=rid, reason="invalid_credentials"
            )
            return None, None, ApiError("UNAUTHENTICATED", 401, "Invalid email or password")

        user_id = cast(UUID, row[0])
        role = cast(Literal["admin", "team_lead", "analyst", "auditor"], str(row[3]))
        team_id = cast(UUID | None, row[4])
        disabled = bool(row[5])
        failed_logins = int(cast(int, row[6]))
        locked_until = cast(datetime | None, row[7])
        now_dt = cast(datetime, row[8])
        actor = Actor(type="user", id=str(user_id), role=role, team_id="" if team_id is None else str(team_id))

        if disabled:
            verify_dummy(password)
            _audit_login_denied(conn, actor=actor, target_id=str(user_id), ip=ip, rid=rid, reason="disabled")
            return None, None, ApiError("UNAUTHENTICATED", 401, "Invalid email or password")

        if locked_until is not None and locked_until > now_dt:
            verify_dummy(password)
            _audit_login_denied(conn, actor=actor, target_id=str(user_id), ip=ip, rid=rid, reason="locked")
            return None, None, ApiError("ACCOUNT_LOCKED", 403, "Account temporarily locked")

        if locked_until is not None and locked_until <= now_dt:
            failed_logins = 0

        ok, needs_rehash = verify_password(password, str(row[2]))
        if not ok:
            new_fails = failed_logins + 1
            if new_fails >= _MAX_FAILS:
                cur.execute(
                    "UPDATE app_user SET failed_logins = %s, "
                    "locked_until = now() + make_interval(mins => %s) WHERE id = %s",
                    (new_fails, _LOCK_MINUTES, user_id),
                )
                audit_append(
                    conn, actor=actor, action="auth.lockout", target_type="user", target_id=str(user_id),
                    outcome="denied", ip=ip, request_id=rid, detail={"failures": new_fails},
                )
                cur.execute(
                    "INSERT INTO activity_event (team_id, severity, kind, message) "
                    "VALUES (%s, 'warn', 'alert.login_bruteforce', %s)",
                    (team_id, f"Account locked after {new_fails} failed logins"),
                )
                return None, None, ApiError("ACCOUNT_LOCKED", 403, "Account temporarily locked")

            cur.execute("UPDATE app_user SET failed_logins = %s, locked_until = NULL WHERE id = %s", (new_fails, user_id))
            _audit_login_denied(conn, actor=actor, target_id=str(user_id), ip=ip, rid=rid, reason="invalid_credentials")
            return None, None, ApiError("UNAUTHENTICATED", 401, "Invalid email or password")

        if needs_rehash:
            cur.execute("UPDATE app_user SET password_hash = %s WHERE id = %s", (hash_password(password), user_id))

        cur.execute("UPDATE app_user SET failed_logins = 0, locked_until = NULL WHERE id = %s", (user_id,))
        raw_token = generate_session_token()
        csrf_token = generate_csrf_token()
        cur.execute(
            "INSERT INTO session (token_sha256, user_id, csrf_token, ip, user_agent, expires_at) "
            "VALUES (%s, %s, %s, %s, %s, now() + make_interval(hours => %s))",
            (hash_session_token(raw_token), user_id, csrf_token, ip, ua, abs_hours),
        )
        audit_append(
            conn, actor=actor, action="auth.login", target_type="user", target_id=str(user_id),
            outcome="success", ip=ip, request_id=rid, detail={"mfa": False},
        )
    user = UserOut(id=user_id, email=str(row[1]), role=role, team_id=team_id, disabled=False, created_at=str(row[9]))
    return AuthSessionOut(user=user, csrf_token=csrf_token), raw_token, None


@router.post("/login", response_model=AuthSessionOut)
def login(body: LoginRequest, request: Request, response: Response) -> AuthSessionOut:
    """Authenticate user with Argon2id, lockout, session cookie, and CSRF token."""
    pool = get_pool(request)
    if pool is None:
        raise ApiError("INTERNAL", 500, "Database pool not configured")

    settings = get_settings(request)
    with pool.connection() as conn, conn.transaction():
        out, raw_token, err = _attempt_login(
            conn,
            email=body.email.strip().lower(),
            password=body.password,
            ip=client_ip(request),
            rid=get_request_id(request),
            ua=request.headers.get("User-Agent", "")[:256],
            abs_hours=settings.session_abs_hours,
        )
    if err is not None:
        raise err
    assert out is not None and raw_token is not None
    response.set_cookie(
        key=SESSION_COOKIE, value=raw_token, httponly=True, secure=True,
        samesite="strict", path="/", max_age=settings.session_abs_hours * 3600,
    )
    return out


@router.post("/logout", status_code=204)
def logout(response: Response, ctx: Annotated[AuthContext, Depends(require_session)]) -> None:
    """Delete current session and record auth.logout atomically."""
    with ctx.transaction() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM session WHERE token_sha256 = %s", (ctx.token_sha256,))
        audit_append(
            conn, actor=ctx.actor, action="auth.logout", target_type="user",
            target_id=str(ctx.user.id), outcome="success", ip=ctx.ip, request_id=ctx.request_id,
        )
    response.delete_cookie(key=SESSION_COOKIE, path="/", httponly=True, secure=True, samesite="strict")


@router.get("/me", response_model=AuthSessionOut)
def me(ctx: Annotated[AuthContext, Depends(require_session)]) -> AuthSessionOut:
    """Return the authenticated user and current CSRF token."""
    return AuthSessionOut(user=ctx.user, csrf_token=ctx.csrf_token)
