"""Collectors and alerts (docs/08 section 5; docs/04_CONTRACTS.md sections 6 and 7.6; risks R-03, R-04, R-16).

Docker calls (events, stats, exec of df) were checked against docker-py 7.2.0 source; the stats and event field
names follow the Docker Engine API. None has run against a daemon: the R-04 memory cross-check, the OOM alert
latency and T-MON-02 are Linux-host acceptance and still pending.
"""

from __future__ import annotations

import logging
import os
import time
from collections.abc import Mapping, Sequence
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Any, cast

import docker.errors

from core.abh_core.audit import append
from core.abh_core.db import transaction
from services.runner import storage
from services.runner.launch import MANAGED, EnvRow, canonical_id
from services.runner.metrics import (
    EVENT_FILTERS, MIB, SAMPLE_KEYS, classify, df_used_mb, due_alerts, env_sample, payload, usage,
)
from services.runner.reconcile import ENV_COLS, FAILED, Conn, Pool, actor, env_row, event, record

log = logging.getLogger("abh.runner")

RUNNING_SQL = f"SELECT {ENV_COLS} FROM env WHERE observed_state = 'running' AND id::text = ANY(%s)"
LOCK_SQL = f"SELECT {ENV_COLS} FROM env WHERE id = %s::uuid FOR UPDATE"
INSERT_SQL = """INSERT INTO metric_sample (env_id, cpu_pct, mem_mb, storage_mb, pids, net_rx_bytes, net_tx_bytes)
VALUES (%s::uuid, %s, %s, %s, %s, %s, %s) RETURNING ts"""
NOTIFY_SQL = "SELECT pg_notify('abh_metric', %s)"
RECENT_SQL = "SELECT cpu_pct, mem_mb, storage_mb FROM metric_sample WHERE env_id = %s::uuid ORDER BY ts DESC LIMIT 5"
THROTTLE_SQL = ("SELECT 1 FROM activity_event WHERE env_id = %s::uuid AND kind = %s"
                " AND ts > now() - interval '5 minutes' LIMIT 1")
PRUNE_SQL = "DELETE FROM metric_sample WHERE ts < now() - interval '1 hour'"


def storage_used(env: EnvRow, method: str | None, volume_dir: str, containers: Sequence[Any]) -> float:
    """docs/08 section 4: V1 the allocated size of the image file; V2/V3 the used size seen inside the sandbox.
    A V2 volume is shared by the env's containers (largest reading); each V3 tmpfs is per container (sum)."""
    if storage.require(method) == "V1":
        return os.stat(storage.image_path(volume_dir, env)).st_blocks * 512 / MIB
    used = []
    for c in containers:
        r = c.exec_run(["df", "-P", "-k", "/workspace"], user="1000:1000")
        if r.exit_code != 0:
            raise RuntimeError(f"df in {c.name} exited {r.exit_code}")
        used.append(df_used_mb(r.output))
    return sum(used) if method == "V3" else max(used)


def throttled(conn: Conn, env_id: str, kind: str) -> bool:
    """One alert per environment per kind per five minutes, read from activity_event so a restart keeps it."""
    return conn.execute(THROTTLE_SQL, (env_id, kind)).fetchone() is not None


def write_sample(conn: Conn, env: EnvRow, sample: Mapping[str, float | int]) -> list[str]:
    """Insert, notify and raise any due threshold alert; returns the alert kinds written."""
    ts = cast(tuple[datetime], conn.execute(INSERT_SQL, (env.id, *(sample[k] for k in SAMPLE_KEYS))).fetchone())[0]
    conn.execute(NOTIFY_SQL, (payload(env.id, ts, sample),))
    recent = cast(list[tuple[float, float, float]], conn.execute(RECENT_SQL, (env.id,)).fetchall())
    raised = [k for k in due_alerts(env, recent) if not throttled(conn, env.id, k)]
    for kind in raised:
        event(conn, env, kind, "warn", f"{kind}: threshold of docs/04 section 6 crossed", dict(sample))
    return raised


