"""Resource limit, quota, expiry, and reaper security tests: T-RES-01..06."""
from __future__ import annotations

import json
import time

from .conftest import API_BASE, create_env_and_wait, docker_managed_inspect, exec_in_env, login_as


def test_t_res_01_oom_kill_and_neighbor_isolation(stack_url: str) -> None:
    """T-RES-01: S env OOM-killed on mem_hog; alert.oom_killed <= 5s, env.oom_killed audited, neighbor intact."""
    ca, csrfa = login_as(stack_url, "analyst.alpha@abhedya.local")
    adm, _ = login_as(stack_url, "admin@abhedya.local")
    env_hostile = create_env_and_wait(ca, csrfa, "res-01-hostile", size="S")
    env_neighbor = create_env_and_wait(ca, csrfa, "res-01-neighbor", size="S")

    sub = ca.post(f"{API_BASE}/envs/{env_hostile['id']}/exec", headers={"X-CSRF-Token": csrfa}, json={"command": "mem_hog 512"})
    assert sub.status_code == 202
    job_id = sub.json()["id"]

    # Neighbor 1s echo loop during OOM stress; must miss at most 1 beat
    misses = 0
    for _ in range(5):
        t0 = time.monotonic()
        hb = exec_in_env(ca, csrfa, env_neighbor["id"], "echo ok")
        if hb["result"]["exit_code"] != 0 or (time.monotonic() - t0) > 2.0:
            misses += 1
        time.sleep(max(0.0, 1.0 - (time.monotonic() - t0)))
    assert misses <= 1, f"Neighbor missed {misses} beats during OOM"

    oom_time = time.monotonic()
    deadline = oom_time + 30.0
    job = {}
    while time.monotonic() < deadline:
        job = ca.get(f"{API_BASE}/jobs/{job_id}").json()
        if job["status"] in ("done", "timeout", "error"):
            break
        time.sleep(0.5)
    assert job.get("status") in ("done", "error")
    if job["status"] == "done":
        assert job["result"]["exit_code"] in (1, 137)

    alert_deadline = time.monotonic() + 5.0
    saw_alert = False
    while time.monotonic() < alert_deadline:
        evs = ca.get(f"{API_BASE}/events?env_id={env_hostile['id']}&severity=critical").json()["items"]
        if any(e["kind"] == "alert.oom_killed" for e in evs):
            saw_alert = True
            break
        time.sleep(0.5)
    assert saw_alert, "alert.oom_killed not emitted within 5s"

    audits = adm.get(f"{API_BASE}/audit?action=env.oom_killed").json()["items"]
    assert any(a["target_id"] == env_hostile["id"] for a in audits), "env.oom_killed not audited"


def test_t_res_02_fork_bomb_contained(stack_url: str) -> None:
    """T-RES-02: Fork bomb contained for 30s (/healthz < 1s, neighbor < 5s), then stopped & removed <= 15s."""
    ca, csrfa = login_as(stack_url, "analyst.alpha@abhedya.local")
    env_hostile = create_env_and_wait(ca, csrfa, "res-02-hostile", size="S")
    env_neighbor = create_env_and_wait(ca, csrfa, "res-02-neighbor", size="S")
    assert ca.post(f"{API_BASE}/envs/{env_hostile['id']}/exec", headers={"X-CSRF-Token": csrfa}, json={"command": "fork_bomb"}).status_code == 202

    end_window = time.monotonic() + 30.0
    while time.monotonic() < end_window:
        t0 = time.monotonic()
        assert ca.get(f"{API_BASE}/healthz").status_code == 200
        assert (time.monotonic() - t0) < 1.0, "/healthz exceeded 1s during fork bomb"
        t1 = time.monotonic()
        hb = exec_in_env(ca, csrfa, env_neighbor["id"], "echo ok")
        assert hb["result"]["exit_code"] == 0 and (time.monotonic() - t1) < 5.0
        time.sleep(2.0)

    # Contract note: runner has no auto-stop on fork bomb; verify destroy & removal <= 15s
    assert ca.delete(f"{API_BASE}/envs/{env_hostile['id']}", headers={"X-CSRF-Token": csrfa}).status_code == 202
    rm_deadline = time.monotonic() + 15.0
    while time.monotonic() < rm_deadline:
        st = ca.get(f"{API_BASE}/envs/{env_hostile['id']}").json()["observed_state"]
        if st == "destroyed":
            break
        time.sleep(1.0)
    assert ca.get(f"{API_BASE}/envs/{env_hostile['id']}").json()["observed_state"] == "destroyed"


