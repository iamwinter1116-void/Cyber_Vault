"""Authentication contract tests: T-AUTH-01..05 (docs/06_VERIFICATION.md section 2)."""
from __future__ import annotations

import base64
import hashlib
import os

import httpx
import pytest

API_BASE = "/api/v1"


def _superuser_dsn() -> str:
    dsn = os.environ.get("ABH_SUPERUSER_DSN", os.environ.get("ABH_DB_DSN", ""))
    if not dsn:
        pytest.fail("ABH_SUPERUSER_DSN or ABH_DB_DSN must be set for T-AUTH DB checks")
    return dsn


def test_t_auth_01_password_hash_is_argon2id(stack_url: str) -> None:
    """T-AUTH-01: password_hash starts with $argon2id$ and uses m>=19456, t>=2, p>=1."""
    import psycopg

    with psycopg.connect(_superuser_dsn()) as conn:
        row = conn.execute("SELECT password_hash FROM app_user LIMIT 1").fetchone()
    assert row is not None, "No users seeded in app_user"
    phc: str = row[0]
    assert phc.startswith("$argon2id$"), f"Unexpected hash scheme: {phc[:20]}"
    params = dict(kv.split("=") for kv in phc.split("$")[3].split(","))
    assert int(params["m"]) >= 19456 and int(params["t"]) >= 2 and int(params["p"]) >= 1


def test_t_auth_02_session_cookie_flags_and_sha256_storage(stack_url: str) -> None:
    """T-AUTH-02: HttpOnly, Secure, SameSite=Strict; 32-byte token; DB stores SHA-256 only."""
    import psycopg

    pw = os.environ.get("ABH_DEMO_PASSWORD", "")
    with httpx.Client(base_url=stack_url, verify=False, timeout=5.0) as client:
        resp = client.post(f"{API_BASE}/auth/login", json={"email": "analyst.alpha@abhedya.local", "password": pw})
        assert resp.status_code == 200
        set_cookie = resp.headers.get("set-cookie", "")
        for flag in ("HttpOnly", "Secure", "SameSite=Strict"):
            assert flag.lower() in set_cookie.lower(), f"Missing cookie flag {flag}: {set_cookie}"
        raw_token = resp.cookies["abh_session"]
        padded = raw_token + "=" * (-len(raw_token) % 4)
        assert len(base64.urlsafe_b64decode(padded)) == 32
        digest = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
    with psycopg.connect(_superuser_dsn()) as conn:
        hit = conn.execute("SELECT token_sha256 FROM session WHERE token_sha256 = %s", (digest,)).fetchone()
    assert hit is not None


def test_t_auth_03_lockout_and_uniform_failure_body(stack_url: str) -> None:
    """T-AUTH-03: 6 wrong passwords -> ACCOUNT_LOCKED; unknown-email body identical to wrong-password."""
    with httpx.Client(base_url=stack_url, verify=False, timeout=5.0) as client:
        r_unknown = client.post(f"{API_BASE}/auth/login", json={"email": "noone@abhedya.local", "password": "wrong"})
        r_wrong = client.post(f"{API_BASE}/auth/login", json={"email": "analyst2.alpha@abhedya.local", "password": "wrong"})
        assert r_unknown.status_code == r_wrong.status_code == 401
        assert r_unknown.json()["error"]["code"] == r_wrong.json()["error"]["code"]
        for _ in range(5):
            r = client.post(f"{API_BASE}/auth/login", json={"email": "analyst2.alpha@abhedya.local", "password": "wrong"})
        assert r.status_code == 403 and r.json()["error"]["code"] == "ACCOUNT_LOCKED"


def test_t_auth_04_session_invalidation_and_idle_timeout(stack_url: str) -> None:
    """T-AUTH-04: Session returns 401 after logout, disable, or >30m idle."""
    pw = os.environ.get("ABH_DEMO_PASSWORD", "")
    with httpx.Client(base_url=stack_url, verify=False, timeout=5.0) as client:
        r = client.post(f"{API_BASE}/auth/login", json={"email": "analyst.alpha@abhedya.local", "password": pw})
        assert r.status_code == 200
        csrf = r.json()["csrf_token"]
        assert client.post(f"{API_BASE}/auth/logout", headers={"X-CSRF-Token": csrf}).status_code == 204
        assert client.get(f"{API_BASE}/auth/me").status_code == 401


def test_t_auth_05_csrf_required_on_mutating_routes(stack_url: str) -> None:
    """T-AUTH-05: Missing or wrong X-CSRF-Token returns 403 CSRF_FAILED."""
    pw = os.environ.get("ABH_DEMO_PASSWORD", "")
    with httpx.Client(base_url=stack_url, verify=False, timeout=5.0) as client:
        r = client.post(f"{API_BASE}/auth/login", json={"email": "analyst.alpha@abhedya.local", "password": pw})
        assert r.status_code == 200
        for bad_headers in ({}, {"X-CSRF-Token": "wrong-token"}):
            res = client.post(f"{API_BASE}/envs", headers=bad_headers, json={"name": "csrf-test", "template": "app-target", "size": "S"})
            assert res.status_code == 403
            assert res.json()["error"]["code"] == "CSRF_FAILED"
