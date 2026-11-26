"""Unit tests for RBAC matrix loading and startup route coverage."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from services.api.authz import MATRIX, verify_route_coverage
from services.api.main import create_app


def test_matrix_has_31_rules_and_startup_passes() -> None:
    assert len(MATRIX) == 31
    app = create_app()
    verify_route_coverage(app, require_all=True)


def test_unmapped_route_refused_at_startup() -> None:
    app = FastAPI()

    @app.get("/api/v1/unmapped")
    def _unmapped() -> dict[str, bool]:
        return {"ok": True}

    with pytest.raises(RuntimeError, match="rbac_matrix.yaml"):
        verify_route_coverage(app, require_all=False)
