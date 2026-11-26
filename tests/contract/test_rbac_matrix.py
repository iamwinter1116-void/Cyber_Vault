"""Matrix-driven RBAC contract tests (T-RBAC-01..03, 05, 07, 09..12)."""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any, Iterator

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


def _delete_env(client: httpx.Client, stack_url: str, csrf: str, env_id: str) -> None:
    client.delete(f"{stack_url}{BASE_PATH}/envs/{env_id}", headers={"X-CSRF-Token": csrf})


def _create_exec_job(client: httpx.Client, stack_url: str, csrf: str, env_id: str) -> str:
    r = client.post(
        f"{stack_url}{BASE_PATH}/envs/{env_id}/exec",
        headers={"X-CSRF-Token": csrf},
        json={"command": "echo ok", "container": "toolbox"},
    )
    assert r.status_code == 202, f"create exec job failed: {r.status_code} {r.text}"
    return r.json()["id"]


def _fill_path(path: str, ids: dict[str, str]) -> str:
    for key, val in ids.items():
        path = path.replace(f"{{{key}}}", val)
    return path


def _payload_for_rule(rule_id: str, team_id: str, suffix: str) -> dict[str, Any]:
    return {
        "R05": {"email": f"rbac.{suffix}@abhedya.local", "password": "TempPassword!123", "role": "analyst", "team_id": team_id},
        "R06": {"disabled": False},
        "R08": {"name": f"rbac-{suffix}"},
        "R09": {"quota_envs": 4},
        "R12": {"name": f"rbac-env-{suffix}", "template": "app-target", "size": "S", "ttl_minutes": 10},
        "R17": {"command": "echo ok", "container": "toolbox"},
        "R21": {"target": "stub-guarded", "probe_set": "quick"},
        "R30": {"team_id": team_id},
    }.get(rule_id, {})


@pytest.fixture(scope="module")
def real_rbac_ids(stack_url: str) -> Iterator[dict[str, str]]:
    """Create minimal real alpha & bravo fixtures once per module and clean them up."""
    with httpx.Client(verify=False, timeout=5.0) as adm:
        adm_csrf = _login(adm, stack_url, "admin@abhedya.local")
        teams = adm.get(f"{stack_url}{BASE_PATH}/teams").json()["items"]
        alpha_team = next(t["id"] for t in teams if t["name"] == "alpha")
        users = adm.get(f"{stack_url}{BASE_PATH}/users").json()["items"]
        analyst2_id = next(u["id"] for u in users if u["email"] == "analyst2.alpha@abhedya.local")

    with httpx.Client(verify=False, timeout=5.0) as a_cli, httpx.Client(verify=False, timeout=5.0) as b_cli:
        a_csrf = _login(a_cli, stack_url, "analyst.alpha@abhedya.local")
        b_csrf = _login(b_cli, stack_url, "lead.bravo@abhedya.local")
        alpha_env = _create_env(a_cli, stack_url, a_csrf, "rbac-alpha-shared")
        bravo_env = _create_env(b_cli, stack_url, b_csrf, "rbac-bravo-shared")
        alpha_job = _create_exec_job(a_cli, stack_url, a_csrf, alpha_env)
        bravo_job = _create_exec_job(b_cli, stack_url, b_csrf, bravo_env)
        try:
            yield {
                "alpha_team": alpha_team,
                "analyst2_id": analyst2_id,
                "alpha_env": alpha_env,
                "alpha_job": alpha_job,
                "bravo_env": bravo_env,
                "bravo_job": bravo_job,
            }
        finally:
            _delete_env(a_cli, stack_url, a_csrf, alpha_env)
            _delete_env(b_cli, stack_url, b_csrf, bravo_env)


def _rbac_cases() -> list[tuple[dict[str, Any], str]]:
    return [(rule, actor) for rule in RULES for actor in ("anonymous", *ROLES)]


