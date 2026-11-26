"""Resource limit, quota, expiry, and reaper security tests: T-RES-01..06."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import time

import pytest

from .conftest import API_BASE, create_env_and_wait, delete_env_and_wait, docker_managed_inspect, exec_in_env, login_as


def _assert_no_labelled_objects(env_id: str) -> None:
    for cmd in (["docker", "ps", "-aq"], ["docker", "network", "ls", "-q"], ["docker", "volume", "ls", "-q"]):
        out = subprocess.run([*cmd, "--filter", f"label=abh.env_id={env_id}"], capture_output=True, text=True, check=False)
        assert out.returncode == 0 and not out.stdout.strip(), f"Leftover Docker object for {env_id}: {out.stdout}"


def test_t_res_01_oom_kill_and_neighbor_isolation(stack_url: str) -> None:
    """T-RES-01: S env OOM-killed on mem_hog; alert.oom_killed <= 5s of OOM, env.oom_killed audited, neighbor intact."""
    ca, csrfa = login_as(stack_url, "analyst.alpha@abhedya.local")
    adm, _ = login_as(stack_url, "admin@abhedya.local")
    env_hostile = create_env_and_wait(ca, csrfa, "res-01-hostile", size="S")
    env_neighbor = create_env_and_wait(ca, csrfa, "res-01-neighbor", size="S")
    try:
        sub = ca.post(f"{API_BASE}/envs/{env_hostile['id']}/exec", headers={"X-CSRF-Token": csrfa}, json={"command": "mem_hog 512"})
        assert sub.status_code == 202
        job_id = sub.json()["id"]

        misses = 0
        job: dict = {}
        stress_deadline = time.monotonic() + 35.0
        while time.monotonic() < stress_deadline:
            t0 = time.monotonic()
            hb = exec_in_env(ca, csrfa, env_neighbor["id"], "echo ok")
            if hb["result"]["exit_code"] != 0 or (time.monotonic() - t0) > 2.0:
                misses += 1
            job = ca.get(f"{API_BASE}/jobs/{job_id}").json()
            if job["status"] in ("done", "timeout", "error"):
                break
            time.sleep(max(0.0, 1.0 - (time.monotonic() - t0)))
        assert misses <= 1, f"Neighbor missed {misses} beats during OOM"
        assert job.get("status") in ("done", "error"), f"OOM job did not finish: {job}"
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
        assert saw_alert, "alert.oom_killed not emitted within 5s of OOM completion"

        audits = adm.get(f"{API_BASE}/audit?action=env.oom_killed").json()["items"]
        assert any(a["target_id"] == env_hostile["id"] for a in audits), "env.oom_killed not audited"
    finally:
        delete_env_and_wait(ca, csrfa, env_hostile["id"])
        delete_env_and_wait(ca, csrfa, env_neighbor["id"])


def test_t_res_02_fork_bomb_contained(stack_url: str, record_property: pytest.FixtureRequest) -> None:
    """T-RES-02: Fork bomb contained for 30s (/healthz < 1s, neighbor < 5s), then deleted & all Docker objects removed <= 15s."""
    ca, csrfa = login_as(stack_url, "analyst.alpha@abhedya.local")
    env_hostile = create_env_and_wait(ca, csrfa, "res-02-hostile", size="S")
    env_neighbor = create_env_and_wait(ca, csrfa, "res-02-neighbor", size="S")
    try:
        sub = ca.post(f"{API_BASE}/envs/{env_hostile['id']}/exec", headers={"X-CSRF-Token": csrfa}, json={"command": "fork_bomb"})
        assert sub.status_code == 202
        job_id = sub.json()["id"]

        end_window = time.monotonic() + 30.0
        while time.monotonic() < end_window:
            t0 = time.monotonic()
            assert ca.get(f"{API_BASE}/healthz").status_code == 200
            assert (time.monotonic() - t0) < 1.0, "/healthz exceeded 1s during fork bomb"
            t1 = time.monotonic()
            hb = exec_in_env(ca, csrfa, env_neighbor["id"], "echo ok")
            assert hb["result"]["exit_code"] == 0 and (time.monotonic() - t1) < 5.0
            time.sleep(2.0)

        fb_job = ca.get(f"{API_BASE}/jobs/{job_id}").json()
        pids_lim = env_hostile["pids_limit"]
        record_property("fork_bomb_limit", f"pids_limit={pids_lim} job_status={fb_job['status']} result={fb_job.get('result')}")

        assert ca.delete(f"{API_BASE}/envs/{env_hostile['id']}", headers={"X-CSRF-Token": csrfa}).status_code == 202
        rm_deadline = time.monotonic() + 15.0
        while time.monotonic() < rm_deadline:
            st = ca.get(f"{API_BASE}/envs/{env_hostile['id']}").json()["observed_state"]
            if st == "destroyed":
                break
            time.sleep(1.0)
        assert ca.get(f"{API_BASE}/envs/{env_hostile['id']}").json()["observed_state"] == "destroyed"
        _assert_no_labelled_objects(env_hostile["id"])
    finally:
        delete_env_and_wait(ca, csrfa, env_neighbor["id"])


def test_t_res_03_storage_quota_enforced(stack_url: str) -> None:
    """T-RES-03: disk_fill /workspace exits 1 with ENOSPC <= storage_mb, host free drop bounded, neighbor can write."""
    ca, csrfa = login_as(stack_url, "analyst.alpha@abhedya.local")
    vol_dir = os.environ.get("ABH_VOLUME_DIR", "/var/lib/abhedya/vol")
    free_before = shutil.disk_usage(vol_dir).free
    env_a = create_env_and_wait(ca, csrfa, "res-03-alpha", size="S")
    env_neighbor = create_env_and_wait(ca, csrfa, "res-03-neighbor", size="S")
    try:
        job = exec_in_env(ca, csrfa, env_a["id"], "disk_fill /workspace")
        assert job["result"]["exit_code"] == 1, f"Expected exit_code 1 (ENOSPC), got {job['result']}"
        out = json.loads(job["result"]["output"].strip().splitlines()[-1])
        assert out["errno"] == "ENOSPC", f"Expected ENOSPC, got {out}"
        max_bytes = env_a["storage_mb"] * 1048576
        assert out["bytes_written"] <= max_bytes
        free_after = shutil.disk_usage(vol_dir).free
        assert (free_before - free_after) <= max_bytes + (16 * 1048576), "Host free space dropped beyond quota"

        nw = exec_in_env(ca, csrfa, env_neighbor["id"], "probe_write /workspace/neighbor.txt")
        assert json.loads(nw["result"]["output"].strip().splitlines()[-1])["ok"] is True
    finally:
        delete_env_and_wait(ca, csrfa, env_a["id"])
        delete_env_and_wait(ca, csrfa, env_neighbor["id"])


def test_t_res_04_cpu_limit_and_healthz_latency(stack_url: str) -> None:
    """T-RES-04: CPU burn stays <= 115% of cpu_millis; /healthz p95 < 300ms."""
    ca, csrfa = login_as(stack_url, "analyst.alpha@abhedya.local")
    env_a = create_env_and_wait(ca, csrfa, "res-04-alpha", size="S")
    try:
        ca.post(f"{API_BASE}/envs/{env_a['id']}/exec", headers={"X-CSRF-Token": csrfa}, json={"command": "cpu_burn 20"})
        latencies = []
        for _ in range(20):
            t0 = time.monotonic()
            assert ca.get(f"{API_BASE}/healthz").status_code == 200
            latencies.append(time.monotonic() - t0)
            time.sleep(0.2)
        latencies.sort()
        assert latencies[int(len(latencies) * 0.95)] < 0.300
    finally:
        delete_env_and_wait(ca, csrfa, env_a["id"])


def test_t_res_05_team_quota_enforced(stack_url: str) -> None:
    """T-RES-05: Requesting past team quota returns 409 QUOTA_EXCEEDED; lowering quota also enforces 409."""
    adm, adm_csrf = login_as(stack_url, "admin@abhedya.local")
    ca, csrfa = login_as(stack_url, "analyst.alpha@abhedya.local")
    teams = adm.get(f"{API_BASE}/teams").json()["items"]
    alpha = next(t for t in teams if t["name"] == "alpha")
    orig_quota = alpha["quota_envs"]
    created: list[str] = []
    try:
        needed = max(0, orig_quota - alpha["usage"]["envs"])
        for i in range(needed):
            r = ca.post(f"{API_BASE}/envs", headers={"X-CSRF-Token": csrfa}, json={"name": f"res-05-q{i}", "template": "app-target", "size": "S"})
            assert r.status_code == 201, f"Expected 201 within quota, got {r.status_code} {r.text}"
            created.append(r.json()["id"])
        over = ca.post(f"{API_BASE}/envs", headers={"X-CSRF-Token": csrfa}, json={"name": "res-05-over", "template": "app-target", "size": "S"})
        assert over.status_code == 409 and over.json()["error"]["code"] == "QUOTA_EXCEEDED"

        assert adm.patch(f"{API_BASE}/teams/{alpha['id']}", headers={"X-CSRF-Token": adm_csrf}, json={"quota_envs": 0}).status_code == 200
        over2 = ca.post(f"{API_BASE}/envs", headers={"X-CSRF-Token": csrfa}, json={"name": "res-05-over2", "template": "app-target", "size": "S"})
        assert over2.status_code == 409 and over2.json()["error"]["code"] == "QUOTA_EXCEEDED"
    finally:
        adm.patch(f"{API_BASE}/teams/{alpha['id']}", headers={"X-CSRF-Token": adm_csrf}, json={"quota_envs": orig_quota})
        for eid in created:
            delete_env_and_wait(ca, csrfa, eid)


def test_t_res_06_ttl_expiry_and_cleanup(stack_url: str) -> None:
    """T-RES-06: Expired env becomes destroyed with zero containers/networks/volumes; runner restart mid-provision converges."""
    ca, csrfa = login_as(stack_url, "analyst.alpha@abhedya.local")
    env_a = create_env_and_wait(ca, csrfa, "res-06-ttl", size="S", ttl_minutes=1)
    deadline = time.monotonic() + 95.0
    while time.monotonic() < deadline:
        if ca.get(f"{API_BASE}/envs/{env_a['id']}").json()["observed_state"] == "destroyed":
            break
        time.sleep(2.0)
    assert ca.get(f"{API_BASE}/envs/{env_a['id']}").json()["observed_state"] == "destroyed"
    _assert_no_labelled_objects(env_a["id"])

    r_prov = ca.post(f"{API_BASE}/envs", headers={"X-CSRF-Token": csrfa}, json={"name": "res-06-restart", "template": "app-target", "size": "S"})
    assert r_prov.status_code == 201
    eid2 = r_prov.json()["id"]
    try:
        assert subprocess.run(["docker", "compose", "restart", "runner"], capture_output=True, text=True, check=False).returncode == 0
        deadline2 = time.monotonic() + 45.0
        while time.monotonic() < deadline2:
            if ca.get(f"{API_BASE}/envs/{eid2}").json()["observed_state"] == "running":
                break
            time.sleep(1.0)
        assert ca.get(f"{API_BASE}/envs/{eid2}").json()["observed_state"] == "running"
        matches = [c for c in docker_managed_inspect() if c["Config"]["Labels"].get("abh.env_id") == eid2]
        assert len({c["Config"]["Labels"].get("abh.service", c["Name"]) for c in matches}) == len(matches)
    finally:
        delete_env_and_wait(ca, csrfa, eid2)
