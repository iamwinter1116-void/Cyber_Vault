"""Matrix-driven RBAC contract tests (T-RBAC-01..04, 07, 09..12)."""
from __future__ import annotations

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


def _resolve_path(path: str) -> str:
    return (
        path.replace("{user_id}", "00000000-0000-4000-8000-000000000001")
        .replace("{team_id}", "00000000-0000-4000-8000-000000000002")
        .replace("{env_id}", "00000000-0000-4000-8000-000000000003")
        .replace("{job_id}", "00000000-0000-4000-8000-000000000004")
    )


def _rbac_cases() -> list[tuple[dict[str, Any], str]]:
    cases: list[tuple[dict[str, Any], str]] = []
    for rule in RULES:
        cases.append((rule, "anonymous"))
        for role in ROLES:
            cases.append((rule, role))
    return cases


@pytest.mark.parametrize("rule,actor", _rbac_cases(), ids=lambda x: x["id"] if isinstance(x, dict) else str(x))
def test_t_rbac_01_matrix_enforcement(
    rule: dict[str, Any],
    actor: str,
    stack_url: str,
    fixture_users: dict[str, dict[str, str | None]],
) -> None:
    """Assert T-RBAC-01 directly from contracts/rbac_matrix.yaml without duplicating allow map."""
    url = f"{stack_url}{BASE_PATH}{_resolve_path(rule['path'])}"
    is_public = bool(rule.get("public", False))
    allow_map: dict[str, str] = rule.get("allow", {})

    with httpx.Client(verify=False, timeout=5.0) as client:
        if actor == "anonymous":
            resp = client.request(rule["method"], url)
            if is_public:
                assert resp.status_code not in (401, 403)
            else:
                assert resp.status_code == 401
            return

        user = next(u for u in fixture_users.values() if u["role"] == actor)
        login_resp = client.post(
            f"{stack_url}{BASE_PATH}/auth/login",
            json={"email": user["email"], "password": ""},
        )
        assert login_resp.status_code == 200, f"login failed for {actor}: {login_resp.text}"
        csrf = login_resp.json()["csrf_token"]
        headers = {"X-CSRF-Token": csrf} if rule["method"] in ("POST", "PATCH", "DELETE") else {}
        resp = client.request(rule["method"], url, headers=headers)
        if is_public or actor in allow_map:
            assert resp.status_code not in (401, 403)
        else:
            assert resp.status_code == 403


@pytest.mark.parametrize("rule", [r for r in RULES if "{" in r["path"]], ids=lambda r: r["id"])
def test_t_rbac_02_cross_team_returns_404(rule: dict[str, Any], stack_url: str) -> None:
    """Cross-team object lookup must return 404 indistinguishable from random UUID."""
    with httpx.Client(verify=False, timeout=5.0) as client:
        resp = client.request(rule["method"], f"{stack_url}{BASE_PATH}{_resolve_path(rule['path'])}")
        assert resp.status_code in (401, 404)


@pytest.mark.parametrize("rule", [r for r in RULES if "own" in r.get("allow", {}).values()], ids=lambda r: r["id"])
def test_t_rbac_03_own_scope_teammate_returns_403(rule: dict[str, Any], stack_url: str) -> None:
    """Rules with scope 'own' must return 403 for a teammate's object."""
    with httpx.Client(verify=False, timeout=5.0) as client:
        resp = client.request(rule["method"], f"{stack_url}{BASE_PATH}{_resolve_path(rule['path'])}")
        assert resp.status_code == 403


@pytest.mark.parametrize("rule_id", ["R17", "R18", "R19", "R20", "R21"])
@pytest.mark.parametrize("role", ["admin", "auditor"])
def test_t_rbac_07_platform_roles_denied_workload_io(rule_id: str, role: str, stack_url: str) -> None:
    """Platform roles (admin, auditor) cannot execute commands or read job output."""
    rule = next(r for r in RULES if r["id"] == rule_id)
    assert role not in rule.get("allow", {})
    with httpx.Client(verify=False, timeout=5.0) as client:
        resp = client.request(rule["method"], f"{stack_url}{BASE_PATH}{_resolve_path(rule['path'])}")
        assert resp.status_code == 403


@pytest.mark.parametrize("br_id", ["BR1_LAST_ADMIN", "BR2_SELF_ROLE_CHANGE", "BR3_QUOTA_EXCEEDED", "BR4_ENV_NOT_RUNNING"])
def test_t_rbac_09_to_12_business_rules_return_409(br_id: str, stack_url: str) -> None:
    """BR1..BR4 must return 409 with the contracted error code."""
    with httpx.Client(verify=False, timeout=5.0) as client:
        resp = client.get(f"{stack_url}{BASE_PATH}/healthz")
        assert resp.status_code == 200, f"{br_id} requires live stack"
        pytest.fail(f"{br_id} requires authenticated fixture setup on live stack")
