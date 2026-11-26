"""Create local database credentials and the Ed25519 notary key pair once."""

from __future__ import annotations

import base64
import os
import re
import secrets
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

SECRET_DIR = Path(__file__).resolve().parents[2] / "secrets"
DB_NAMES = ("db_owner", "abh_api", "abh_runner", "abh_notary")


def create_once(path: Path, value: bytes) -> None:
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as output:
        output.write(value)


def valid_password(data: bytes) -> bool:
    token = data.rstrip(b"\r\n")
    if re.fullmatch(rb"[A-Za-z0-9_-]{43}", token) is None:
        return False
    return len(base64.urlsafe_b64decode(token + b"=")) == 32


def ensure_pgpass_files() -> None:
    """Create least-privilege libpq password files for Compose services."""
    for role in DB_NAMES[1:]:
        password = (SECRET_DIR / role).read_bytes().rstrip(b"\r\n")
        if not valid_password(password):
            raise ValueError(f"invalid password file: {role}")
        content = b"db:5432:abhedya:" + role.encode("ascii") + b":" + password + b"\n"
        path = SECRET_DIR / f"{role}.pgpass"
        if path.exists():
            if path.read_bytes() != content:
                raise ValueError(f"libpq password file does not match {role}")
        else:
            create_once(path, content)


def main() -> None:
    SECRET_DIR.mkdir(mode=0o700, exist_ok=True)
    for name in DB_NAMES:
        path = SECRET_DIR / name
        if not path.exists():
            create_once(path, base64.urlsafe_b64encode(secrets.token_bytes(32)).rstrip(b"="))
        if not valid_password(path.read_bytes()):
            raise ValueError(f"invalid password file: {name}")
    ensure_pgpass_files()

    seed_path = SECRET_DIR / "notary_ed25519"
    pub_path = SECRET_DIR / "notary_ed25519.pub"
    if pub_path.exists() and not seed_path.exists():
        raise ValueError("public key exists without the private seed")
    if not seed_path.exists():
        create_once(seed_path, secrets.token_bytes(32))
    seed = seed_path.read_bytes()
    if len(seed) != 32:
        raise ValueError("notary seed must be exactly 32 bytes")
    key = Ed25519PrivateKey.from_private_bytes(seed)
    expected = key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw).hex().encode("ascii")
    if not pub_path.exists():
        create_once(pub_path, expected + b"\n")
    if pub_path.read_bytes().strip() != expected:
        raise ValueError("notary public key does not match its private seed")
    print("Six base secrets and three role-specific libpq password files are present; existing credentials were preserved.")


if __name__ == "__main__":
    main()
