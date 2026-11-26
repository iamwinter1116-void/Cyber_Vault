"""Shared helpers and fixtures for security tests (Bhavya-owned)."""
from __future__ import annotations

import json
import os
import subprocess
import time
from pathlib import Path
from typing import Any

import httpx
import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
API_BASE = "/api/v1"


@pytest.fixture(scope="session")
def stack_url() -> str:
    return os.environ.get("ABH_STACK_URL", "https://localhost")


@pytest.fixture(scope="session")
def superuser_dsn() -> str:
    dsn = os.environ.get("ABH_SUPERUSER_DSN", os.environ.get("ABH_DB_DSN", ""))
    if not dsn:
        pytest.fail("ABH_SUPERUSER_DSN or ABH_DB_DSN must be set for security DB checks")
    return dsn


def login_as(stack_url: str, email: str, password: str | None = None) -> tuple[httpx.Client, str]:
    pw = password or os.environ.get("ABH_DEMO_PASSWORD", "")
    client = httpx.Client(base_url=stack_url, verify=False, timeout=10.0)
    resp = client.post(f"{API_BASE}/auth/login", json={"email": email, "password": pw})
    assert resp.status_code == 200, f"Login failed for {email}: {resp.status_code} {resp.text}"
    return client, resp.json()["csrf_token"]


def create_env_and_wait(client: httpx.Client, csrf: str, name: str, size: str = "S", ttl_minutes: int = 10) -> dict[str, Any]:
    resp = client.post(
        f"{API_BASE}/envs",
        headers={"X-CSRF-Token": csrf},
        json={"name": name, "template": "app-target", "size": size, "ttl_minutes": ttl_minutes},
    )
    assert resp.status_code == 201, f"Create env failed: {resp.status_code} {resp.text}"
    env_id = resp.json()["id"]
    deadline = time.monotonic() + 30.0
    while time.monotonic() < deadline:
        r = client.get(f"{API_BASE}/envs/{env_id}")
        assert r.status_code == 200
        if r.json()["observed_state"] == "running":
            return r.json()
        time.sleep(0.5)
    pytest.fail(f"Env {env_id} did not reach running within 30s")


def delete_env_and_wait(client: httpx.Client, csrf: str, env_id: str) -> None:
    dr = client.delete(f"{API_BASE}/envs/{env_id}", headers={"X-CSRF-Token": csrf})
    assert dr.status_code == 202, f"Delete env {env_id} failed: {dr.status_code} {dr.text}"
    deadline = time.monotonic() + 30.0
    while time.monotonic() < deadline:
        r = client.get(f"{API_BASE}/envs/{env_id}")
        assert r.status_code == 200
        if r.json()["observed_state"] in ("destroyed", "failed"):
            return
        time.sleep(0.5)
    pytest.fail(f"Env {env_id} did not reach destroyed/failed within 30s")


def exec_in_env(client: httpx.Client, csrf: str, env_id: str, command: str, container: str = "toolbox") -> dict[str, Any]:
    resp = client.post(
        f"{API_BASE}/envs/{env_id}/exec",
        headers={"X-CSRF-Token": csrf},
        json={"command": command, "container": container},
    )
    assert resp.status_code == 202, f"Exec submit failed: {resp.status_code} {resp.text}"
    job_id = resp.json()["id"]
    deadline = time.monotonic() + 75.0
    while time.monotonic() < deadline:
        jr = client.get(f"{API_BASE}/jobs/{job_id}")
        assert jr.status_code == 200
        if jr.json()["status"] in ("done", "timeout", "error"):
            return jr.json()
        time.sleep(0.5)
    pytest.fail(f"Job {job_id} did not finish within 75s")


def docker_managed_inspect() -> list[dict[str, Any]]:
    ps = subprocess.run(["docker", "ps", "-q", "--filter", "label=abh.managed=true"], capture_output=True, text=True, check=False)
    assert ps.returncode == 0, f"docker ps failed: {ps.stderr}"
    ids = [i for i in ps.stdout.splitlines() if i.strip()]
    assert ids, "No running abh.managed=true containers found"
    insp = subprocess.run(["docker", "inspect", *ids], capture_output=True, text=True, check=False)
    assert insp.returncode == 0, f"docker inspect failed: {insp.stderr}"
    return json.loads(insp.stdout)
