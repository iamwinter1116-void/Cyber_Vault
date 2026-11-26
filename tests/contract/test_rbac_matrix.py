"""Matrix-driven RBAC contract tests (T-RBAC-01..03, 05, 07, 09..12)."""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

import httpx
import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
MATRIX = yaml.safe_load((REPO_ROOT / "contracts" / "rbac_matrix.yaml").read_text(encoding="utf-8"))
ROLES: list[str] = MATRIX["roles"]
RULES: list[dict[str, Any]] = MATRIX["rules"]
BASE_PATH: str = MATRIX["base_path"]
RAND_UUID = "99999999-9999-4999-8999-999999999999"


def _login(client: httpx.Client, stack_url: str, email: str) -> str:
    pw = os.environ.get("ABH_DEMO_PASSWORD", "")
    r = client.post(f"{stack_url}{BASE_PATH}/auth/login", json={"email": email, "password": pw})
    assert r.status_code == 200, f"login failed for {email}: {r.status_code} {r.text}"
    return r.json()["csrf_token"]


def _create_env(client: httpx.Client, stack_url: str, csrf: str, name: str) -> str:
    r = client.post(
        f"{stack_url}{BASE_PATH}/envs",
        headers={"X-CSRF-Token": csrf},
        json={"name": name, "template": "app-target", "size": "S", "ttl_minutes": 10},
    )
    assert r.status_code == 201, f"create env failed: {r.status_code} {r.text}"
    return r.json()["id"]


def _create_job(client: httpx.Client, stack_url: str, csrf: str) -> str:
    r = client.post(
        f"{stack_url}{BASE_PATH}/ai-scans",
        headers={"X-CSRF-Token": csrf},
        json={"target": "stub-vulnerable", "probe_set": "quick"},
    )
    assert r.status_code == 202, f"create job failed: {r.status_code} {r.text}"
    return r.json()["id"]


def _fill_path(path: str, ids: dict[str, str]) -> str:
    for key, val in ids.items():
        path = path.replace(f"{{{key}}}", val)
    return path


def _payload_for_rule(rule_id: str, team_id: str) -> dict[str, Any]:
    return {
        "R05": {"email": "rbac.temp@abhedya.local", "password": "TempPassword!123", "role": "analyst", "team_id": team_id},
        "R06": {"disabled": False},
        "R08": {"name": "rbac-temp-team"},
        "R09": {"quota_envs": 4},
        "R12": {"name": "rbac-temp-env", "template": "app-target", "size": "S", "ttl_minutes": 10},
        "R17": {"command": "echo ok", "container": "toolbox"},
        "R21": {"target": "stub-vulnerable", "probe_set": "quick"},
        "R30": {"team_id": team_id},
    }.get(rule_id, {})


def _rbac_cases() -> list[tuple[dict[str, Any], str]]:
    return [(rule, actor) for rule in RULES for actor in ("anonymous", *ROLES)]


