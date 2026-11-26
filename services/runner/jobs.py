"""Exec jobs: claim, run inside the sandbox, finish with one job.finished audit record and activity event
(docs/08 section 6). Docker calls checked against docker-py 7.2.0 source (APIClient.exec_create, exec_start,
exec_inspect); none has run against a daemon. Assumes one runner per stack (R-23), so a job still `running`
at start-up was cut off by a restart.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Mapping
from typing import Any, cast

from psycopg.types.json import Jsonb

from core.abh_core.audit import Actor, append
from core.abh_core.db import transaction
from services.runner.exec_policy import DEADLINE_SEC, OUTPUT_CAP, clean_output, exec_argv, status, target
from services.runner.reconcile import ACTIVITY_SQL, ENV_COLS, Conn, Pool, env_row

log = logging.getLogger("abh.runner")
GRACE_SEC = 5  # host-side bound: a background child may keep the output stream open after the deadline
CLAIM_SQL = """UPDATE job SET status = 'running', started_at = now()
 WHERE id = (SELECT id FROM job WHERE status = 'queued' AND kind = 'exec' ORDER BY created_at
             LIMIT 1 FOR UPDATE SKIP LOCKED)
RETURNING id::text, env_id::text, team_id::text, input"""
ENV_SQL = f"SELECT {ENV_COLS} FROM env WHERE id = %s::uuid"
FINISH_SQL = ("UPDATE job SET status = %s, result = %s, finished_at = now()"
              " WHERE id = %s::uuid AND status = 'running'")
ORPHANS_SQL = ("SELECT id::text, env_id::text, team_id::text FROM job"
               " WHERE status = 'running' AND kind = 'exec' FOR UPDATE")
Job = tuple[str, str, str, Mapping[str, object]]


def finish(conn: Conn, job_id: str, env_id: str, team_id: str, state: str, result: Mapping[str, object]) -> bool:
    """Final job row, its audit record and its activity event together; False if the job is not running."""
    if conn.execute(FINISH_SQL, (state, Jsonb(dict(result)), job_id)).rowcount != 1:
        return False
    detail = {"kind": "exec", "status": state, "env_id": env_id,
              **{k: result[k] for k in ("exit_code", "duration_ms", "truncated") if k in result}}
    append(conn, actor=Actor(type="service", id="runner", team_id=team_id), action="job.finished",
           target_type="job", target_id=job_id, outcome="success" if state == "done" else "error", detail=detail)
    conn.execute(ACTIVITY_SQL, (team_id, env_id, "info", "job.finished", f"exec job {job_id} {state}",
                                Jsonb({"job_id": job_id, "status": state})))
    return True


def claim(pool: Pool) -> Job | None:
    with transaction(pool) as conn:
        row = conn.execute(CLAIM_SQL).fetchone()
    return None if row is None else (str(row[0]), str(row[1]), str(row[2]), cast(Mapping[str, object], row[3]))


def run_exec(api: Any, container: str, command: str) -> tuple[int | None, bytes, bool, bool, int]:
    """(exit code, first OUTPUT_CAP bytes, more output existed, host bound hit, duration ms). Output beyond the
    cap is read and discarded so the runner's memory stays bounded."""
    started = time.monotonic()
    exec_id = api.exec_create(container, exec_argv(command), user="1000:1000")["Id"]
    stream = api.exec_start(exec_id, stream=True)
    buf, more, hit = bytearray(), False, False
    try:
        for chunk in stream:
            room = OUTPUT_CAP - len(buf)
            buf += chunk[:room]
            more = more or len(chunk) > room
            if time.monotonic() - started > DEADLINE_SEC + GRACE_SEC:
                hit = True
                break
    except Exception:  # a read timeout after the deadline is a timeout; anything earlier is an error
        if time.monotonic() - started < DEADLINE_SEC:
            raise
        hit = True
    finally:
        stream.close()
    duration_ms = int((time.monotonic() - started) * 1000)
    info = api.exec_inspect(exec_id)
    for _ in range(20):  # the stream can end a moment before the engine records the exit code
        if not info["Running"]:
            break
        time.sleep(0.1)
        info = api.exec_inspect(exec_id)
    return (None if info["Running"] else info["ExitCode"]), bytes(buf), more, hit, duration_ms


def run_job(pool: Pool, api: Any, job: Job) -> str:
    job_id, env_id, team_id, data = job
    try:
        with transaction(pool) as conn:
            row = conn.execute(ENV_SQL, (env_id,)).fetchone()
        if row is None:
            raise ValueError("environment row not found")
        env, observed, _, _ = env_row(row)
        container, command = target(env, observed, data)
        code, raw, more, hit, ms = run_exec(api, container, command)
        output, truncated = clean_output(raw, more)
        state: str = status(code, ms, hit)
        result: dict[str, object] = {"exit_code": code, "output": output, "truncated": truncated, "duration_ms": ms}
    except Exception as exc:
        state, result = "error", {"error": f"{type(exc).__name__}: {exc}"[:500]}
    with transaction(pool) as conn:
        finish(conn, job_id, env_id, team_id, state, result)
    return state


def recover_orphans(pool: Pool) -> int:
    """At start-up: end exec jobs left `running` by a previous runner process as error, each audited."""
    with transaction(pool) as conn:
        rows = conn.execute(ORPHANS_SQL).fetchall()
        for job_id, env_id, team_id in rows:
            finish(conn, str(job_id), str(env_id), str(team_id), "error", {"error": "runner restarted during the job"})
    return len(rows)


def work_forever(pool: Pool, api: Any) -> None:
    """One worker thread; several run so a long job does not delay a neighbour's exec (T-RES-02)."""
    while True:
        try:
            job = claim(pool)
            if job is None:
                time.sleep(0.5)
                continue
            log.info("exec job %s finished: %s", job[0], run_job(pool, api, job))
        except Exception:
            log.exception("exec worker pass failed; retrying in 1 s")
            time.sleep(1)
