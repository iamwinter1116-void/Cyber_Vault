"""Admin overview (R29) and kill-switch (R30) routes."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Annotated, cast

from core.abh_core.audit import append as audit_append
from core.abh_core.settings import Settings
from fastapi import APIRouter, Depends

from services.api.authz import ScopedAuth, authorize
from services.api.schemas import CheckpointOut, KillSwitchRequest, KillSwitchResponse

router = APIRouter(prefix="/admin", tags=["admin"])


def _host_totals() -> tuple[int, int]:
    cpu_total = (os.cpu_count() or 4) * 1000
    mem_total = 8192
    meminfo = Path("/proc/meminfo")
    if meminfo.exists():
        for line in meminfo.read_text(encoding="utf-8").splitlines():
            if line.startswith("MemTotal:"):
                mem_total = int(line.split()[1]) // 1024
                break
    return cpu_total, mem_total


@router.get("/overview")
def admin_overview(auth: Annotated[ScopedAuth, Depends(authorize("R29"))]) -> dict[str, object]:
    """Return live SQL counts, host allocation, ledger status, and isolation tier."""
    cfg = Settings()
    cpu_total, mem_total = _host_totals()
    with auth.ctx.transaction() as conn, conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM app_user")
        users_cnt = int(cast(int, (cur.fetchone() or (0,))[0]))
        cur.execute("SELECT count(*) FROM team")
        teams_cnt = int(cast(int, (cur.fetchone() or (0,))[0]))
        cur.execute("SELECT observed_state, count(*) FROM env GROUP BY observed_state")
        envs_by_state = {str(r[0]): int(cast(int, r[1])) for r in cur.fetchall()}
        cur.execute(
            "SELECT COALESCE(sum(cpu_millis),0), COALESCE(sum(mem_mb),0), COALESCE(sum(storage_mb),0) "
            "FROM env WHERE observed_state NOT IN ('destroyed', 'failed')"
        )
        alloc = cur.fetchone() or (0, 0, 0)
        cur.execute(
            "SELECT count(*) FROM activity_event "
            "WHERE severity IN ('warn', 'critical') AND ts >= now() - interval '1 hour'"
        )
        alerts_cnt = int(cast(int, (cur.fetchone() or (0,))[0]))
        cur.execute("SELECT count(*) FROM audit_log")
        records_cnt = int(cast(int, (cur.fetchone() or (0,))[0]))
        cur.execute(
            "SELECT log_id, tree_size, root_hash, head_hash, ts, signature "
            "FROM audit_checkpoint ORDER BY tree_size DESC LIMIT 1"
        )
        cp_row = cur.fetchone()
    last_cp = (
        CheckpointOut(
            v=1,
            log_id=str(cp_row[0]),
            tree_size=int(cast(int, cp_row[1])),
            root_hash=str(cp_row[2]),
            head_hash=str(cp_row[3]),
            ts=str(cp_row[4]),
            signature=str(cp_row[5]),
        ).model_dump()
        if cp_row is not None
        else None
    )
    return {
        "users": users_cnt,
        "teams": teams_cnt,
        "envs_by_state": envs_by_state,
        "host": {
            "cpu_millis_total": cpu_total,
            "cpu_millis_allocated": int(cast(int, alloc[0])),
            "mem_mb_total": mem_total,
            "mem_mb_allocated": int(cast(int, alloc[1])),
            "storage_mb_allocated": int(cast(int, alloc[2])),
        },
        "alerts_last_hour": alerts_cnt,
        "ledger": {"records": records_cnt, "last_checkpoint": last_cp, "last_verify": None},
        "isolation": {"runtime": cfg.sandbox_runtime, "degraded": cfg.allow_degraded},
    }


@router.post("/kill-switch", status_code=202, response_model=KillSwitchResponse)
def kill_switch(
    body: KillSwitchRequest,
    auth: Annotated[ScopedAuth, Depends(authorize("R30"))],
) -> KillSwitchResponse:
    """Set desired_state='stopped' on running environments for one team or all teams."""
    with auth.ctx.transaction() as conn, conn.cursor() as cur:
        cur.execute(
            "UPDATE env SET desired_state = 'stopped', updated_at = now() "
            "WHERE desired_state = 'running' AND (%s::uuid IS NULL OR team_id = %s::uuid)",
            (body.team_id, body.team_id),
        )
        affected = cur.rowcount
        audit_append(
            conn,
            actor=auth.ctx.actor,
            action="admin.kill_switch",
            target_type="team" if body.team_id is not None else "platform",
            target_id=str(body.team_id) if body.team_id is not None else "all",
            outcome="success",
            ip=auth.ctx.ip,
            request_id=auth.ctx.request_id,
            detail={"affected": affected},
        )
        return KillSwitchResponse(affected=affected)
