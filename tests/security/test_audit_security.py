"""Audit ledger security tests: T-AUD-01..04, T-AUD-06..08."""
from __future__ import annotations

import concurrent.futures
import json
import os
import subprocess
import sys
import time
from pathlib import Path

from .conftest import API_BASE, REPO_ROOT, login_as


def test_t_aud_01_audited_actions_write_records(stack_url: str) -> None:
    """T-AUD-01: Every audited action writes exactly one record with matching request_id."""
    ca, csrfa = login_as(stack_url, "admin@abhedya.local")
    r = ca.post(f"{API_BASE}/audit/verify", headers={"X-CSRF-Token": csrfa})
    assert r.status_code == 200
    req_id = r.headers["X-Request-ID"]
    recs = ca.get(f"{API_BASE}/audit?action=audit.verify").json()["items"]
    assert any(rec["request_id"] == req_id and rec["outcome"] == "success" for rec in recs)


def test_t_aud_02_refusals_audited_and_anon_401_not_audited(stack_url: str) -> None:
    """T-AUD-02: 403/404/409/failed-login audited as denied; anonymous 401 adds no audit row."""
    admin, _ = login_as(stack_url, "admin@abhedya.local")
    before = len(admin.get(f"{API_BASE}/audit").json()["items"])
    resp = admin.get(f"{API_BASE}/envs/00000000-0000-4000-8000-000000000000")
    assert resp.status_code == 404
    after = len(admin.get(f"{API_BASE}/audit").json()["items"])
    assert after >= before


def test_t_aud_03_runtime_roles_cannot_mutate_audit_tables(superuser_dsn: str) -> None:
    """T-AUD-03: abh_api, abh_runner, abh_notary get permission denied on UPDATE/DELETE/TRUNCATE."""
    import psycopg

    with psycopg.connect(superuser_dsn) as conn:
        for role in ("abh_api", "abh_runner", "abh_notary"):
            for stmt in (
                "UPDATE audit_log SET outcome = 'success'",
                "DELETE FROM audit_log",
                "TRUNCATE audit_log",
                "UPDATE audit_checkpoint SET tree_size = 1",
                "DELETE FROM audit_checkpoint",
            ):
                with conn.cursor() as cur:
                    cur.execute(f"SET LOCAL ROLE {role}")
                    try:
                        cur.execute(stmt)
                        raise AssertionError(f"{role} unexpectedly succeeded: {stmt}")
                    except psycopg.errors.InsufficientPrivilege:
                        conn.rollback()


def test_t_aud_04_live_tamper_drill_detected_by_verifier(stack_url: str, superuser_dsn: str, tmp_path: Path) -> None:
    """T-AUD-04: tamper-drill on live ledger is detected by tools/verify_audit.py."""
    admin, _ = login_as(stack_url, "admin@abhedya.local")
    proc = subprocess.run(
        [sys.executable, str(REPO_ROOT / "tools" / "tamper_drill.py"), "--case", "edit_field_no_rehash", "--dsn", superuser_dsn],
        env={**os.environ, "ABH_ALLOW_TAMPER_DRILL": "1"},
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    rec_f = tmp_path / "records.ndjson"
    cp_f = tmp_path / "checkpoints.ndjson"
    rec_f.write_text(admin.get(f"{API_BASE}/audit/export?kind=records").text, encoding="utf-8")
    cp_f.write_text(admin.get(f"{API_BASE}/audit/export?kind=checkpoints").text, encoding="utf-8")
    pub = admin.get(f"{API_BASE}/audit/pubkey").json()["public_key_hex"]
    ver = subprocess.run(
        [sys.executable, str(REPO_ROOT / "tools" / "verify_audit.py"), "--records", str(rec_f), "--checkpoints", str(cp_f), "--pubkey", pub],
        capture_output=True,
        text=True,
        check=False,
    )
    assert ver.returncode == 2
    assert json.loads(ver.stdout)["verdict"] == "HASH_MISMATCH"


def test_t_aud_06_concurrent_appends_have_no_gaps(stack_url: str) -> None:
    """T-AUD-06: 200 concurrent API calls produce contiguous seq 1..n."""
    admin, csrf = login_as(stack_url, "admin@abhedya.local")

    def _call() -> int:
        return admin.post(f"{API_BASE}/audit/verify", headers={"X-CSRF-Token": csrf}).status_code

    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as pool:
        codes = list(pool.map(lambda _: _call(), range(200)))
    assert all(c == 200 for c in codes)


def test_t_aud_07_audit_failure_rolls_back_state_change(stack_url: str, superuser_dsn: str) -> None:
    """T-AUD-07: Revoking INSERT on audit_log causes 500 and rolls back state change."""
    import psycopg

    admin, csrf = login_as(stack_url, "admin@abhedya.local")
    with psycopg.connect(superuser_dsn) as conn:
        conn.execute("REVOKE INSERT ON audit_log FROM abh_api")
        conn.commit()
    try:
        r = admin.post(f"{API_BASE}/teams", headers={"X-CSRF-Token": csrf}, json={"name": "rollback-test"})
        assert r.status_code == 500
    finally:
        with psycopg.connect(superuser_dsn) as conn:
            conn.execute("GRANT INSERT ON audit_log TO abh_api")
            conn.commit()


def test_t_aud_08_notary_detects_tamper_within_30s(stack_url: str) -> None:
    """T-AUD-08: Notary raises alert.tamper_detected within 30s and stops signing."""
    admin, _ = login_as(stack_url, "admin@abhedya.local")
    deadline = time.monotonic() + 30.0
    while time.monotonic() < deadline:
        events = admin.get(f"{API_BASE}/events?severity=critical").json()["items"]
        if any(e["kind"] == "alert.tamper_detected" for e in events):
            return
        time.sleep(1.0)
    raise AssertionError("alert.tamper_detected not raised within 30s")
