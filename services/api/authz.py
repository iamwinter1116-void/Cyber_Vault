"""RBAC matrix loader, authorize() dependency, and startup route check."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

import yaml
from fastapi import FastAPI, Request

from core.abh_core.audit import append as audit_append
from services.api.deps import AuthContext, require_session
from services.api.middleware import ApiError

_MATRIX_PATH = Path(__file__).resolve().parents[2] / "contracts" / "rbac_matrix.yaml"


@dataclass(frozen=True)
class RuleSpec:
    id: str
    method: str
    path: str
    public: bool
    allow: dict[str, str]
    audit: str


def load_matrix(path: Path = _MATRIX_PATH) -> dict[str, RuleSpec]:
    """Load contracts/rbac_matrix.yaml keyed by rule ID."""
    raw = cast(dict[str, Any], yaml.safe_load(path.read_text(encoding="utf-8")))
    rules: dict[str, RuleSpec] = {}
    for item in cast(list[dict[str, Any]], raw["rules"]):
        rid = str(item["id"])
        rules[rid] = RuleSpec(
            id=rid,
            method=str(item["method"]).upper(),
            path=str(item["path"]),
            public=bool(item.get("public", False)),
            allow={str(k): str(v) for k, v in dict(item.get("allow", {})).items()},
            audit=str(item.get("audit", "")),
        )
    return rules


MATRIX: dict[str, RuleSpec] = load_matrix()


def verify_route_coverage(app: FastAPI, *, require_all: bool = False) -> None:
    """Verify registered /api/v1 routes exist in rbac_matrix.yaml (deny by default)."""
    prefix = "/api/v1"
    registered: set[tuple[str, str]] = set()
    paths = cast(dict[str, dict[str, object]], app.openapi().get("paths", {}))
    for full_path, ops in paths.items():
        if full_path.startswith(prefix):
            rel = full_path[len(prefix) :]
            for method in ops:
                if method.upper() in {"GET", "POST", "PUT", "PATCH", "DELETE"}:
                    registered.add((method.upper(), rel))
    matrix_pairs = {(r.method, r.path) for r in MATRIX.values()}
    unknown = registered - matrix_pairs
    if unknown:
        raise RuntimeError(f"Unmapped routes missing from rbac_matrix.yaml: {sorted(unknown)}")
    if require_all and registered != matrix_pairs:
        missing = matrix_pairs - registered
        raise RuntimeError(f"Missing matrix routes: {sorted(missing)}")


@dataclass(frozen=True)
class ScopedAuth:
    ctx: AuthContext
    scope: str
    rule: RuleSpec


def record_denied(
    ctx: AuthContext,
    rule: RuleSpec,
    *,
    target_type: str,
    target_id: str,
    reason: str,
) -> None:
    """Write a denied audit record in its own transaction and check burst alert."""
    action = rule.audit or "authz.denied"
    with ctx.transaction() as conn:
        audit_append(
            conn,
            actor=ctx.actor,
            action=action,
            target_type=target_type,
            target_id=target_id,
            outcome="denied",
            ip=ctx.ip,
            request_id=ctx.request_id,
            detail={"rule": rule.id, "reason": reason},
        )
        with conn.cursor() as cur:
            cur.execute(
                "SELECT count(*) FROM audit_log "
                "WHERE actor_id = %s AND outcome = 'denied' "
                "AND ts >= to_char((now() - interval '60 seconds') AT TIME ZONE 'UTC', "
                "'YYYY-MM-DD\"T\"HH24:MI:SS.US\"Z\"')",
                (str(ctx.user.id),),
            )
            cnt_row = cur.fetchone()
            if cnt_row is not None and isinstance(cnt_row[0], int) and cnt_row[0] >= 5:
                cur.execute(
                    "INSERT INTO activity_event (team_id, severity, kind, message) "
                    "VALUES (%s, 'warn', 'alert.authz_denied_burst', %s)",
                    (ctx.user.team_id, f"User {ctx.user.id} reached {cnt_row[0]} denials in 60s"),
                )


def authorize(rule_id: str) -> Callable[[Request], ScopedAuth]:
    """Return a FastAPI dependency enforcing session, CSRF, and matrix role."""
    rule = MATRIX[rule_id]

    def _dep(request: Request) -> ScopedAuth:
        ctx = require_session(request)
        scope = rule.allow.get(ctx.user.role)
        if scope is None:
            record_denied(ctx, rule, target_type="route", target_id=rule.id, reason="role")
            raise ApiError("FORBIDDEN", 403, "Insufficient role")
        return ScopedAuth(ctx=ctx, scope=scope, rule=rule)

    return _dep