@pytest.mark.parametrize("rule,actor", _rbac_cases(), ids=lambda x: x["id"] if isinstance(x, dict) else str(x))
def test_t_rbac_01_matrix_enforcement(
    rule: dict[str, Any],
    actor: str,
    stack_url: str,
    fixture_users: dict[str, dict[str, str | None]],
    real_rbac_ids: dict[str, str],
) -> None:
    """T-RBAC-01: Assert exact 401/403/2xx from contracts/rbac_matrix.yaml using minimal shared fixtures."""
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

        user = next(u for u in fixture_users.values() if u["role"] == actor)
        email = "analyst.alpha@abhedya.local" if actor == "analyst" else str(user["email"])
        csrf = _login(client, stack_url, email)
        headers = {"X-CSRF-Token": csrf} if rule["method"] in ("POST", "PATCH", "DELETE") else {}

        disposable_env: str | None = None
        env_target = real_rbac_ids["alpha_env"]
        if rule["id"] in ("R14", "R15") and actor in allow_map:
            a_csrf = _login(client, stack_url, "analyst.alpha@abhedya.local")
            disposable_env = _create_env(client, stack_url, a_csrf, f"rbac-disp-{actor}")
            env_target = disposable_env
            csrf = _login(client, stack_url, email)
            headers = {"X-CSRF-Token": csrf}

        ids = {
            "user_id": real_rbac_ids["analyst2_id"],
            "team_id": real_rbac_ids["alpha_team"],
            "env_id": env_target,
            "job_id": real_rbac_ids["alpha_job"],
        }
        url = f"{stack_url}{BASE_PATH}{_fill_path(rule['path'], ids)}"
        body = _payload_for_rule(rule["id"], real_rbac_ids["alpha_team"], f"{rule['id'].lower()}-{actor}")
        try:
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
                if rule["id"] == "R12":
                    _delete_env(client, stack_url, csrf, resp.json()["id"])
                elif rule["id"] in ("R20", "R21") and resp.json().get("env_id"):
                    _delete_env(client, stack_url, csrf, resp.json()["env_id"])
            else:
                assert resp.status_code == 403, f"{rule['id']} expected 403 for {actor}, got {resp.status_code}"
        finally:
            if disposable_env:
                _delete_env(client, stack_url, csrf, disposable_env)


@pytest.mark.parametrize(
    "rule",
    [r for r in RULES if "{" in r["path"] and any(role in r.get("allow", {}) for role in ("team_lead", "analyst"))],
    ids=lambda r: r["id"],
)
def test_t_rbac_02_cross_team_returns_404(rule: dict[str, Any], stack_url: str, real_rbac_ids: dict[str, str]) -> None:
    """T-RBAC-02: Allowed alpha role targeting a real bravo object gets 404 matching random UUID 404."""
    with httpx.Client(verify=False, timeout=5.0) as b_cli, httpx.Client(verify=False, timeout=5.0) as a_cli:
        b_csrf = _login(b_cli, stack_url, "lead.bravo@abhedya.local")
        a_csrf = _login(a_cli, stack_url, "lead.alpha@abhedya.local")
        bravo_env = real_rbac_ids["bravo_env"]
        disposable: str | None = None
        if rule["id"] in ("R14", "R15"):
            disposable = _create_env(b_cli, stack_url, b_csrf, f"rbac02-disp-{rule['id'].lower()}")
            bravo_env = disposable

        bravo_ids = {"env_id": bravo_env, "job_id": real_rbac_ids["bravo_job"]}
        b_headers = {"X-CSRF-Token": b_csrf} if rule["method"] in ("POST", "PATCH", "DELETE") else {}
        a_headers = {"X-CSRF-Token": a_csrf} if rule["method"] in ("POST", "PATCH", "DELETE") else {}
        body = _payload_for_rule(rule["id"], "", "02")
        try:
            r_cross = a_cli.request(rule["method"], f"{stack_url}{BASE_PATH}{_fill_path(rule['path'], bravo_ids)}", headers=a_headers, json=body if body else None)
            r_rand = a_cli.request(rule["method"], f"{stack_url}{BASE_PATH}{_fill_path(rule['path'], {'env_id': RAND_UUID, 'job_id': RAND_UUID})}", headers=a_headers, json=body if body else None)
            assert r_cross.status_code == 404 and r_rand.status_code == 404
            assert r_cross.json()["error"]["code"] == r_rand.json()["error"]["code"]
            assert r_cross.json()["error"]["message"] == r_rand.json()["error"]["message"]

            ctrl = b_cli.request(rule["method"], f"{stack_url}{BASE_PATH}{_fill_path(rule['path'], bravo_ids)}", headers=b_headers, json=body if body else None)
            assert 200 <= ctrl.status_code < 300, f"Control failed for bravo owner: {ctrl.status_code}"
        finally:
            if disposable:
                _delete_env(b_cli, stack_url, b_csrf, disposable)


@pytest.mark.parametrize("rule", [r for r in RULES if "own" in r.get("allow", {}).values()], ids=lambda r: r["id"])
def test_t_rbac_03_own_scope_teammate_returns_403(rule: dict[str, Any], stack_url: str, real_rbac_ids: dict[str, str]) -> None:
    """T-RBAC-03: analyst2.alpha accessing a real object owned by analyst.alpha must return exact 403."""
    with httpx.Client(verify=False, timeout=5.0) as client:
        a2_csrf = _login(client, stack_url, "analyst2.alpha@abhedya.local")
        headers = {"X-CSRF-Token": a2_csrf} if rule["method"] in ("POST", "PATCH", "DELETE") else {}
        ids = {"env_id": real_rbac_ids["alpha_env"], "job_id": real_rbac_ids["alpha_job"]}
        body = _payload_for_rule(rule["id"], "", "03")
        resp = client.request(rule["method"], f"{stack_url}{BASE_PATH}{_fill_path(rule['path'], ids)}", headers=headers, json=body if body else None)
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
    real_rbac_ids: dict[str, str],
) -> None:
    """T-RBAC-07: Platform roles (admin, auditor) cannot execute commands or read job output."""
    rule = next(r for r in RULES if r["id"] == rule_id)
    assert role not in rule.get("allow", {})
    user = next(u for u in fixture_users.values() if u["role"] == role)
    with httpx.Client(verify=False, timeout=5.0) as client:
        csrf = _login(client, stack_url, str(user["email"]))
        headers = {"X-CSRF-Token": csrf} if rule["method"] in ("POST", "PATCH", "DELETE") else {}
        url = f"{stack_url}{BASE_PATH}{_fill_path(rule['path'], {'env_id': real_rbac_ids['alpha_env'], 'job_id': real_rbac_ids['alpha_job']})}"
        resp = client.request(rule["method"], url, headers=headers)
        assert resp.status_code == 403


