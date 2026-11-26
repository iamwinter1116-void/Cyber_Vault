"""Resource limit, quota, expiry, and reaper security tests: T-RES-01..06."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
from datetime import datetime

import pytest

from .conftest import API_BASE, create_env_and_wait, delete_env_and_wait, docker_managed_inspect, exec_in_env, login_as


def _assert_no_labelled_objects(env_id: str) -> None:
    for cmd in (["docker", "ps", "-aq"], ["docker", "network", "ls", "-q"], ["docker", "volume", "ls", "-q"]):
        out = subprocess.run([*cmd, "--filter", f"label=abh.env_id={env_id}"], capture_output=True, text=True, check=False)
        assert out.returncode == 0 and not out.stdout.strip(), f"Leftover Docker object for {env_id}: {out.stdout}"


def _parse_ts(ts: str) -> datetime:
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


def test_t_res_01_oom_kill_and_neighbor_isolation(stack_url: str) -> None:
    """T-RES-01: S env OOM-killed on mem_hog; alert.oom_killed <= 5s of actual OOM event, env.oom_killed audited, neighbor intact."""
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

        alert_ev: dict | None = None
        alert_deadline = time.monotonic() + 10.0
        while time.monotonic() < alert_deadline:
            evs = ca.get(f"{API_BASE}/events?env_id={env_hostile['id']}&severity=critical").json()["items"]
            alert_ev = next((e for e in evs if e["kind"] == "alert.oom_killed"), None)
            if alert_ev is not None:
                break
            time.sleep(0.5)
        assert alert_ev is not None, "alert.oom_killed not emitted"

        audits = adm.get(f"{API_BASE}/audit?action=env.oom_killed").json()["items"]
        oom_audit = next((a for a in audits if a["target_id"] == env_hostile["id"]), None)
        assert oom_audit is not None, "env.oom_killed not audited"
        oom_ref_ts = _parse_ts(job["finished_at"]) if job.get("finished_at") else _parse_ts(oom_audit["ts"])
        delta_s = abs((_parse_ts(alert_ev["ts"]) - oom_ref_ts).total_seconds())
        assert delta_s <= 5.0, f"alert.oom_killed arrived {delta_s:.2f}s after OOM event (limit 5s)"
    finally:
        delete_env_and_wait(ca, csrfa, env_hostile["id"])
        delete_env_and_wait(ca, csrfa, env_neighbor["id"])


def test_t_res_02_fork_bomb_contained(stack_url: str, record_property: pytest.FixtureRequest) -> None:
    """T-RES-02: Fork bomb contained for 30s (/healthz < 1s, neighbor < 5s), prove limit, then delete & remove <= 15s."""
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
        hostile_containers = [c for c in docker_managed_inspect() if c["Config"]["Labels"].get("abh.env_id") == env_hostile["id"]]
        assert hostile_containers and all(c["HostConfig"]["PidsLimit"] == env_hostile["pids_limit"] for c in hostile_containers)
        if fb_job["status"] == "done" and fb_job["result"].get("exit_code") == 1:
            fb_out = json.loads(fb_job["result"]["output"].strip().splitlines()[-1])
            assert fb_out["errno"] in ("EAGAIN", "ENOMEM", "EMFILE"), f"Unexpected fork_bomb errno: {fb_out}"
            record_property("fork_bomb_limit", f"pids_limit={env_hostile['pids_limit']} errno={fb_out['errno']} forks={fb_out['forks']}")
        else:
            record_property("fork_bomb_limit", f"pids_limit={env_hostile['pids_limit']} job_status={fb_job['status']}")

        assert ca.delete(f"{API_BASE}/envs/{env_hostile['id']}", headers={"X-CSRF-Token": csrfa}).status_code == 202
        rm_deadline = time.monotonic() + 15.0
        while time.monotonic() < rm_deadline:
            if ca.get(f"{API_BASE}/envs/{env_hostile['id']}").json()["observed_state"] == "destroyed":
                break
            time.sleep(1.0)
        assert ca.get(f"{API_BASE}/envs/{env_hostile['id']}").json()["observed_state"] == "destroyed"
        _assert_no_labelled_objects(env_hostile["id"])
    finally:
        if ca.get(f"{API_BASE}/envs/{env_hostile['id']}").json()["observed_state"] not in ("destroyed", "failed"):
            delete_env_and_wait(ca, csrfa, env_hostile["id"])
        delete_env_and_wait(ca, csrfa, env_neighbor["id"])


def test_t_res_03_storage_quota_enforced(stack_url: str) -> None:
    """T-RES-03: disk_fill /workspace exits 1 with ENOSPC <= storage_mb, host free drop <= quota, neighbor can write."""
    ca, csrfa = login_as(stack_url, "analyst.alpha@abhedya.local")
    vol_dir = os.environ.get("ABH_VOLUME_DIR", "/var/lib/abhedya/vol")
    env_a = create_env_and_wait(ca, csrfa, "res-03-alpha", size="S")
    env_neighbor = create_env_and_wait(ca, csrfa, "res-03-neighbor", size="S")
    try:
        free_before = shutil.disk_usage(vol_dir).free
        job = exec_in_env(ca, csrfa, env_a["id"], "disk_fill /workspace")
        assert job["result"]["exit_code"] == 1, f"Expected exit_code 1 (ENOSPC), got {job['result']}"
        out = json.loads(job["result"]["output"].strip().splitlines()[-1])
        assert out["errno"] == "ENOSPC", f"Expected ENOSPC, got {out}"
        max_bytes = env_a["storage_mb"] * 1048576
        assert out["bytes_written"] <= max_bytes
        free_after = shutil.disk_usage(vol_dir).free
        assert (free_before - free_after) <= max_bytes, f"Host free space dropped by {free_before - free_after} > {max_bytes}"

        nw = exec_in_env(ca, csrfa, env_neighbor["id"], "probe_write /workspace/neighbor.txt")
        assert json.loads(nw["result"]["output"].strip().splitlines()[-1])["ok"] is True
    finally:
        delete_env_and_wait(ca, csrfa, env_a["id"])
        delete_env_and_wait(ca, csrfa, env_neighbor["id"])


def test_t_res_04_cpu_limit_and_healthz_latency(stack_url: str) -> None:
    """T-RES-04: CPU burn stays <= 115% of cpu_millis over 20s; /healthz p95 < 300ms."""
    ca, csrfa = login_as(stack_url, "analyst.alpha@abhedya.local")
    env_a = create_env_and_wait(ca, csrfa, "res-04-alpha", size="S")
    try:
        t_start = time.monotonic()
        assert ca.post(f"{API_BASE}/envs/{env_a['id']}/exec", headers={"X-CSRF-Token": csrfa}, json={"command": "cpu_burn 20"}).status_code == 202
        latencies = []
        while time.monotonic() - t_start < 20.0:
            t0 = time.monotonic()
            assert ca.get(f"{API_BASE}/healthz").status_code == 200
            latencies.append(time.monotonic() - t0)
            time.sleep(0.5)
        latencies.sort()
        assert latencies[int(len(latencies) * 0.95)] < 0.300
        samples = ca.get(f"{API_BASE}/envs/{env_a['id']}/metrics?minutes=2").json()["items"]
        assert samples, "No CPU metric samples recorded during 20s burn"
        avg_cpu = sum(s["cpu_pct"] for s in samples) / len(samples)
        assert avg_cpu <= 115.0, f"Average CPU usage {avg_cpu:.1f}% exceeded 115% of cpu_millis"
    finally:
        delete_env_and_wait(ca, csrfa, env_a["id"])


def test_t_res_05_team_quota_enforced(stack_url: str, superuser_dsn: str) -> None:
    """T-RES-05: Quota enforcement returns 409 QUOTA_EXCEEDED, writes denied audit, and Team.usage == SQL sum."""
    import psycopg

    adm, adm_csrf = login_as(stack_url, "admin@abhedya.local")
    ca, csrfa = login_as(stack_url, "analyst.alpha@abhedya.local")
    alpha = next(t for t in adm.get(f"{API_BASE}/teams").json()["items"] if t["name"] == "alpha")
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
        req_id = over.headers["X-Request-ID"]
        audits = adm.get(f"{API_BASE}/audit?action=env.create&outcome=denied").json()["items"]
        assert any(a["request_id"] == req_id for a in audits), "Denied QUOTA_EXCEEDED env.create not audited"

        alpha_now = next(t for t in adm.get(f"{API_BASE}/teams").json()["items"] if t["id"] == alpha["id"])
        with psycopg.connect(superuser_dsn) as conn:
            row = conn.execute(
                "SELECT COUNT(*), COALESCE(SUM(cpu_millis),0), COALESCE(SUM(mem_mb),0), COALESCE(SUM(storage_mb),0) "
                "FROM env WHERE team_id = %s AND observed_state NOT IN ('destroyed', 'failed')",
                (alpha["id"],),
            ).fetchone()
        assert alpha_now["usage"] == {"envs": row[0], "cpu_millis": row[1], "mem_mb": row[2], "storage_mb": row[3]}

        assert adm.patch(f"{API_BASE}/teams/{alpha['id']}", headers={"X-CSRF-Token": adm_csrf}, json={"quota_envs": 0}).status_code == 200
        over2 = ca.post(f"{API_BASE}/envs", headers={"X-CSRF-Token": csrfa}, json={"name": "res-05-over2", "template": "app-target", "size": "S"})
        assert over2.status_code == 409 and over2.json()["error"]["code"] == "QUOTA_EXCEEDED"
    finally:
        adm.patch(f"{API_BASE}/teams/{alpha['id']}", headers={"X-CSRF-Token": adm_csrf}, json={"quota_envs": orig_quota})
        for eid in created:
            delete_env_and_wait(ca, csrfa, eid)


def test_t_res_06_ttl_expiry_and_cleanup(stack_url: str) -> None:
    """T-RES-06: Expired env becomes destroyed with zero objects; mid-provision runner restart converges without duplicates."""
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
        saw_provisioning = False
        for _ in range(40):
            st = ca.get(f"{API_BASE}/envs/{eid2}").json()["observed_state"]
            if st == "provisioning":
                saw_provisioning = True
                break
            if st == "running":
                break
            time.sleep(0.1)
        assert saw_provisioning, "Did not catch env in provisioning state before runner restart"
        assert subprocess.run(["docker", "compose", "restart", "runner"], capture_output=True, text=True, check=False).returncode == 0
        deadline2 = time.monotonic() + 45.0
        while time.monotonic() < deadline2:
            if ca.get(f"{API_BASE}/envs/{eid2}").json()["observed_state"] == "running":
                break
            time.sleep(1.0)
        assert ca.get(f"{API_BASE}/envs/{eid2}").json()["observed_state"] == "running"
        containers = [c for c in docker_managed_inspect() if c["Config"]["Labels"].get("abh.env_id") == eid2]
        assert len(containers) == 2, f"Expected 2 containers (target, toolbox), got {len(containers)}"
        nets = subprocess.run(["docker", "network", "ls", "-q", "--filter", f"label=abh.env_id={eid2}"], capture_output=True, text=True, check=False)
        vols = subprocess.run(["docker", "volume", "ls", "-q", "--filter", f"label=abh.env_id={eid2}"], capture_output=True, text=True, check=False)
        assert len(nets.stdout.splitlines()) == 1 and len(vols.stdout.splitlines()) == 1
    finally:
        delete_env_and_wait(ca, csrfa, eid2)
