"""Runner SQL against real PostgreSQL with contracts/schema.sql applied, run explicitly (not collected by
pytest's default test_*.py pattern, so `make check-fast` neither runs nor skips it):

  python -m unittest -v tests.unit.runner.live_pg_suite

No Docker is involved or replaced: claim(), record(), the reaper's liveness query, the collector's DB writes
(samples, NOTIFY, alerts, OOM, unexpected exit) and the exec job claim/finish/recovery run here; Docker work
needs the Linux host. Needs docker (imported, no daemon used), psycopg, psycopg-pool, pydantic-settings, and:
  ABH_TEST_ALLOW_DISPOSABLE_DB=1
  ABH_TEST_OWNER_DSN   owner role on a disposable database whose name contains "test" or "disposable"
  ABH_TEST_RUNNER_DSN  abh_runner role on the same database: everything the runner code does
audit_log is append-only, so each run leaves permanent audit rows; it refuses any other database.
"""

import json
import os
import unittest
import uuid

import psycopg

from core.abh_core.audit import record_hash
from core.abh_core.db import create_pool, transaction
from services.runner import collect, jobs, reconcile
from services.runner.state import Work

DSN_OWNER = os.environ.get("ABH_TEST_OWNER_DSN", "")
DSN_RUNNER = os.environ.get("ABH_TEST_RUNNER_DSN", "")

BODY = ("v", "seq", "ts", "actor_type", "actor_id", "actor_role", "team_id", "action", "target_type", "target_id",
        "outcome", "ip", "request_id", "detail", "prev_hash")


def require_disposable() -> None:
    """Fail loudly (never skip) unless explicitly pointed at a disposable database, as Henil's live suite does."""
    if os.environ.get("ABH_TEST_ALLOW_DISPOSABLE_DB") != "1" or not DSN_OWNER or not DSN_RUNNER:
        raise RuntimeError("set ABH_TEST_ALLOW_DISPOSABLE_DB=1, ABH_TEST_OWNER_DSN and ABH_TEST_RUNNER_DSN")
    names = []
    for dsn in (DSN_OWNER, DSN_RUNNER):
        with psycopg.connect(dsn, autocommit=True) as c:
            names.append(str((c.execute("SELECT current_database()").fetchone() or ("",))[0]))
    if names[0] != names[1] or names[0] == "abhedya" or not ("test" in names[0] or "disposable" in names[0]):
        raise RuntimeError(f"refusing non-disposable or mismatched databases {names!r}")


class PgFixture(unittest.TestCase):
    pool: reconcile.Pool

    @classmethod
    def setUpClass(cls) -> None:
        require_disposable()
        cls.pool = create_pool(DSN_RUNNER, max_size=2)
        cls.team = cls.user = ""
        with psycopg.connect(DSN_OWNER, autocommit=True) as o:
            other = o.execute("SELECT count(*) FROM env WHERE observed_state <> 'destroyed'").fetchone()
            if other is None or other[0] != 0:  # claim() acts on every row; never touch someone else's env
                raise RuntimeError(f"database has {other} live env rows; run only on a disposable database")
            t = o.execute("INSERT INTO team (name) VALUES (%s) RETURNING id::text", (f"t-{uuid.uuid4().hex[:12]}",))
            cls.team = str(t.fetchone()[0])  # type: ignore[index]
            u = o.execute("INSERT INTO app_user (email, password_hash, role, team_id, disabled) VALUES "
                          "(%s, '!test-fixture-no-login', 'analyst', %s, true) RETURNING id::text",
                          (f"{uuid.uuid4().hex[:12]}@runner.test", cls.team))
            cls.user = str(u.fetchone()[0])  # type: ignore[index]

    @classmethod
    def tearDownClass(cls) -> None:
        cls.pool.close()
        with psycopg.connect(DSN_OWNER, autocommit=True) as o:  # retire this run's rows so a re-run may start
            o.execute("UPDATE job SET status = 'error', finished_at = now() WHERE team_id = %s"
                      " AND status IN ('queued', 'running')", (cls.team,))
            o.execute("UPDATE env SET observed_state = 'destroyed', desired_state = 'destroyed' WHERE team_id = %s",
                      (cls.team,))

    def env(self, observed: str, desired: str, minutes: int = 60) -> str:
        with psycopg.connect(DSN_OWNER, autocommit=True) as o:
            r = o.execute(
                "INSERT INTO env (team_id, owner_id, name, template, size, cpu_millis, mem_mb, storage_mb, pids_limit,"
                " observed_state, desired_state, expires_at) VALUES (%s, %s, %s, 'app-target', 'S', 500, 256, 128,"
                " 128, %s, %s, now() + make_interval(mins => %s)) RETURNING id::text",
                (self.team, self.user, f"e-{uuid.uuid4().hex[:12]}", observed, desired, minutes))
            return str(r.fetchone()[0])  # type: ignore[index]

    def row(self, sql: str, *args: object) -> tuple[object, ...]:
        with psycopg.connect(DSN_OWNER, autocommit=True) as o:
            r = o.execute(sql, args).fetchone()
            assert r is not None
            return r



