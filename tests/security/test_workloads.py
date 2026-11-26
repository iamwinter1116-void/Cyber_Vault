"""Workload security tests: T-WL-01..03 (docs/06_VERIFICATION.md section 8)."""
from __future__ import annotations

import hashlib
import time

from .conftest import API_BASE, create_env_and_wait, docker_managed_inspect, exec_in_env, login_as

EICAR_BYTES = rb"X5O!P%@AP[4\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*"


def _wait_job(client, job_id: str, timeout_s: float = 150.0) -> dict:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        r = client.get(f"{API_BASE}/jobs/{job_id}")
        assert r.status_code == 200
        if r.json()["status"] in ("done", "timeout", "error"):
            return r.json()
        time.sleep(1.0)
    raise AssertionError(f"Job {job_id} did not complete within {timeout_s}s")


def test_t_wl_01_app_target_connectivity_and_isolation(stack_url: str) -> None:
    """T-WL-01: toolbox reaches target home page HTTP 200; isolated from another env."""
    ca, csrfa = login_as(stack_url, "analyst.alpha@abhedya.local")
    cb, csrfb = login_as(stack_url, "analyst.bravo@abhedya.local")
    env_a = create_env_and_wait(ca, csrfa, "wl-01-alpha")
    env_b = create_env_and_wait(cb, csrfb, "wl-01-bravo")
    ok = exec_in_env(ca, csrfa, env_a["id"], "curl -s -o /dev/null -w '%{http_code}' http://target:8080/")
    assert "200" in ok["result"]["output"]
    blocked = exec_in_env(cb, csrfb, env_b["id"], "probe_connect target 8080 3")
    assert '"reachable": false' in blocked["result"]["output"].lower()


def test_t_wl_02_file_analysis_eicar_benign_and_cleanup(stack_url: str) -> None:
    """T-WL-02: EICAR -> malicious, benign -> clean, no leftover containers/networks/volumes."""
    ca, csrfa = login_as(stack_url, "analyst.alpha@abhedya.local")
    r_mal = ca.post(
        f"{API_BASE}/files",
        headers={"X-CSRF-Token": csrfa},
        files={"file": ("eicar.txt", EICAR_BYTES, "text/plain")},
        data={"detonate": "false"},
    )
    assert r_mal.status_code == 202
    j_mal = _wait_job(ca, r_mal.json()["id"])
    assert j_mal["result"]["verdict"] == "malicious" and j_mal["result"]["yara_matches"]

    r_ben = ca.post(
        f"{API_BASE}/files",
        headers={"X-CSRF-Token": csrfa},
        files={"file": ("benign.txt", b"hello abhedya", "text/plain")},
        data={"detonate": "false"},
    )
    assert r_ben.status_code == 202
    j_ben = _wait_job(ca, r_ben.json()["id"])
    assert j_ben["result"]["verdict"] == "clean"
    leaked = [c for c in docker_managed_inspect() if c["Config"]["Labels"].get("abh.env_id") in (j_mal["env_id"], j_ben["env_id"])]
    assert not leaked


def test_t_wl_03_ai_scan_vulnerable_vs_guarded_offline(stack_url: str) -> None:
    """T-WL-03: quick scan finds >0 failures on stub-vulnerable and strictly fewer on stub-guarded."""
    ca, csrfa = login_as(stack_url, "analyst.alpha@abhedya.local")
    rv = ca.post(f"{API_BASE}/ai-scans", headers={"X-CSRF-Token": csrfa}, json={"target": "stub-vulnerable", "probe_set": "quick"})
    rg = ca.post(f"{API_BASE}/ai-scans", headers={"X-CSRF-Token": csrfa}, json={"target": "stub-guarded", "probe_set": "quick"})
    assert rv.status_code == 202 and rg.status_code == 202
    jv = _wait_job(ca, rv.json()["id"], timeout_s=180.0)
    jg = _wait_job(ca, rg.json()["id"], timeout_s=180.0)
    assert jv["status"] == "done" and jg["status"] == "done"
    assert jv["result"]["failures"] > 0 and jg["result"]["failures"] < jv["result"]["failures"]
    for p in jv["result"]["probes"]:
        assert p["owasp_llm"].startswith("LLM")
    assert len(jv["result"]["report_sha256"]) == 64
    assert hashlib.sha256(b"").hexdigest() != jv["result"]["report_sha256"]
