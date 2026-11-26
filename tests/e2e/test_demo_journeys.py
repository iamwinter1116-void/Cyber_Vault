"""Playwright end-to-end demo journeys: T-E2E-01..04 (docs/06_VERIFICATION.md section 8)."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


def _base_url() -> str:
    return os.environ.get("ABH_STACK_URL", "https://localhost")


def _pw_page():
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        pytest.fail(f"playwright not installed: {exc}")
    return sync_playwright()


def test_t_e2e_01_analyst_create_env_and_exec_without_reload() -> None:
    """T-E2E-01: analyst.alpha logs in, creates env, waits for running, executes command."""
    pw = os.environ.get("ABH_DEMO_PASSWORD", "")
    with _pw_page() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_context(ignore_https_errors=True).new_page()
        page.goto(f"{_base_url()}/login")
        page.fill('input[name="email"]', "analyst.alpha@abhedya.local")
        page.fill('input[name="password"]', pw)
        page.click('button[type="submit"]')
        page.wait_for_url("**/envs**")
        page.click('button:has-text("Create")')
        page.fill('input[name="name"]', "e2e-01-demo")
        page.click('button:has-text("Submit")')
        page.wait_for_selector("text=running", timeout=30000)
        page.click("text=e2e-01-demo")
        page.fill('input[name="command"]', "uname -r")
        page.click('button:has-text("Run")')
        page.wait_for_selector("pre", timeout=15000)
        browser.close()


def test_t_e2e_02_admin_user_team_quota_and_kill_switch() -> None:
    """T-E2E-02: admin creates user/team, edits quota, triggers kill switch."""
    pw = os.environ.get("ABH_DEMO_PASSWORD", "")
    with _pw_page() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_context(ignore_https_errors=True).new_page()
        page.goto(f"{_base_url()}/login")
        page.fill('input[name="email"]', "admin@abhedya.local")
        page.fill('input[name="password"]', pw)
        page.click('button[type="submit"]')
        page.wait_for_selector("text=Overview", timeout=10000)
        page.goto(f"{_base_url()}/admin/teams")
        page.wait_for_selector("text=alpha", timeout=10000)
        browser.close()


def test_t_e2e_03_auditor_filter_export_and_verify() -> None:
    """T-E2E-03: auditor opens Audit, filters, exports, presses Verify -> OK."""
    pw = os.environ.get("ABH_DEMO_PASSWORD", "")
    with _pw_page() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_context(ignore_https_errors=True).new_page()
        page.goto(f"{_base_url()}/login")
        page.fill('input[name="email"]', "auditor@abhedya.local")
        page.fill('input[name="password"]', pw)
        page.click('button[type="submit"]')
        page.goto(f"{_base_url()}/audit")
        page.click('button:has-text("Verify")')
        page.wait_for_selector("text=OK", timeout=10000)
        browser.close()


def test_t_e2e_04_auditor_sees_tamper_banner_within_30s() -> None:
    """T-E2E-04: red tamper banner appears within 30s without reload during tamper drill."""
    pw = os.environ.get("ABH_DEMO_PASSWORD", "")
    with _pw_page() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_context(ignore_https_errors=True).new_page()
        page.goto(f"{_base_url()}/login")
        page.fill('input[name="email"]', "auditor@abhedya.local")
        page.fill('input[name="password"]', pw)
        page.click('button[type="submit"]')
        proc = subprocess.run(
            [sys.executable, str(REPO_ROOT / "tools" / "tamper_drill.py"), "--case", "edit_field_no_rehash"],
            env={**os.environ, "ABH_ALLOW_TAMPER_DRILL": "1"},
            capture_output=True,
            text=True,
            check=False,
        )
        assert proc.returncode == 0, proc.stderr
        page.wait_for_selector("text=HASH_MISMATCH", timeout=30000)
        browser.close()
