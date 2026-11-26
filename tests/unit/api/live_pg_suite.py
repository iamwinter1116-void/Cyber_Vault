"""Live PostgreSQL regression suite (run explicitly against a fresh disposable DB).

Required environment variables:
  ABH_TEST_ALLOW_DISPOSABLE_DB=1
  ABH_TEST_OWNER_DSN=postgresql://postgres:<pw>@<host>:<port>/<disposable_db>
  ABH_TEST_API_DSN=postgresql://abh_api:<pw>@<host>:<port>/<disposable_db>
  ABH_TEST_NOTARY_DSN=postgresql://abh_notary:<pw>@<host>:<port>/<disposable_db>
"""

from __future__ import annotations

import os
import uuid
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

_SCHEMA_PATH = Path(__file__).resolve().parents[3] / "contracts" / "schema.sql"


def _require_disposable_dsns() -> tuple[str, str, str]:
    if os.environ.get("ABH_TEST_ALLOW_DISPOSABLE_DB") != "1":
        pytest.fail("Set ABH_TEST_ALLOW_DISPOSABLE_DB=1 to run against a disposable test database")
    owner_dsn = os.environ.get("ABH_TEST_OWNER_DSN", "")
    api_dsn = os.environ.get("ABH_TEST_API_DSN", "")
    notary_dsn = os.environ.get("ABH_TEST_NOTARY_DSN", "")
    if not owner_dsn or not api_dsn or not notary_dsn:
        pytest.fail("ABH_TEST_OWNER_DSN, ABH_TEST_API_DSN, and ABH_TEST_NOTARY_DSN must all be set")

    with psycopg.connect(owner_dsn, autocommit=True) as conn, conn.cursor() as cur:
        cur.execute("SELECT current_database()")
        db_name = str((cur.fetchone() or ("",))[0])
        if db_name == "abhedya" or ("test" not in db_name and "disposable" not in db_name):
            pytest.fail(f"Refusing to run against non-disposable database {db_name!r}; name must include 'test' or 'disposable'")
        cur.execute("SELECT to_regclass('public.audit_log')")
        if (cur.fetchone() or (None,))[0] is None:
            cur.execute(_SCHEMA_PATH.read_text(encoding="utf-8"))

    for dsn, expected_role in ((api_dsn, "abh_api"), (notary_dsn, "abh_notary")):
        with psycopg.connect(dsn) as conn, conn.cursor() as cur:
            cur.execute("SELECT current_user")
            role = str((cur.fetchone() or ("",))[0])
            if role != expected_role:
                pytest.fail(f"Expected role {expected_role!r}, got {role!r}")

    return owner_dsn, api_dsn, notary_dsn


def test_pg_denied_login_lockout_quota_and_notary(tmp_path: Path) -> None:
    owner_dsn, api_dsn, notary_dsn = _require_disposable_dsns()
    tag = uuid.uuid4().hex[:8]
    email = f"analyst.{tag}@abhedya.local"
    pw = "Correct-Horse-123!"

    with psycopg.connect(owner_dsn, autocommit=True) as conn, conn.cursor() as cur:
        cur.execute("INSERT INTO team (name, quota_envs) VALUES (%s, 1) RETURNING id", (f"t-{tag}",))
        team_id = cast(UUID, (cur.fetchone() or (None,))[0])
        cur.execute(
            "INSERT INTO app_user (email, password_hash, role, team_id) VALUES (%s, %s, 'analyst', %s)",
            (email, hash_password(pw), team_id),
        )
        cur.execute("SELECT COALESCE(max(seq), 0) FROM audit_log")
        base_seq = int(cast(int, (cur.fetchone() or (0,))[0]))

    app = create_app(Settings(db_dsn=api_dsn, witness_path=str(tmp_path / "witness.ndjson")))
    with TestClient(app) as client:
        # 1. Unknown email -> 401 AND denied audit row committed as abh_api
        r_unknown = client.post("/api/v1/auth/login", json={"email": f"nobody.{tag}@abhedya.local", "password": "wrong"})
        assert r_unknown.status_code == 401
        with psycopg.connect(api_dsn) as conn, conn.cursor() as cur:
            cur.execute("SELECT seq, action, outcome, detail->>'reason' FROM audit_log WHERE seq > %s ORDER BY seq DESC LIMIT 1", (base_seq,))
            row = cur.fetchone()
            assert row is not None and row[1:] == ("auth.login", "denied", "invalid_credentials")

        # 2. Five wrong passwords -> 401 x4, then 403 ACCOUNT_LOCKED + auth.lockout + alert.login_bruteforce
        for i in range(4):
            assert client.post("/api/v1/auth/login", json={"email": email, "password": f"bad-{i}"}).status_code == 401
        r_lock = client.post("/api/v1/auth/login", json={"email": email, "password": "bad-4"})
        assert r_lock.status_code == 403
        assert r_lock.json()["error"]["code"] == "ACCOUNT_LOCKED"

        with psycopg.connect(api_dsn) as conn, conn.cursor() as cur:
            cur.execute("SELECT failed_logins, locked_until > now() FROM app_user WHERE email = %s", (email,))
            assert cur.fetchone() == (5, True)
            cur.execute("SELECT action, outcome FROM audit_log ORDER BY seq DESC LIMIT 1")
            assert cur.fetchone() == ("auth.lockout", "denied")
            cur.execute("SELECT kind FROM activity_event ORDER BY id DESC LIMIT 1")
            assert cur.fetchone() == ("alert.login_bruteforce",)

        # 3. Reset lock as owner, valid login -> cookie + CSRF + me + quota + logout
        with psycopg.connect(owner_dsn, autocommit=True) as conn, conn.cursor() as cur:
            cur.execute("UPDATE app_user SET failed_logins = 0, locked_until = NULL WHERE email = %s", (email,))

        r_ok = client.post("/api/v1/auth/login", json={"email": email, "password": pw})
        assert r_ok.status_code == 200
        csrf = r_ok.json()["csrf_token"]
        assert "abh_session" in client.cookies
        assert client.get("/api/v1/auth/me").status_code == 200
        assert client.post("/api/v1/envs", json={"name": f"e1-{tag}", "template": "app-target", "size": "S"}).status_code == 403

        r_env1 = client.post("/api/v1/envs", headers={"X-CSRF-Token": csrf}, json={"name": f"e1-{tag}", "template": "app-target", "size": "S"})
        assert r_env1.status_code == 201
        r_env2 = client.post("/api/v1/envs", headers={"X-CSRF-Token": csrf}, json={"name": f"e2-{tag}", "template": "app-target", "size": "S"})
        assert r_env2.status_code == 409
        assert r_env2.json()["error"]["code"] == "QUOTA_EXCEEDED"

        assert client.post("/api/v1/auth/logout", headers={"X-CSRF-Token": csrf}).status_code == 204
        assert client.get("/api/v1/auth/me").status_code == 401

        # 4. Notary tick as abh_notary creates checkpoint + witness file
        key = Ed25519PrivateKey.generate()
        witness = tmp_path / "witness.ndjson"
        with psycopg.connect(notary_dsn) as conn, conn.transaction():
            ok, _ = run_tick(conn, key, "0" * 16, witness, every_n=1, every_sec=1, last_cp_monotonic=0.0)
            assert ok is True
        assert witness.exists() and len(witness.read_text(encoding="utf-8").splitlines()) == 1