class ReconcileSQL(PgFixture):
    def claimed(self) -> dict[str, reconcile.Claimed]:
        return {c.env.id: c for c in reconcile.claim(self.pool, limit=1000)}

    def test_requested_becomes_provisioning_then_running_with_audit(self) -> None:
        env_id = self.env("requested", "running")
        c = self.claimed()[env_id]
        self.assertEqual((c.observed, c.step.work), ("provisioning", Work.PROVISION))
        self.assertEqual(self.row("SELECT observed_state FROM env WHERE id = %s", env_id), ("provisioning",))
        self.assertEqual(self.row("SELECT count(*) FROM audit_log WHERE target_id = %s", env_id), (0,))
        with transaction(self.pool) as conn:
            self.assertTrue(reconcile.record(conn, c.env, "provisioning", "running", "env.provisioned",
                                             c.step.activity, tier="gvisor", reason=""))
        self.assertEqual(self.row("SELECT observed_state, isolation_tier FROM env WHERE id = %s", env_id),
                         ("running", "gvisor"))
        kinds = self.row("SELECT array_agg(kind ORDER BY id) FROM activity_event WHERE env_id = %s", env_id)
        self.assertEqual(kinds, (["env.state_changed", "env.state_changed"],))
        cols = ", ".join(BODY)
        rec = self.row(f"SELECT {cols}, hash FROM audit_log WHERE target_id = %s", env_id)
        body = dict(zip(BODY, rec[:-1], strict=True))
        self.assertEqual((body["action"], body["actor_type"], body["actor_id"], body["team_id"]),
                         ("env.provisioned", "service", "runner", self.team))
        self.assertEqual(record_hash(body), rec[-1])
        prev = self.row("SELECT hash FROM audit_log WHERE seq = %s", int(str(body["seq"])) - 1)[0] \
            if int(str(body["seq"])) > 1 else "0" * 64
        self.assertEqual(body["prev_hash"], prev)

    def test_stale_write_is_refused_and_not_audited(self) -> None:
        env_id = self.env("running", "running")
        c = reconcile.EnvRow(env_id, self.team, "app-target", 500, 256, 128, 128)
        with transaction(self.pool) as conn:
            self.assertFalse(reconcile.record(conn, c, "provisioning", "running", "env.provisioned",
                                              reconcile.CHANGED))
        self.assertEqual(self.row("SELECT count(*) FROM audit_log WHERE target_id = %s", env_id), (0,))

    def test_selection(self) -> None:
        idle_failed = self.env("failed", "running")
        stopped_wants_running = self.env("stopped", "running")
        converged = self.env("running", "running")
        failed_destroy = self.env("failed", "destroyed")
        expired = self.env("running", "running", minutes=-1)
        to_stop = self.env("running", "stopped")
        got = self.claimed()
        for absent in (idle_failed, stopped_wants_running, converged):
            self.assertNotIn(absent, got)
        self.assertEqual(got[failed_destroy].step.audit_action, "env.destroyed")
        self.assertEqual(got[expired].step.audit_action, "env.expired")
        self.assertEqual(got[to_stop].step.audit_action, "env.stopped")

    def test_skip_locked(self) -> None:
        env_id = self.env("running", "destroyed")
        with psycopg.connect(DSN_OWNER) as other:  # holds the row lock in an open transaction
            other.execute("SELECT 1 FROM env WHERE id = %s FOR UPDATE", (env_id,))
            self.assertNotIn(env_id, self.claimed())
            other.rollback()
        self.assertIn(env_id, self.claimed())

    def test_liveness_query_for_reaper(self) -> None:
        live, stopped = self.env("running", "running"), self.env("stopped", "stopped")
        gone, failed = self.env("destroyed", "destroyed"), self.env("failed", "running")  # failed: retried cleanup
        missing = str(uuid.uuid4())
        with transaction(self.pool) as conn:
            rows = conn.execute(reconcile.LIVE_SQL, ([live, stopped, gone, failed, missing, "not-a-uuid"],)).fetchall()
        self.assertEqual({r[0] for r in rows}, {live, stopped})

    def test_runner_role_grants(self) -> None:
        with psycopg.connect(DSN_RUNNER) as conn:
            with self.assertRaises(psycopg.errors.InsufficientPrivilege):
                conn.execute("INSERT INTO team (name) VALUES ('x-denied')")
            conn.rollback()
            with self.assertRaises(psycopg.errors.InsufficientPrivilege):
                conn.execute("DELETE FROM env")
            conn.rollback()
            with self.assertRaises(psycopg.errors.InsufficientPrivilege):  # no UPDATE grant on audit_log
                conn.execute("UPDATE audit_log SET ip = 'x' WHERE seq = (SELECT max(seq) FROM audit_log)")


