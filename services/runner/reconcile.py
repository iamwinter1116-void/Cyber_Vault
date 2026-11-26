"""Reconcile loop over env rows (docs/08 section 3; risk R-10).

Pattern per pass: one short transaction claims rows with FOR UPDATE SKIP LOCKED (requested rows become
provisioning there); the Docker work runs with no transaction open; a second short transaction writes the new
observed_state, its audit record (core.abh_core.audit.append) and its activity events together.
"""

from __future__ import annotations

import logging
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Protocol, cast

import psycopg
from psycopg.types.json import Jsonb
from psycopg_pool import ConnectionPool

from core.abh_core.audit import Actor, Outcome, append
from core.abh_core.db import transaction
from services.runner.launch import EnvRow, RuntimeChoice
from services.runner.state import FAILED, Step, Work, decide

Conn = psycopg.Connection[tuple[object, ...]]
Pool = ConnectionPool[Conn]
log = logging.getLogger("abh.runner")

ENV_COLS = ("id::text, team_id::text, template, cpu_millis, mem_mb, storage_mb, pids_limit, observed_state, "
            "desired_state, expires_at <= now()")
CLAIM_SQL = f"""
SELECT {ENV_COLS}
  FROM env
 WHERE observed_state <> 'destroyed'
   AND (observed_state <> desired_state OR expires_at <= now())
   AND NOT (observed_state IN ('failed', 'stopped') AND desired_state <> 'destroyed' AND expires_at > now())
 ORDER BY updated_at
 LIMIT %s
   FOR UPDATE SKIP LOCKED
"""
WRITE_SQL = """
UPDATE env SET observed_state = %s, isolation_tier = COALESCE(%s::text, isolation_tier),
               failure_reason = COALESCE(%s::text, failure_reason), updated_at = now()
 WHERE id = %s::uuid AND observed_state = %s
"""
ACTIVITY_SQL = """
INSERT INTO activity_event (team_id, env_id, severity, kind, message, data)
VALUES (%s::uuid, %s::uuid, %s, %s, %s, %s)
"""
LIVE_SQL = "SELECT id::text FROM env WHERE observed_state NOT IN ('destroyed', 'failed') AND id::text = ANY(%s)"
CHANGED = (("env.state_changed", "info"),)


class DockerWork(Protocol):
    def provision(self, env: EnvRow) -> RuntimeChoice: ...
    def stop(self, env: EnvRow) -> None: ...
    def destroy(self, env_id: str) -> None: ...
    def labelled_env_ids(self) -> set[str]: ...
    def remove_unowned(self) -> int: ...


@dataclass(frozen=True)
class Claimed:
    env: EnvRow
    observed: str  # observed_state after the claim transaction
    step: Step


def actor(env: EnvRow) -> Actor:
    return Actor(type="service", id="runner", team_id=env.team_id)


def event(conn: Conn, env: EnvRow, kind: str, severity: str, message: str, data: Mapping[str, object]) -> None:
    conn.execute(ACTIVITY_SQL, (env.team_id, env.id, severity, kind, message, Jsonb(dict(data))))


def record(conn: Conn, env: EnvRow, old: str, new: str, action: str | None, activity: Sequence[tuple[str, str]],
           *, outcome: Outcome = "success", tier: str | None = None, reason: str | None = None,
           detail: Mapping[str, object] | None = None) -> bool:
    """One state write with its audit record and activity events; False if the row moved on meanwhile."""
    if conn.execute(WRITE_SQL, (new, tier, reason, env.id, old)).rowcount != 1:
        return False
    data: dict[str, object] = {"from": old, "to": new, **(detail or {})}
    if action is not None:
        append(conn, actor=actor(env), action=action, target_type="env", target_id=env.id, outcome=outcome,
               detail=data)
    for kind, severity in activity:
        event(conn, env, kind, severity, f"{kind}: {old} -> {new}" + (f" ({reason})" if reason else ""), data)
    return True