@pytest.mark.parametrize("rule,actor", _rbac_cases(), ids=lambda x: x["id"] if isinstance(x, dict) else str(x))
def test_t_rbac_01_matrix_enforcement(
    rule: dict[str, Any],
    actor: str,
    stack_url: str,
    fixture_users: dict[str, dict[str, str | None]],
) -> None:
    """T-RBAC-01: Assert exact 401/403/2xx from contracts/rbac_matrix.yaml against real resources."""
    is_public = bool(rule.get("public", False))
    allow_map: dict[str, str] = rule.get("allow", {})

    with httpx.Client(verify=False, timeout=5.0) as client:
        if actor == "anonymous":
            url = f"{stack_url}{BASE_PATH}{_fill_path(rule['path'], {'user_id': RAND_UUID, 'team_id': RAND_UUID, 'env_id': RAND_UUID, 'job_id': RAND_UUID})}"
            resp = client.request(rule["method"], url)
            assert (200 <= resp.status_code < 300) if is_public else (resp.status_code == 401)
            return

        if rule["id"] in ("R01", "R02", "R31"):
            return  # auth login/logout/healthz covered directly in T-AUTH

        adm_csrf = _login(client, stack_url, "admin@abhedya.local")
        teams = client.get(f"{stack_url}{BASE_PATH}/teams").json()["items"]
        alpha_team = next(t["id"] for t in teams if t["name"] == "alpha")
        users = client.get(f"{stack_url}{BASE_PATH}/users").json()["items"]
        alpha_user = next(u["id"] for u in users if u["email"] == "analyst.alpha@abhedya.local")

        a_csrf = _login(client, stack_url, "analyst.alpha@abhedya.local")
        alpha_env = _create_env(client, stack_url, a_csrf, f"rbac01-{actor}")
        alpha_job = _create_job(client, stack_url, a_csrf)

        user = next(u for u in fixture_users.values() if u["role"] == actor)
        email = "analyst.alpha@abhedya.local" if actor == "analyst" else str(user["email"])
        csrf = _login(client, stack_url, email)
        headers = {"X-CSRF-Token": csrf} if rule["method"] in ("POST", "PATCH", "DELETE") else {}
        ids = {"user_id": alpha_user, "team_id": alpha_team, "env_id": alpha_env, "job_id": alpha_job}
        url = f"{stack_url}{BASE_PATH}{_fill_path(rule['path'], ids)}"
        body = _payload_for_rule(rule["id"], alpha_team)
        if rule["id"] == "R20":
            resp = client.request(
                rule["method"],
                url,
                headers=headers,
                files={"file": ("rbac.txt", b"rbac", "text/plain")},
                data={"detonate": "false"},
            )
        else:
            resp = client.request(rule["method"], url, headers=headers, json=body if body else None)
        if is_public or actor in allow_map:
            assert 200 <= resp.status_code < 300, f"{rule['id']} failed for {actor}: {resp.status_code} {resp.text}"
        else:
            assert resp.status_code == 403, f"{rule['id']} expected 403 for {actor}, got {resp.status_code}"


@pytest.mark.parametrize(
    "rule",
    [r for r in RULES if "{" in r["path"] and any(role in r.get("allow", {}) for role in ("team_lead", "analyst"))],
    ids=lambda r: r["id"],
)
def test_t_rbac_02_cross_team_returns_404(rule: dict[str, Any], stack_url: str) -> None:
    """T-RBAC-02: Allowed alpha role targeting a real bravo object gets 404 matching random UUID 404."""
    with httpx.Client(verify=False, timeout=5.0) as client:
        b_csrf = _login(client, stack_url, "lead.bravo@abhedya.local")
        bravo_env = _create_env(client, stack_url, b_csrf, f"rbac02-b-{rule['id'].lower()}")
        bravo_job = _create_job(client, stack_url, b_csrf)
        bravo_ids = {"env_id": bravo_env, "job_id": bravo_job}

        b_headers = {"X-CSRF-Token": b_csrf} if rule["method"] in ("POST", "PATCH", "DELETE") else {}
        ctrl = client.request(rule["method"], f"{stack_url}{BASE_PATH}{_fill_path(rule['path'], bravo_ids)}", headers=b_headers)
        assert ctrl.status_code not in (401, 403, 404), f"Control failed for bravo owner: {ctrl.status_code}"

        a_csrf = _login(client, stack_url, "lead.alpha@abhedya.local")
        a_headers = {"X-CSRF-Token": a_csrf} if rule["method"] in ("POST", "PATCH", "DELETE") else {}
        r_cross = client.request(rule["method"], f"{stack_url}{BASE_PATH}{_fill_path(rule['path'], bravo_ids)}", headers=a_headers)
        r_rand = client.request(rule["method"], f"{stack_url}{BASE_PATH}{_fill_path(rule['path'], {'env_id': RAND_UUID, 'job_id': RAND_UUID})}", headers=a_headers)
        assert r_cross.status_code == 404 and r_rand.status_code == 404
        assert r_cross.json()["error"]["code"] == r_rand.json()["error"]["code"]
        assert r_cross.json()["error"]["message"] == r_rand.json()["error"]["message"]