class CollectSQL(PgFixture):
    SAMPLE = {"cpu_pct": 12.5, "mem_mb": 240.0, "storage_mb": 3.0, "pids": 4, "net_rx_bytes": 10, "net_tx_bytes": 20}

    def env_row(self, env_id: str) -> reconcile.EnvRow:
        return reconcile.EnvRow(env_id, self.team, "app-target", 500, 256, 128, 128)

    def count(self, sql: str, *args: object) -> int:
        return int(str(self.row(sql, *args)[0]))

    def test_sample_insert_notify_and_prune(self) -> None:
        env_id = self.env("running", "running")
        with psycopg.connect(DSN_OWNER, autocommit=True) as o:
            o.execute("INSERT INTO metric_sample (env_id, ts, cpu_pct, mem_mb, storage_mb, pids, net_rx_bytes,"
                      " net_tx_bytes) VALUES (%s, now() - interval '2 hours', 1, 1, 1, 1, 1, 1)", (env_id,))
            o.execute("LISTEN abh_metric")
            with transaction(self.pool) as conn:
                collect.write_sample(conn, self.env_row(env_id), self.SAMPLE)
            got = [n.payload for n in o.notifies(timeout=5, stop_after=1)]
        data = json.loads(got[0])
        self.assertEqual(data["env_id"], env_id)
        self.assertEqual({k: data[k] for k in self.SAMPLE}, self.SAMPLE)
        self.assertTrue(data["ts"].endswith("Z"))
        with transaction(self.pool) as conn:
            conn.execute(collect.PRUNE_SQL)
        self.assertEqual(self.count("SELECT count(*) FROM metric_sample WHERE env_id = %s", env_id), 1)

    def test_mem_high_once_per_five_minutes(self) -> None:
        env_id = self.env("running", "running")  # 240 of 256 MB is 93.75 %
        raised = []
        for _ in range(4):  # separate transactions: metric_sample's key is (env_id, ts) and now() is per transaction
            with transaction(self.pool) as conn:
                raised.append(collect.write_sample(conn, self.env_row(env_id), self.SAMPLE))
        self.assertEqual(raised, [[], [], ["alert.mem_high"], []])
        self.assertEqual(self.count("SELECT count(*) FROM activity_event WHERE env_id = %s AND kind = 'alert.mem_high'"
                                    " AND severity = 'warn'", env_id), 1)

    def test_oom_audit_and_alert_once(self) -> None:
        env_id = self.env("running", "running")
        self.assertTrue(collect.on_oom(self.pool, env_id, "abh-x-target"))
        self.assertFalse(collect.on_oom(self.pool, env_id, "abh-x-target"))
        self.assertEqual(self.row("SELECT action, outcome, detail FROM audit_log WHERE target_id = %s", env_id),
                         ("env.oom_killed", "success", {"mem_limit_mb": 256}))
        self.assertEqual(self.count("SELECT count(*) FROM activity_event WHERE env_id = %s AND kind ="
                                    " 'alert.oom_killed' AND severity = 'critical'", env_id), 1)
        self.assertFalse(collect.on_oom(self.pool, str(uuid.uuid4()), "abh-x-target"))  # no row: nothing written

    def test_unexpected_die_fails_only_a_running_unexpired_env(self) -> None:
        running = self.env("running", "running")
        self.assertTrue(collect.on_die(self.pool, running, "abh-x-target", "137", True))
        self.assertEqual(self.row("SELECT observed_state FROM env WHERE id = %s", running), ("failed",))
        self.assertEqual(self.row("SELECT action, outcome FROM audit_log WHERE target_id = %s", running),
                         ("env.failed", "error"))
        self.assertFalse(collect.on_die(self.pool, running, "abh-x-target", "137", False))  # replayed event
        for observed, desired, minutes in (("running", "stopped", 60), ("running", "destroyed", 60),
                                           ("running", "running", -1), ("provisioning", "running", 60)):
            env_id = self.env(observed, desired, minutes)
            self.assertFalse(collect.on_die(self.pool, env_id, "abh-x-target", "0", False))
            self.assertEqual(self.row("SELECT observed_state FROM env WHERE id = %s", env_id), (observed,))
        self.assertFalse(collect.on_die(self.pool, str(uuid.uuid4()), "abh-x-target", "0", False))



