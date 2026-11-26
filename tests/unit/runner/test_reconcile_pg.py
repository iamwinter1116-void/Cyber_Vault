"""Reconciler SQL against real PostgreSQL with contracts/schema.sql applied. No Docker is involved or replaced:
only claim(), record() and the reaper's liveness query run here; apply() and reap() need the Linux host.

Needs psycopg, psycopg-pool, pydantic-settings and core.abh_core (Henil's branch) importable, and:
  ABH_TEST_OWNER_DSN   owner role: inserts the team/user/env fixtures the runner role may not insert
  ABH_TEST_RUNNER_DSN  abh_runner role: everything the runner code does
WARNING: audit_log is append-only, so each run leaves permanent env.* audit rows. Use a disposable database.
"""

import os
import unittest
import uuid

DSN_OWNER = os.environ.get("ABH_TEST_OWNER_DSN", "")
DSN_RUNNER = os.environ.get("ABH_TEST_RUNNER_DSN", "")
if not DSN_OWNER or not DSN_RUNNER:
    raise RuntimeError("set ABH_TEST_OWNER_DSN and ABH_TEST_RUNNER_DSN; this test is not skipped silently")

import psycopg  # noqa: E402
from core.abh_core.audit import record_hash  # noqa: E402
from core.abh_core.db import create_pool, transaction  # noqa: E402
from services.runner import reconcile  # noqa: E402
from services.runner.state import Work  # noqa: E402

BODY = ("v", "seq", "ts", "actor_type", "actor_id", "actor_role", "team_id", "action", "target_type", "target_id",
        "outcome", "ip", "request_id", "detail", "prev_hash")


class ReconcileSQL(unittest.TestCase):
    pool: reconcile.Pool

    @classmethod
    def setUpClass(cls) -> None:
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
        live, gone = self.env("running", "running"), self.env("destroyed", "destroyed")
        missing = str(uuid.uuid4())
        with transaction(self.pool) as conn:
            rows = conn.execute(reconcile.LIVE_SQL, ([live, gone, missing, "not-a-uuid"],)).fetchall()
        self.assertEqual({r[0] for r in rows}, {live})

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


if __name__ == "__main__":
    unittest.main()