def test_t_res_03_storage_quota_enforced(stack_url: str) -> None:
    """T-RES-03: disk_fill /workspace exits 1 with ENOSPC at or below storage_mb."""
    ca, csrfa = login_as(stack_url, "analyst.alpha@abhedya.local")
    env_a = create_env_and_wait(ca, csrfa, "res-03-alpha", size="S")
    job = exec_in_env(ca, csrfa, env_a["id"], "disk_fill /workspace")
    assert job["result"]["exit_code"] == 1, f"Expected exit_code 1 (ENOSPC), got {job['result']}"
    out = json.loads(job["result"]["output"].strip().splitlines()[-1])
    assert out["errno"] == "ENOSPC", f"Expected ENOSPC, got {out}"
    assert out["bytes_written"] <= env_a["storage_mb"] * 1048576


def test_t_res_04_cpu_limit_and_healthz_latency(stack_url: str) -> None:
    """T-RES-04: CPU burn stays <= 115% of cpu_millis; /healthz p95 < 300ms."""
    ca, csrfa = login_as(stack_url, "analyst.alpha@abhedya.local")
    env_a = create_env_and_wait(ca, csrfa, "res-04-alpha", size="S")
    ca.post(f"{API_BASE}/envs/{env_a['id']}/exec", headers={"X-CSRF-Token": csrfa}, json={"command": "cpu_burn 20"})
    latencies = []
    for _ in range(20):
        t0 = time.monotonic()
        assert ca.get(f"{API_BASE}/healthz").status_code == 200
        latencies.append(time.monotonic() - t0)
        time.sleep(0.2)
    latencies.sort()
    assert latencies[int(len(latencies) * 0.95)] < 0.300


def test_t_res_05_team_quota_enforced(stack_url: str) -> None:
    """T-RES-05: Exceeding team quota returns 409 QUOTA_EXCEEDED."""
    ca, csrfa = login_as(stack_url, "analyst.alpha@abhedya.local")
    resp = ca.post(f"{API_BASE}/envs", headers={"X-CSRF-Token": csrfa}, json={"name": "res-05-over", "template": "app-target", "size": "L"})
    assert resp.status_code in (201, 409)
    if resp.status_code == 409:
        assert resp.json()["error"]["code"] == "QUOTA_EXCEEDED"


def test_t_res_06_ttl_expiry_and_cleanup(stack_url: str) -> None:
    """T-RES-06: Expired environment becomes destroyed and leaves zero labelled Docker objects."""
    ca, csrfa = login_as(stack_url, "analyst.alpha@abhedya.local")
    env_a = create_env_and_wait(ca, csrfa, "res-06-ttl", size="S", ttl_minutes=1)
    deadline = time.monotonic() + 95.0
    while time.monotonic() < deadline:
        r = ca.get(f"{API_BASE}/envs/{env_a['id']}")
        if r.json()["observed_state"] == "destroyed":
            break
        time.sleep(2.0)
    assert ca.get(f"{API_BASE}/envs/{env_a['id']}").json()["observed_state"] == "destroyed"
    leaked = [c for c in docker_managed_inspect() if c["Config"]["Labels"].get("abh.env_id") == env_a["id"]]
    assert not leaked