class JobsSQL(PgFixture):
    def job(self, env_id: str, kind: str = "exec", container: str = "toolbox") -> str:
        with psycopg.connect(DSN_OWNER, autocommit=True) as o:
            r = o.execute("INSERT INTO job (kind, env_id, team_id, requested_by, input) VALUES (%s, %s, %s, %s, %s)"
                          " RETURNING id::text", (kind, env_id, self.team, self.user,
                                                  json.dumps({"command": "id", "container": container})))
            return str(r.fetchone()[0])  # type: ignore[index]

    def drain(self) -> list[jobs.Job]:
        out = []
        while (j := jobs.claim(self.pool)) is not None:
            out.append(j)
        return out

    def test_claim_takes_only_queued_exec_jobs_oldest_first(self) -> None:
        env_id = self.env("running", "running")
        other = self.job(env_id, kind="file_analysis")
        first, second = self.job(env_id), self.job(env_id)
        ids = [j[0] for j in self.drain()]
        self.assertLess(ids.index(first), ids.index(second))
        self.assertNotIn(other, ids)
        self.assertEqual(self.row("SELECT status, started_at IS NOT NULL FROM job WHERE id = %s", first),
                         ("running", True))
        self.assertEqual(self.row("SELECT status FROM job WHERE id = %s", other), ("queued",))

    def test_finish_writes_result_audit_and_activity_once(self) -> None:
        env_id = self.env("running", "running")
        job_id = self.job(env_id)
        self.drain()
        result = {"exit_code": 0, "output": "uid=1000", "truncated": False, "duration_ms": 12}
        with transaction(self.pool) as conn:
            self.assertTrue(jobs.finish(conn, job_id, env_id, self.team, "done", result))
        with transaction(self.pool) as conn:
            self.assertFalse(jobs.finish(conn, job_id, env_id, self.team, "error", {"error": "again"}))
        self.assertEqual(self.row("SELECT status, result, finished_at IS NOT NULL FROM job WHERE id = %s", job_id),
                         ("done", result, True))
        self.assertEqual(self.row("SELECT action, target_type, outcome, actor_id, team_id, detail FROM audit_log"
                                  " WHERE target_id = %s", job_id),
                         ("job.finished", "job", "success", "runner", self.team,
                          {"kind": "exec", "status": "done", "env_id": env_id, "exit_code": 0, "duration_ms": 12,
                           "truncated": False}))
        self.assertEqual(self.row("SELECT count(*) FROM activity_event WHERE env_id = %s AND kind = 'job.finished'",
                                  env_id), (1,))

    def test_run_job_ends_as_error_before_any_docker_call(self) -> None:
        stopped, running = self.env("stopped", "stopped"), self.env("running", "running")
        for env_id, container in ((stopped, "toolbox"), (running, "analyzer")):
            job_id = self.job(env_id, container=container)
            claimed = [j for j in self.drain() if j[0] == job_id]
            self.assertEqual(jobs.run_job(self.pool, None, claimed[0]), "error")  # api=None: never reached
            status, result = self.row("SELECT status, result FROM job WHERE id = %s", job_id)
            self.assertEqual(status, "error")
            self.assertIn("ValueError", str(result))

    def test_recover_orphans_ends_running_jobs_with_audit(self) -> None:
        env_id = self.env("running", "running")
        job_id = self.job(env_id)
        self.drain()
        self.assertGreaterEqual(jobs.recover_orphans(self.pool), 1)
        self.assertEqual(self.row("SELECT status FROM job WHERE id = %s", job_id), ("error",))
        self.assertEqual(self.row("SELECT action, outcome FROM audit_log WHERE target_id = %s", job_id),
                         ("job.finished", "error"))

if __name__ == "__main__":
    unittest.main()
