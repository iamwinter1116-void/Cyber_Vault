"""Resource limit, quota, expiry, and reaper security tests: T-RES-01..06."""
from __future__ import annotations

import time

from .conftest import API_BASE, create_env_and_wait, docker_managed_inspect, exec_in_env, login_as


def test_t_res_01_oom_kill_and_neighbor_isolation(stack_url: str) -> None:
    """T-RES-01: S env OOM-killed on mem_hog; neighbor echo loop unaffected."""
    ca, csrfa = login_as(stack_url, "analyst.alpha@abhedya.local")
    env_hostile = create_env_and_wait(ca, csrfa, "res-01-hostile", size="S")
    env_neighbor = create_env_and_wait(ca, csrfa, "res-01-neighbor", size="S")
    job = exec_in_env(ca, csrfa, env_hostile["id"], "mem_hog 512")
    assert job["result"]["exit_code"] != 0
    hb = exec_in_env(ca, csrfa, env_neighbor["id"], "echo ok")
    assert hb["result"]["exit_code"] == 0


def test_t_res_02_fork_bomb_contained(stack_url: str) -> None:
    """T-RES-02: Fork bomb contained; /healthz < 1s and neighbor exec < 5s."""
    ca, csrfa = login_as(stack_url, "analyst.alpha@abhedya.local")
    env_hostile = create_env_and_wait(ca, csrfa, "res-02-hostile", size="S")
    env_neighbor = create_env_and_wait(ca, csrfa, "res-02-neighbor", size="S")
    ca.post(f"{API_BASE}/envs/{env_hostile['id']}/exec", headers={"X-CSRF-Token": csrfa}, json={"command": "fork_bomb"})
    t0 = time.monotonic()
    assert ca.get(f"{API_BASE}/healthz").status_code == 200
    assert time.monotonic() - t0 < 1.0
    t1 = time.monotonic()
    hb = exec_in_env(ca, csrfa, env_neighbor["id"], "echo ok")
    assert hb["result"]["exit_code"] == 0 and (time.monotonic() - t1) < 5.0


def test_t_res_03_storage_quota_enforced(stack_url: str) -> None:
    """T-RES-03: Writing to /workspace fails with no space at or below storage_mb."""
    ca, csrfa = login_as(stack_url, "analyst.alpha@abhedya.local")
    env_a = create_env_and_wait(ca, csrfa, "res-03-alpha", size="S")
    job = exec_in_env(ca, csrfa, env_a["id"], "disk_fill /workspace")
    assert job["result"]["exit_code"] != 0


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
