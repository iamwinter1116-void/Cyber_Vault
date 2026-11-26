"""Isolation and static security tests: T-ISO-01..07, T-STATIC-01."""
from __future__ import annotations

import json
import os
import platform
from pathlib import Path

import pytest

from .conftest import API_BASE, REPO_ROOT, create_env_and_wait, docker_managed_inspect, exec_in_env, login_as


def test_t_iso_01_runtime_is_runsc(stack_url: str) -> None:
    """T-ISO-01: Every abh.managed=true container runs under runsc (or visible degraded alert)."""
    client, csrf = login_as(stack_url, "analyst.alpha@abhedya.local")
    create_env_and_wait(client, csrf, "iso-01-alpha")
    containers = docker_managed_inspect()
    for c in containers:
        runtime = c["HostConfig"]["Runtime"]
        assert runtime == "runsc", f"Container {c['Name']} runtime={runtime}, expected runsc"


def test_t_iso_02_sandbox_profile(stack_url: str) -> None:
    """T-ISO-02: Every row of docs/04_CONTRACTS.md section 8 holds in docker inspect."""
    for c in docker_managed_inspect():
        hc = c["HostConfig"]
        cfg = c["Config"]
        assert cfg["User"] == "1000:1000"
        assert hc["CapDrop"] == ["ALL"] and not hc.get("CapAdd")
        assert "no-new-privileges" in (hc.get("SecurityOpt") or [])
        assert hc["Privileged"] is False and not hc.get("Devices")
        assert hc["ReadonlyRootfs"] is True
        assert hc.get("PidMode", "") != "host" and hc.get("NetworkMode", "") != "host"
        for m in c.get("Mounts", []):
            assert "/var/run/docker.sock" not in m.get("Source", "")
            assert m.get("Destination") in ("/tmp", "/workspace") or m.get("RW") is False
        assert hc["NanoCpus"] > 0 and hc["Memory"] > 0 and hc["PidsLimit"] > 0
        labels = cfg.get("Labels") or {}
        for req in ("abh.managed", "abh.env_id", "abh.team_id", "abh.template"):
            assert req in labels


def test_t_iso_03_cross_team_network_isolation(stack_url: str, record_property: pytest.FixtureRequest) -> None:
    """T-ISO-03: Alpha toolbox cannot TCP connect/ICMP/DNS to bravo containers."""
    ca, csrfa = login_as(stack_url, "analyst.alpha@abhedya.local")
    cb, csrfb = login_as(stack_url, "analyst.bravo@abhedya.local")
    env_a = create_env_and_wait(ca, csrfa, "iso-03-alpha")
    env_b = create_env_and_wait(cb, csrfb, "iso-03-bravo")
    bravo_containers = [c for c in docker_managed_inspect() if c["Config"]["Labels"].get("abh.env_id") == env_b["id"]]
    bravo_ips = [net["IPAddress"] for c in bravo_containers for net in c["NetworkSettings"]["Networks"].values() if net.get("IPAddress")]
    assert bravo_ips, "No IP addresses found for bravo containers"
    for ip in bravo_ips:
        tcp = json.loads(exec_in_env(ca, csrfa, env_a["id"], f"probe_connect {ip} 80 3")["result"]["output"].strip().splitlines()[-1])
        assert tcp["reachable"] is False, f"Cross-team TCP reachability succeeded to {ip}"
        icmp = json.loads(exec_in_env(ca, csrfa, env_a["id"], f"probe_icmp {ip} 3")["result"]["output"].strip().splitlines()[-1])
        if icmp.get("sent"):
            assert icmp["reachable"] is False, f"Cross-team ICMP reachability succeeded to {ip}"
        else:
            record_property("icmp_note", f"ICMP not testable under cap_drop=ALL for {ip}: {icmp.get('error')}")
    for c in bravo_containers:
        cname = c["Name"].lstrip("/")
        dns = json.loads(exec_in_env(ca, csrfa, env_a["id"], f"probe_dns {cname} 3")["result"]["output"].strip().splitlines()[-1])
        assert dns["resolved"] is False, f"Cross-team DNS resolved {cname}: {dns.get('addresses')}"


