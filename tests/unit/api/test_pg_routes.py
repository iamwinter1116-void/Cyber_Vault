"""Real PostgreSQL regression tests for auth (denied/lockout commit), RBAC, quota, and notary."""

from __future__ import annotations

import os
from pathlib import Path
from typing import cast
from uuid import UUID

import psycopg
import pytest
from core.abh_core.settings import Settings
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from fastapi.testclient import TestClient
from services.api.main import create_app
from services.api.security import hash_password
from services.notary.__main__ import run_tick


def _pg_dsn() -> str:
    dsn = os.environ.get("ABH_DB_DSN", "")
    if not dsn:
        pytest.skip("ABH_DB_DSN not set (requires live PostgreSQL)")
    return dsn


def _reset_and_seed(dsn: str) -> tuple[UUID, str]:
    with psycopg.connect(dsn, autocommit=True) as conn, conn.cursor() as cur:
        cur.execute("TRUNCATE session, job, metric_sample, activity_event, env, app_user, team CASCADE")
        cur.execute("ALTER TABLE audit_log DISABLE TRIGGER audit_no_update_delete, audit_no_truncate")
        cur.execute("TRUNCATE audit_log, audit_checkpoint")
        cur.execute("ALTER TABLE audit_log ENABLE TRIGGER audit_no_update_delete, audit_no_truncate")
        cur.execute("INSERT INTO team (name, quota_envs) VALUES ('alpha', 1) RETURNING id")
        team_row = cur.fetchone()
        assert team_row is not None
        team_id = cast(UUID, team_row[0])
        pw = "Correct-Horse-123!"
        cur.execute(
            "INSERT INTO app_user (email, password_hash, role, team_id) VALUES (%s, %s, 'analyst', %s)",
            ("analyst.alpha@abhedya.local", hash_password(pw), team_id),
        )
    return team_id, pw


def test_pg_denied_login_lockout_and_session_lifecycle(tmp_path: Path) -> None:
    dsn = _pg_dsn()
    _team_id, pw = _reset_and_seed(dsn)
    app = create_app(Settings(db_dsn=dsn, witness_path=str(tmp_path / "witness.ndjson")))

    with TestClient(app) as client:
        # 1. Unknown email -> 401 AND denied audit row persisted
        r_unknown = client.post("/api/v1/auth/login", json={"email": "nobody@abhedya.local", "password": "wrong"})
        assert r_unknown.status_code == 401
        with psycopg.connect(dsn) as conn, conn.cursor() as cur:
            cur.execute("SELECT action, outcome, detail->>'reason' FROM audit_log ORDER BY seq DESC LIMIT 1")
            assert cur.fetchone() == ("auth.login", "denied", "invalid_credentials")

        # 2. Five wrong passwords -> 401 x4 then 403 ACCOUNT_LOCKED + alert.login_bruteforce
        for i in range(4):
            r_bad = client.post("/api/v1/auth/login", json={"email": "analyst.alpha@abhedya.local", "password": f"bad-{i}"})
            assert r_bad.status_code == 401
        r_lock = client.post("/api/v1/auth/login", json={"email": "analyst.alpha@abhedya.local", "password": "bad-4"})
        assert r_lock.status_code == 403
        assert r_lock.json()["error"]["code"] == "ACCOUNT_LOCKED"

        with psycopg.connect(dsn) as conn, conn.cursor() as cur:
            cur.execute("SELECT failed_logins, locked_until > now() FROM app_user WHERE email = 'analyst.alpha@abhedya.local'")
            assert cur.fetchone() == (5, True)
            cur.execute("SELECT action, outcome FROM audit_log ORDER BY seq DESC LIMIT 1")
            assert cur.fetchone() == ("auth.lockout", "denied")
            cur.execute("SELECT kind FROM activity_event ORDER BY id DESC LIMIT 1")
            assert cur.fetchone() == ("alert.login_bruteforce",)

        # 3. Reset lock, valid login -> cookie + CSRF + me + quota + logout
        with psycopg.connect(dsn, autocommit=True) as conn, conn.cursor() as cur:
            cur.execute("UPDATE app_user SET failed_logins = 0, locked_until = NULL")

        r_ok = client.post("/api/v1/auth/login", json={"email": "analyst.alpha@abhedya.local", "password": pw})
        assert r_ok.status_code == 200
        csrf = r_ok.json()["csrf_token"]
        assert "abh_session" in client.cookies

        assert client.get("/api/v1/auth/me").status_code == 200
        assert client.post("/api/v1/envs", json={"name": "lab-1", "template": "app-target", "size": "S"}).status_code == 403

        r_env1 = client.post(
            "/api/v1/envs",
            headers={"X-CSRF-Token": csrf},
            json={"name": "lab-1", "template": "app-target", "size": "S"},
        )
        assert r_env1.status_code == 201
        r_env2 = client.post(
            "/api/v1/envs",
            headers={"X-CSRF-Token": csrf},
            json={"name": "lab-2", "template": "app-target", "size": "S"},
        )
        assert r_env2.status_code == 409
        assert r_env2.json()["error"]["code"] == "QUOTA_EXCEEDED"

        assert client.post("/api/v1/auth/logout", headers={"X-CSRF-Token": csrf}).status_code == 204
        assert client.get("/api/v1/auth/me").status_code == 401

        # 4. Notary tick creates checkpoint + witness file
        key = Ed25519PrivateKey.generate()
        witness = tmp_path / "witness.ndjson"
        with psycopg.connect(dsn) as conn, conn.transaction():
            ok, _ = run_tick(conn, key, "0" * 16, witness, every_n=1, every_sec=1, last_cp_monotonic=0.0)
            assert ok is True
        assert witness.exists() and len(witness.read_text(encoding="utf-8").splitlines()) == 1