def env_row(row: tuple[object, ...]) -> tuple[EnvRow, str, str, bool]:
    s, n = (lambda i: cast(str, row[i])), (lambda i: cast(int, row[i]))
    return EnvRow(s(0), s(1), s(2), n(3), n(4), n(5), n(6)), s(7), s(8), bool(row[9])


def claim(pool: Pool, limit: int = 20) -> list[Claimed]:
    out: list[Claimed] = []
    with transaction(pool) as conn:
        for row in conn.execute(CLAIM_SQL, (limit,)).fetchall():
            env, observed, desired, expired = env_row(row)
            step = decide(observed, desired, expired)
            if step is None:
                continue
            if step.work is Work.PROVISION and observed == "requested":
                record(conn, env, "requested", "provisioning", None, CHANGED)
                observed = "provisioning"
            out.append(Claimed(env, observed, step))
    return out


def _provision(pool: Pool, ops: DockerWork, c: Claimed) -> None:
    try:
        choice = ops.provision(c.env)
    except Exception as exc:  # any provisioning error: remove what exists, then a visible failed state
        reason = f"{type(exc).__name__}: {exc}"[:500]
        try:
            ops.destroy(c.env.id)
        except Exception as cleanup:
            reason = f"{reason}; cleanup failed: {type(cleanup).__name__}: {cleanup}"[:500]
        with transaction(pool) as conn:
            record(conn, c.env, c.observed, FAILED.target_state, FAILED.audit_action, FAILED.activity,
                   outcome="error", reason=reason, detail={"reason": reason[:200]})
        return
    detail = {"runtime": choice.runtime, "isolation_tier": choice.isolation_tier}
    with transaction(pool) as conn:
        written = record(conn, c.env, c.observed, "running", c.step.audit_action, c.step.activity,
                         tier=choice.isolation_tier, reason="", detail=detail)
        if written and choice.degraded:
            append(conn, actor=actor(c.env), action="isolation.degraded", target_type="env", target_id=c.env.id,
                   outcome="success", detail={**detail, "profile": "T0.H1.N2"})
            event(conn, c.env, "alert.isolation_degraded", "critical",
                   "isolation degraded: runc-hardened instead of gVisor, profile T0.H1.N2", detail)


def apply(pool: Pool, ops: DockerWork, c: Claimed) -> None:
    if c.step.work is Work.PROVISION:
        _provision(pool, ops, c)
        return
    if c.step.work is Work.STOP:
        ops.stop(c.env)
    else:
        ops.destroy(c.env.id)
    with transaction(pool) as conn:
        record(conn, c.env, c.observed, c.step.target_state, c.step.audit_action, c.step.activity)


def reconcile_once(pool: Pool, ops: DockerWork) -> int:
    """One pass; a failed stop or destroy is logged and retried on the next pass."""
    done = 0
    for c in claim(pool):
        try:
            apply(pool, ops, c)
            done += 1
        except Exception:
            log.exception("reconcile %s %s failed; will retry", c.env.id, c.step.work.value)
    return done


def reap(pool: Pool, ops: DockerWork) -> set[str]:
    """Remove labelled objects whose env row is destroyed or missing (docs/08 section 3, every 30 s).

    Also: managed objects with no valid abh.env_id (removed outright) and V1 image files whose env is not live.
    A failed row is terminal (no start route), so its leftovers are retried here every pass until gone; the row
    stays failed. Live rows (requested, provisioning, running, stopped) keep their objects and image."""
    unowned = ops.remove_unowned()
    if unowned:
        log.warning("reaper removed %d abh.managed objects without a valid abh.env_id", unowned)
    labelled = ops.labelled_env_ids()
    if not labelled:
        return set()
    with transaction(pool) as conn:
        live = {cast(str, r[0]) for r in conn.execute(LIVE_SQL, (sorted(labelled),)).fetchall()}
    stale = labelled - live
    for env_id in sorted(stale):
        ops.destroy(env_id)
    return stale