@pytest.mark.parametrize("rule", [r for r in RULES if "own" in r.get("allow", {}).values()], ids=lambda r: r["id"])
def test_t_rbac_03_own_scope_teammate_returns_403(rule: dict[str, Any], stack_url: str) -> None:
    """T-RBAC-03: analyst2.alpha accessing a real object owned by analyst.alpha must return exact 403."""
    with httpx.Client(verify=False, timeout=5.0) as client:
        a1_csrf = _login(client, stack_url, "analyst.alpha@abhedya.local")
        env_id = _create_env(client, stack_url, a1_csrf, f"rbac03-{rule['id'].lower()}")
        job_id = _create_job(client, stack_url, a1_csrf)
        ids = {"env_id": env_id, "job_id": job_id}

        a2_csrf = _login(client, stack_url, "analyst2.alpha@abhedya.local")
        headers = {"X-CSRF-Token": a2_csrf} if rule["method"] in ("POST", "PATCH", "DELETE") else {}
        body = _payload_for_rule(rule["id"], "")
        resp = client.request(
            rule["method"],
            f"{stack_url}{BASE_PATH}{_fill_path(rule['path'], ids)}",
            headers=headers,
            json=body if body else None,
        )
        assert resp.status_code == 403, f"{rule['id']} expected 403 for teammate, got {resp.status_code}"


def test_t_rbac_05_registered_routes_match_matrix() -> None:
    """T-RBAC-05: API registered /api/v1 routes equal contracts/rbac_matrix.yaml and unmapped route fails startup."""
    if str(REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT))
    from services.api.authz import verify_route_coverage
    from services.api.main import create_app

    app = create_app()
    paths = app.openapi()["paths"]
    api_routes = {
        (method.upper(), path)
        for path, ops in paths.items()
        if path.startswith(BASE_PATH)
        for method in ops
        if method.upper() in ("GET", "POST", "PUT", "PATCH", "DELETE")
    }
    matrix_routes = {(r["method"], f"{BASE_PATH}{r['path']}") for r in RULES}
    assert api_routes == matrix_routes

    @app.get(f"{BASE_PATH}/_unmapped_test_route")
    def _unmapped() -> dict[str, bool]:
        return {"ok": True}

    with pytest.raises(RuntimeError):
        verify_route_coverage(app, require_all=True)


@pytest.mark.parametrize("rule_id", ["R17", "R18", "R19", "R20", "R21"])
@pytest.mark.parametrize("role", ["admin", "auditor"])
def test_t_rbac_07_platform_roles_denied_workload_io(
    rule_id: str,
    role: str,
    stack_url: str,
    fixture_users: dict[str, dict[str, str | None]],
) -> None:
    """T-RBAC-07: Platform roles (admin, auditor) cannot execute commands or read job output."""
    rule = next(r for r in RULES if r["id"] == rule_id)
    assert role not in rule.get("allow", {})
    user = next(u for u in fixture_users.values() if u["role"] == role)
    with httpx.Client(verify=False, timeout=5.0) as client:
        csrf = _login(client, stack_url, str(user["email"]))
        headers = {"X-CSRF-Token": csrf} if rule["method"] in ("POST", "PATCH", "DELETE") else {}
        url = f"{stack_url}{BASE_PATH}{_fill_path(rule['path'], {'env_id': RAND_UUID, 'job_id': RAND_UUID})}"
        resp = client.request(rule["method"], url, headers=headers)
        assert resp.status_code == 403


@pytest.mark.parametrize("br_id", ["BR1_LAST_ADMIN", "BR2_SELF_ROLE_CHANGE", "BR3_QUOTA_EXCEEDED", "BR4_ENV_NOT_RUNNING"])
def test_t_rbac_09_to_12_business_rules_return_409(br_id: str, stack_url: str) -> None:
    """T-RBAC-09..12: BR1..BR4 must return 409 with the contracted error code."""
    with httpx.Client(verify=False, timeout=5.0) as client:
        resp = client.get(f"{stack_url}{BASE_PATH}/healthz")
        assert resp.status_code == 200, f"{br_id} requires live stack"
        pytest.fail(f"{br_id} requires authenticated fixture setup on live stack")