def test_t_rbac_09_br1_last_admin_returns_409(stack_url: str) -> None:
    """T-RBAC-09 (BR1): R06 refuses disabling the last enabled admin with 409 LAST_ADMIN."""
    with httpx.Client(verify=False, timeout=5.0) as client:
        csrf = _login(client, stack_url, "admin@abhedya.local")
        users = client.get(f"{stack_url}{BASE_PATH}/users").json()["items"]
        admins = [u for u in users if u["role"] == "admin" and not u["disabled"]]
        assert len(admins) == 1, f"Expected 1 enabled admin for BR1 test, found {len(admins)}"
        r = client.patch(f"{stack_url}{BASE_PATH}/users/{admins[0]['id']}", headers={"X-CSRF-Token": csrf}, json={"disabled": True})
        assert r.status_code == 409 and r.json()["error"]["code"] == "LAST_ADMIN"


def test_t_rbac_10_br2_self_role_change_returns_409(stack_url: str) -> None:
    """T-RBAC-10 (BR2): R06 refuses changing the caller's own role with 409 SELF_ROLE_CHANGE."""
    with httpx.Client(verify=False, timeout=5.0) as client:
        csrf = _login(client, stack_url, "admin@abhedya.local")
        me = client.get(f"{stack_url}{BASE_PATH}/auth/me").json()["user"]
        r = client.patch(f"{stack_url}{BASE_PATH}/users/{me['id']}", headers={"X-CSRF-Token": csrf}, json={"role": "analyst"})
        assert r.status_code == 409 and r.json()["error"]["code"] == "SELF_ROLE_CHANGE"


def test_t_rbac_11_br3_quota_exceeded_returns_409(stack_url: str, real_rbac_ids: dict[str, str]) -> None:
    """T-RBAC-11 (BR3): R12 refuses when team quota is exceeded with 409 QUOTA_EXCEEDED."""
    with httpx.Client(verify=False, timeout=5.0) as adm, httpx.Client(verify=False, timeout=5.0) as ana:
        adm_csrf = _login(adm, stack_url, "admin@abhedya.local")
        ana_csrf = _login(ana, stack_url, "analyst.alpha@abhedya.local")
        alpha_id = real_rbac_ids["alpha_team"]
        orig_quota = next(t["quota_envs"] for t in adm.get(f"{stack_url}{BASE_PATH}/teams").json()["items"] if t["id"] == alpha_id)
        assert adm.patch(f"{stack_url}{BASE_PATH}/teams/{alpha_id}", headers={"X-CSRF-Token": adm_csrf}, json={"quota_envs": 0}).status_code == 200
        try:
            r = ana.post(
                f"{stack_url}{BASE_PATH}/envs",
                headers={"X-CSRF-Token": ana_csrf},
                json={"name": "br3-over-quota", "template": "app-target", "size": "S"},
            )
            assert r.status_code == 409 and r.json()["error"]["code"] == "QUOTA_EXCEEDED"
        finally:
            adm.patch(f"{stack_url}{BASE_PATH}/teams/{alpha_id}", headers={"X-CSRF-Token": adm_csrf}, json={"quota_envs": orig_quota})


def test_t_rbac_12_br4_env_not_running_returns_409(stack_url: str) -> None:
    """T-RBAC-12 (BR4): R17 refuses exec on a non-running env with 409 ENV_NOT_RUNNING."""
    with httpx.Client(verify=False, timeout=5.0) as client:
        csrf = _login(client, stack_url, "analyst.alpha@abhedya.local")
        env_id = _create_env(client, stack_url, csrf, "br4-not-running")
        try:
            assert client.post(f"{stack_url}{BASE_PATH}/envs/{env_id}/stop", headers={"X-CSRF-Token": csrf}).status_code == 202
            r = client.post(
                f"{stack_url}{BASE_PATH}/envs/{env_id}/exec",
                headers={"X-CSRF-Token": csrf},
                json={"command": "echo hi", "container": "toolbox"},
            )
            assert r.status_code == 409 and r.json()["error"]["code"] == "ENV_NOT_RUNNING"
        finally:
            _delete_env(client, stack_url, csrf, env_id)
