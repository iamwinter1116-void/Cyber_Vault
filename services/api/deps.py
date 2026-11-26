"""Request dependencies: DB pool, session validation, CSRF check, and actor context."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Literal, cast
from uuid import UUID

import psycopg
from fastapi import Request
from psycopg_pool import ConnectionPool

from core.abh_core.audit import Actor
from core.abh_core.settings import Settings
from services.api.middleware import ApiError
from services.api.schemas import UserOut
from services.api.security import hash_session_token

SESSION_COOKIE = "abh_session"
_UNSAFE_METHODS = frozenset({"POST", "PATCH", "PUT", "DELETE"})


@dataclass(frozen=True)
class AuthContext:
    """Authenticated caller context for a request."""

    user: UserOut
    actor: Actor
    token_sha256: str
    csrf_token: str
    ip: str
    request_id: str
    pool: ConnectionPool[psycopg.Connection[tuple[object, ...]]]

    @contextmanager
    def transaction(self) -> Iterator[psycopg.Connection[tuple[object, ...]]]:
        with self.pool.connection() as conn, conn.transaction():
            yield conn


def get_settings(request: Request) -> Settings:
    settings = getattr(request.app.state, "settings", None)
    return settings if isinstance(settings, Settings) else Settings()


def get_pool(request: Request) -> ConnectionPool[psycopg.Connection[tuple[object, ...]]] | None:
    pool = getattr(request.app.state, "db_pool", None)
    return pool if isinstance(pool, ConnectionPool) else None


def client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
    if forwarded:
        return forwarded[:64]
    return request.client.host if request.client else ""


def get_request_id(request: Request) -> str:
    rid = getattr(request.state, "request_id", "")
    return rid if isinstance(rid, str) else ""


def require_session(request: Request) -> AuthContext:
    """Validate abh_session cookie, idle/absolute expiry, disabled flag, and CSRF."""
    raw_token = request.cookies.get(SESSION_COOKIE, "")
    if not raw_token:
        raise ApiError("UNAUTHENTICATED", 401, "Authentication required")
    pool = get_pool(request)
    if pool is None:
        raise ApiError("INTERNAL", 500, "Database pool not configured")

    settings = get_settings(request)
    token_sha = hash_session_token(raw_token)
    with pool.connection() as conn, conn.transaction(), conn.cursor() as cur:
        cur.execute(
            "SELECT s.csrf_token, u.id, u.email, u.role, u.team_id, u.disabled, "
            "to_char(u.created_at AT TIME ZONE 'UTC', 'YYYY-MM-DD\"T\"HH24:MI:SS\"Z\"') "
            "FROM session s JOIN app_user u ON u.id = s.user_id "
            "WHERE s.token_sha256 = %s "
            "AND s.expires_at > now() "
            "AND s.last_seen_at + make_interval(mins => %s) > now()",
            (token_sha, settings.session_idle_min),
        )
        row = cur.fetchone()
        if row is None or bool(row[5]):
            raise ApiError("UNAUTHENTICATED", 401, "Session invalid or expired")
        cur.execute("UPDATE session SET last_seen_at = now() WHERE token_sha256 = %s", (token_sha,))

    csrf_token = str(row[0])
    if request.method in _UNSAFE_METHODS:
        header_csrf = request.headers.get("X-CSRF-Token", "")
        if not header_csrf or header_csrf != csrf_token:
            raise ApiError("CSRF_FAILED", 403, "CSRF token missing or invalid")

    user_id = cast(UUID, row[1])
    role = cast(Literal["admin", "team_lead", "analyst", "auditor"], str(row[3]))
    team_id = cast(UUID | None, row[4])
    user = UserOut(
        id=user_id,
        email=str(row[2]),
        role=role,
        team_id=team_id,
        disabled=bool(row[5]),
        created_at=str(row[6]),
    )
    actor = Actor(
        type="user",
        id=str(user_id),
        role=role,
        team_id="" if team_id is None else str(team_id),
    )
    return AuthContext(
        user=user,
        actor=actor,
        token_sha256=token_sha,
        csrf_token=csrf_token,
        ip=client_ip(request),
        request_id=get_request_id(request),
        pool=pool,
    )
