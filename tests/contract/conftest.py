"""Shared fixtures for contract tests (Bhavya-owned)."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
CONTRACTS_DIR = REPO_ROOT / "contracts"


@pytest.fixture(scope="session")
def repo_root() -> Path:
    return REPO_ROOT


@pytest.fixture(scope="session")
def audit_vectors() -> dict[str, Any]:
    return json.loads((CONTRACTS_DIR / "audit_vectors.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def rbac_matrix() -> dict[str, Any]:
    return yaml.safe_load((CONTRACTS_DIR / "rbac_matrix.yaml").read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def stack_url() -> str:
    return os.environ.get("ABH_STACK_URL", "https://localhost")


@pytest.fixture(scope="session")
def fixture_users() -> dict[str, dict[str, str | None]]:
    """Fixture user definitions named by docs/06_VERIFICATION.md."""
    return {
        "admin": {"email": "admin@abhedya.local", "role": "admin", "team": None},
        "auditor": {"email": "auditor@abhedya.local", "role": "auditor", "team": None},
        "lead.alpha": {"email": "lead.alpha@abhedya.local", "role": "team_lead", "team": "alpha"},
        "analyst.alpha": {"email": "analyst.alpha@abhedya.local", "role": "analyst", "team": "alpha"},
        "analyst2.alpha": {"email": "analyst2.alpha@abhedya.local", "role": "analyst", "team": "alpha"},
        "lead.bravo": {"email": "lead.bravo@abhedya.local", "role": "team_lead", "team": "bravo"},
        "analyst.bravo": {"email": "analyst.bravo@abhedya.local", "role": "analyst", "team": "bravo"},
    }
