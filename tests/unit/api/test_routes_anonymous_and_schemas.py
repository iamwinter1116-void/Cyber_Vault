"""Real TestClient checks for anonymous 401 enforcement and headers across all protected routes."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from services.api.main import create_app

_UUID = "11111111-1111-4111-8111-111111111111"

_PROTECTED_ROUTES: list[tuple[str, str]] = [
    ("POST", "/api/v1/auth/logout"),
    ("GET", "/api/v1/auth/me"),
    ("GET", "/api/v1/users"),
    ("POST", "/api/v1/users"),
    ("PATCH", f"/api/v1/users/{_UUID}"),
    ("GET", "/api/v1/teams"),
    ("POST", "/api/v1/teams"),
    ("PATCH", f"/api/v1/teams/{_UUID}"),
    ("GET", "/api/v1/templates"),
    ("GET", "/api/v1/envs"),
    ("POST", "/api/v1/envs"),
    ("GET", f"/api/v1/envs/{_UUID}"),
    ("POST", f"/api/v1/envs/{_UUID}/stop"),
    ("DELETE", f"/api/v1/envs/{_UUID}"),
    ("GET", f"/api/v1/envs/{_UUID}/metrics"),
    ("POST", f"/api/v1/envs/{_UUID}/exec"),
    ("GET", "/api/v1/jobs"),
    ("GET", f"/api/v1/jobs/{_UUID}"),
    ("POST", "/api/v1/files"),
    ("POST", "/api/v1/ai-scans"),
    ("GET", "/api/v1/stream"),
    ("GET", "/api/v1/events"),
    ("GET", "/api/v1/audit"),
    ("GET", "/api/v1/audit/export"),
    ("GET", "/api/v1/audit/checkpoints"),
    ("GET", "/api/v1/audit/pubkey"),
    ("POST", "/api/v1/audit/verify"),
    ("GET", "/api/v1/admin/overview"),
    ("POST", "/api/v1/admin/kill-switch"),
]


@pytest.mark.parametrize(("method", "path"), _PROTECTED_ROUTES)
def test_protected_routes_require_session_and_set_security_headers(method: str, path: str) -> None:
    client = TestClient(create_app())
    resp = client.request(method, path)
    assert resp.status_code == 401
    body = resp.json()
    assert body["error"]["code"] == "UNAUTHENTICATED"
    assert body["error"]["request_id"] == resp.headers["X-Request-ID"]
    assert resp.headers["Content-Security-Policy"] == "default-src 'self'"
    assert resp.headers["X-Content-Type-Options"] == "nosniff"
    assert resp.headers["Referrer-Policy"] == "no-referrer"
    assert resp.headers["Cache-Control"] == "no-store"
