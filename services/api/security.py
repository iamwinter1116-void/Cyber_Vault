"""Argon2id password hashing and CSPRNG session/CSRF token helpers."""

from __future__ import annotations

import hashlib
import secrets

from argon2 import PasswordHasher, Type
from argon2.exceptions import InvalidHashError, VerifyMismatchError

_HASHER = PasswordHasher(
    time_cost=2,
    memory_cost=19456,
    parallelism=1,
    hash_len=32,
    salt_len=16,
    type=Type.ID,
)
_DUMMY_HASH = _HASHER.hash("abhedya-dummy-constant-path-password")


def hash_password(password: str) -> str:
    """Hash a plaintext password using Argon2id (m>=19456 KiB, t>=2, p>=1)."""
    return _HASHER.hash(password)


def verify_password(password: str, stored_hash: str) -> tuple[bool, bool]:
    """Verify password against stored Argon2id hash. Returns (valid, needs_rehash)."""
    try:
        ok = _HASHER.verify(stored_hash, password)
    except (VerifyMismatchError, InvalidHashError):
        return False, False
    return ok, _HASHER.check_needs_rehash(stored_hash)


def verify_dummy(password: str) -> None:
    """Run Argon2id verification on a dummy hash to equalize unknown-email timing."""
    verify_password(password, _DUMMY_HASH)


def generate_session_token() -> str:
    """Generate 32 random bytes from OS CSPRNG as URL-safe base64."""
    return secrets.token_urlsafe(32)


def hash_session_token(raw_token: str) -> str:
    """Return SHA-256 hex digest of a raw session token."""
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def generate_csrf_token() -> str:
    """Generate a per-session CSRF token from OS CSPRNG."""
    return secrets.token_urlsafe(32)