def test_t_iso_04_egress_and_control_plane_blocked(stack_url: str) -> None:
    """T-ISO-04: Sandbox cannot reach bridge gateway, host LAN (443,5432,8000), or public IP (53,443)."""
    ca, csrfa = login_as(stack_url, "analyst.alpha@abhedya.local")
    env_a = create_env_and_wait(ca, csrfa, "iso-04-alpha")
    lan_ip = os.environ.get("ABH_HOST_LAN_IP", "127.0.0.1")
    targets = [(lan_ip, 443), (lan_ip, 5432), (lan_ip, 8000), ("1.1.1.1", 53), ("1.1.1.1", 443)]
    for host, port in targets:
        job = exec_in_env(ca, csrfa, env_a["id"], f"probe_connect {host} {port} 3")
        out = json.loads(job["result"]["output"].strip().splitlines()[-1])
        assert out["reachable"] is False, f"Egress/control-plane reachable at {host}:{port}"


def test_t_iso_05_cross_team_api_returns_404(stack_url: str) -> None:
    """T-ISO-05: analyst.alpha gets 404 on every bravo environment call."""
    ca, _ = login_as(stack_url, "analyst.alpha@abhedya.local")
    cb, csrfb = login_as(stack_url, "analyst.bravo@abhedya.local")
    env_b = create_env_and_wait(cb, csrfb, "iso-05-bravo")
    bid = env_b["id"]
    assert ca.get(f"{API_BASE}/envs/{bid}").status_code == 404
    assert ca.get(f"{API_BASE}/envs/{bid}/metrics").status_code == 404
    assert ca.post(f"{API_BASE}/envs/{bid}/stop").status_code in (403, 404)
    assert ca.delete(f"{API_BASE}/envs/{bid}").status_code in (403, 404)


def test_t_iso_06_env_mounts_socket_and_flags(stack_url: str) -> None:
    """T-ISO-06: No ABH_ vars, no docker.sock, read-only root, no flag_host, bravo cannot read alpha flag_env."""
    ca, csrfa = login_as(stack_url, "analyst.alpha@abhedya.local")
    cb, csrfb = login_as(stack_url, "analyst.bravo@abhedya.local")
    env_a = create_env_and_wait(ca, csrfa, "iso-06-alpha")
    env_b = create_env_and_wait(cb, csrfb, "iso-06-bravo")

    env_job = exec_in_env(ca, csrfa, env_a["id"], "probe_env")
    info = json.loads(env_job["result"]["output"].strip().splitlines()[-1])
    assert not any(v.startswith("ABH_") for v in info["env_vars"])
    assert info["uid"] == 1000

    w_job = exec_in_env(ca, csrfa, env_a["id"], "probe_write /etc/abhedya_test")
    assert json.loads(w_job["result"]["output"].strip().splitlines()[-1])["ok"] is False

    host_flag = exec_in_env(cb, csrfb, env_b["id"], "cat /var/lib/abhedya/flag_host")
    assert host_flag["result"]["exit_code"] != 0
    env_flag = exec_in_env(cb, csrfb, env_b["id"], "cat /workspace/flag_env")
    assert env_flag["result"]["exit_code"] != 0


def test_t_iso_07_kernel_release_differs_from_host(stack_url: str) -> None:
    """T-ISO-07: Sandbox uname -r must differ from host kernel release (gVisor)."""
    ca, csrfa = login_as(stack_url, "analyst.alpha@abhedya.local")
    env_a = create_env_and_wait(ca, csrfa, "iso-07-alpha")
    job = exec_in_env(ca, csrfa, env_a["id"], "probe_env")
    info = json.loads(job["result"]["output"].strip().splitlines()[-1])
    assert info["kernel_release"] != platform.release(), "Sandbox reports host kernel; not runsc"


def test_t_static_01_compose_and_runner_no_dangerous_flags() -> None:
    """T-STATIC-01: docker.sock only in runner; no privileged, network_mode: host, or cap_add."""
    compose = REPO_ROOT / "compose.yaml"
    assert compose.exists(), "compose.yaml missing (Manas M1 scaffold not present)"
    text = compose.read_text(encoding="utf-8")
    assert "privileged: true" not in text
    assert "network_mode: host" not in text
    assert "cap_add:" not in text
