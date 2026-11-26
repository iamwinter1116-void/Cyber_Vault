"""Unit tests for RBAC matrix loading and startup route coverage."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from fastapi import FastAPI

from services.api.authz import MATRIX, verify_route_coverage
from services.api.main import create_app
from services.api.openapi_export import dump_openapi


def test_matrix_has_31_rules_and_startup_passes(tmp_path: Path) -> None:
    assert len(MATRIX) == 31
    app = create_app()
    verify_route_coverage(app, require_all=True)
    out = tmp_path / "openapi.yaml"
    dump_openapi(out)
    doc = yaml.safe_load(out.read_text(encoding="utf-8"))
    ops = sum(
        1
        for p, m in doc["paths"].items()
        if p.startswith("/api/v1")
        for k in m
        if k in {"get", "post", "put", "patch", "delete"}
    )
    assert ops == 31


def test_unmapped_route_refused_at_startup() -> None:
    app = FastAPI()

    @app.get("/api/v1/unmapped")
    def _unmapped() -> dict[str, bool]:
        return {"ok": True}

    with pytest.raises(RuntimeError, match="rbac_matrix.yaml"):
        verify_route_coverage(app, require_all=False)
