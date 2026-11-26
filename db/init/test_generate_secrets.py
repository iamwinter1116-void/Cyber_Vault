"""Tests for generated libpq service-role password files."""

from __future__ import annotations

import base64
from pathlib import Path

import pytest

from db.init import generate_secrets


def _password(byte: int) -> bytes:
    return base64.urlsafe_b64encode(bytes([byte]) * 32).rstrip(b"=")


def test_secret_generator_creates_role_specific_pgpass_files_and_is_idempotent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(generate_secrets, "SECRET_DIR", tmp_path)

    generate_secrets.main()
    first = {
        role: (tmp_path / f"{role}.pgpass").read_bytes()
        for role in generate_secrets.DB_NAMES[1:]
    }
    for role in generate_secrets.DB_NAMES[1:]:
        password = (tmp_path / role).read_bytes()
        assert first[role] == b"db:5432:abhedya:" + role.encode("ascii") + b":" + password + b"\n"

    generate_secrets.main()
    assert {
        role: (tmp_path / f"{role}.pgpass").read_bytes()
        for role in generate_secrets.DB_NAMES[1:]
    } == first
    output = capsys.readouterr().out.encode()
    assert all(secret not in output for secret in first.values())


def test_secret_generator_refuses_mismatched_pgpass_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(generate_secrets, "SECRET_DIR", tmp_path)
    generate_secrets.main()
    (tmp_path / "abh_api.pgpass").write_bytes(b"wrong\n")

    with pytest.raises(ValueError, match="does not match abh_api"):
        generate_secrets.main()


def test_secret_generator_refuses_invalid_service_password(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(generate_secrets, "SECRET_DIR", tmp_path)
    tmp_path.mkdir(exist_ok=True)
    (tmp_path / "abh_api").write_bytes(b"not-a-valid-generated-secret\n")

    with pytest.raises(ValueError, match="invalid password file: abh_api"):
        generate_secrets.ensure_pgpass_files()


def test_password_validation_requires_32_bytes_of_base64url() -> None:
    assert generate_secrets.valid_password(_password(7))
    assert not generate_secrets.valid_password(b"short")
    assert not generate_secrets.valid_password(b"!" * 43)