def sample_once(client: Any, pool: Pool, volume_dir: str, method: str | None) -> int:
    """One stats pass over running managed containers; Docker work happens before the write transaction."""
    groups: dict[str, list[Any]] = {}
    for c in client.containers.list(filters={"label": MANAGED, "status": "running"}):
        if (env_id := canonical_id(c.labels.get("abh.env_id"))) is not None:
            groups.setdefault(env_id, []).append(c)
    with transaction(pool) as conn:
        envs = [env_row(r)[0] for r in conn.execute(RUNNING_SQL, (sorted(groups),)).fetchall()]
    with ThreadPoolExecutor(max_workers=8) as ex:  # each non-streamed stats call waits about two engine cycles
        docs = {env.id: [ex.submit(c.stats, stream=False) for c in groups[env.id]] for env in envs}
    samples = []
    for env in envs:
        try:
            parts = [usage(f.result()) for f in docs[env.id]]
            samples.append((env, env_sample(env, parts, storage_used(env, method, volume_dir, groups[env.id]))))
        except Exception:
            log.exception("no sample for env %s this interval", env.id)
    with transaction(pool) as conn:
        for env, sample in samples:
            write_sample(conn, env, sample)
        conn.execute(PRUNE_SQL)
    return len(samples)


def sample_forever(client: Any, pool: Pool, volume_dir: str, method: str | None, interval: float) -> None:
    """Forever, in its own thread: one pass every ABH_METRIC_INTERVAL_SEC (04 section 9 default 2 s)."""
    while True:
        started = time.monotonic()
        try:
            sample_once(client, pool, volume_dir, method)
        except Exception:
            log.exception("metric pass failed; retrying next interval")
        time.sleep(max(0.0, interval - (time.monotonic() - started)))


def on_oom(pool: Pool, env_id: str, container: str) -> bool:
    """alert.oom_killed plus one env.oom_killed audit record, throttled together."""
    with transaction(pool) as conn:
        row = conn.execute(LOCK_SQL, (env_id,)).fetchone()
        if row is None or throttled(conn, env_id, "alert.oom_killed"):
            return False
        env = env_row(row)[0]
        append(conn, actor=actor(env), action="env.oom_killed", target_type="env", target_id=env.id,
               outcome="success", detail={"mem_limit_mb": env.mem_mb})
        event(conn, env, "alert.oom_killed", "critical", f"out-of-memory kill in {container} (limit {env.mem_mb} MB)",
              {"container": container, "mem_limit_mb": env.mem_mb})
    return True


def on_die(pool: Pool, env_id: str, container: str, exit_code: str, oom: bool) -> bool:
    """An unexpected exit: only a running env that should run and has not expired becomes failed; exits caused
    by the runner's own stop, destroy, expiry or provisioning leave the row to the reconciler."""
    reason = f"container {container} exited unexpectedly (exit code {exit_code}{', out of memory' if oom else ''})"
    with transaction(pool) as conn:
        row = conn.execute(LOCK_SQL, (env_id,)).fetchone()
        if row is None:
            return False
        env, observed, desired, expired = env_row(row)
        if (observed, desired, expired) != ("running", "running", False):
            return False
        return record(conn, env, "running", FAILED.target_state, FAILED.audit_action, FAILED.activity,
                      outcome="error", reason=reason, detail={"reason": reason})


def handle(client: Any, pool: Pool, ev: Mapping[str, Any]) -> None:
    got = classify(ev)
    if got is None:
        return
    env_id, action, attrs = got
    name = attrs.get("name", "")
    if action == "oom":
        on_oom(pool, env_id, name)
        return
    try:  # the die of an OOM-killed container carries the flag even if no oom event arrived
        oom = bool(client.containers.get(ev["Actor"]["ID"]).attrs["State"]["OOMKilled"])
    except docker.errors.NotFound:
        oom = False
    if oom:
        on_oom(pool, env_id, name)
    on_die(pool, env_id, name, attrs.get("exitCode", "unknown"), oom)


def watch_events(client: Any, pool: Pool) -> None:
    """Forever, in its own thread. After any stream or handler error it reconnects from the last event second;
    replayed events are harmless (oom is throttled, die needs a running row)."""
    since = int(time.time())
    while True:
        try:
            for ev in client.events(since=since, filters=EVENT_FILTERS, decode=True):
                since = int(ev.get("time", since))
                handle(client, pool, ev)
        except Exception:
            log.exception("docker events stream lost; reconnecting in 2 s")
        time.sleep(2)
