"""Unit tests for API schemas, middleware, security helpers, and healthz."""

from __future__ import annotations

import base64

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from services.api.main import create_app
from services.api.schemas import EnvCreate, LoginRequest
from services.api.security import (
    generate_session_token,
    hash_password,
    hash_session_token,
    verify_dummy,
    verify_password,
)


def test_input_schemas_forbid_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        LoginRequest.model_validate({"email": "a@b.c", "password": "secret", "extra": 1})
    with pytest.raises(ValidationError):
        EnvCreate.model_validate({"name": "lab-1", "template": "file-analysis", "size": "S"})


def test_argon2id_and_session_tokens() -> None:
    phc = hash_password("correct-horse-battery-staple")
    assert phc.startswith("$argon2id$")
    assert "m=19456,t=2,p=1" in phc
    ok, rehash = verify_password("correct-horse-battery-staple", phc)
    assert ok is True
    assert rehash is False
    bad, _ = verify_password("wrong", phc)
    assert bad is False
    verify_dummy("anything")

    tok = generate_session_token()
    raw = base64.urlsafe_b64decode(tok + "==")
    assert len(raw) == 32
    digest = hash_session_token(tok)
    assert len(digest) == 64


def test_healthz_headers_and_error_envelopes() -> None:
    app = create_app()

    @app.get("/api/v1/_boom")
    def _boom() -> dict[str, str]:
        raise RuntimeError("secret stack trace")

    client = TestClient(app, raise_server_exceptions=False)
    r = client.get("/api/v1/healthz")
    assert r.status_code == 200
    assert r.json() == {"status": "ok", "db": False}
    assert r.headers["X-Request-ID"]
    assert r.headers["Content-Security-Policy"] == "default-src 'self'"
    assert r.headers["X-Content-Type-Options"] == "nosniff"
    assert r.headers["Referrer-Policy"] == "no-referrer"
    assert r.headers["Cache-Control"] == "no-store"

    r422 = client.post("/api/v1/auth/login", json={"email": "x", "password": "y", "unknown": 1})
    assert r422.status_code == 422
    assert r422.json()["error"]["code"] == "VALIDATION"
    assert r422.json()["error"]["request_id"] == r422.headers["X-Request-ID"]

    r401 = client.get("/api/v1/auth/me")
    assert r401.status_code == 401
    assert r401.json()["error"]["code"] == "UNAUTHENTICATED"

    r500 = client.get("/api/v1/_boom")
    assert r500.status_code == 500
    assert r500.json()["error"]["code"] == "INTERNAL"
    assert "secret stack trace" not in r500.text
