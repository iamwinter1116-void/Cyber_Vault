"""OpenAPI schema conformance test: T-API-01 (docs/06_VERIFICATION.md section 3)."""
from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
OPENAPI_PATH = REPO_ROOT / "contracts" / "openapi.yaml"


def test_t_api_01_openapi_schema_conformance(stack_url: str) -> None:
    """T-API-01: contracts/openapi.yaml exists and Schemathesis finds zero 5xx or schema violations."""
    assert OPENAPI_PATH.exists(), "contracts/openapi.yaml not generated yet (blocked on G0 make openapi)"
    import schemathesis

    schema = schemathesis.from_path(str(OPENAPI_PATH), base_url=f"{stack_url}/api/v1")
    for op in schema.get_all_operations():
        res = op.ok()
        case = res.case_cls(op) if hasattr(res, "case_cls") else op.make_case()
        resp = case.call(verify=False)
        assert resp.status_code < 500
        case.validate_response(resp)
