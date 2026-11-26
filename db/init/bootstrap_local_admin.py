"""Create the first local website administrator in an empty ABHEDYA database."""

from __future__ import annotations

import argparse
import re
import secrets

import psycopg

from core.abh_core.audit import Actor
from core.abh_core.audit import append as audit_append
from db.init.generate_secrets import SECRET_DIR, create_once, valid_password
from services.api.security import hash_password, verify_password

ADMIN_EMAIL = "admin@abhedya.local"
ADMIN_CREDENTIALS = SECRET_DIR / "local_admin.txt"


def read_password() -> str:
    """Read the persisted first-admin password without printing its value."""
    if ADMIN_CREDENTIALS.exists():
        lines = ADMIN_CREDENTIALS.read_bytes().splitlines()
        if len(lines) != 2 or lines[0].decode("ascii", errors="strict") != ADMIN_EMAIL:
            raise ValueError("local admin credential file has an invalid format")
        if not valid_password(lines[1]):
            raise ValueError("local admin credential file has an invalid password")
        return lines[1].decode("ascii")
    raise RuntimeError("local admin credential file is missing")


def load_or_create_password() -> str:
    """Reuse a prior interrupted bootstrap or generate one persisted password."""
    if ADMIN_CREDENTIALS.exists():
        return read_password()
    password = secrets.token_urlsafe(32)
    payload = f"{ADMIN_EMAIL}\n{password}\n".encode("ascii")
    create_once(ADMIN_CREDENTIALS, payload)
    return password


def bootstrap(*, host: str, port: int, database: str) -> str:
    """Create one admin only when the database has no users; return result label."""
    if host not in {"127.0.0.1", "localhost", "::1"}:
        raise ValueError("local admin bootstrap accepts loopback database hosts only")
    owner_secret = (SECRET_DIR / "db_owner").read_bytes().strip()
    if not valid_password(owner_secret):
        raise ValueError("invalid database owner password file")
    if not re.fullmatch(r"[A-Za-z0-9_.-]{1,63}", database):
        raise ValueError("database name contains unsupported characters")

    password = load_or_create_password()
    dsn = psycopg.conninfo.make_conninfo(
        host=host,
        port=port,
        dbname=database,
        user="postgres",
        password=owner_secret.decode("ascii"),
        connect_timeout=5,
    )
    with psycopg.connect(dsn) as conn, conn.cursor() as cur:
        cur.execute("SELECT password_hash, role FROM app_user WHERE email = %s", (ADMIN_EMAIL,))
        existing = cur.fetchone()
        if existing is not None:
            if str(existing[1]) != "admin":
                raise RuntimeError("local admin email is already assigned a non-admin role")
            if verify_password(read_password(), str(existing[0]))[0]:
                return "already-present"
            raise RuntimeError("local admin exists but its credential file does not match; refusing reset")

        cur.execute("SELECT count(*) FROM app_user")
        count_row = cur.fetchone()
        if count_row is None or int(count_row[0]) != 0:
            raise RuntimeError("database already has users; refusing to add or reset a bootstrap administrator")

        password = load_or_create_password()
        cur.execute(
            "INSERT INTO app_user (email, password_hash, role, team_id) "
            "VALUES (%s, %s, 'admin', NULL) RETURNING id",
            (ADMIN_EMAIL, hash_password(password)),
        )
        user_row = cur.fetchone()
        if user_row is None:
            raise RuntimeError("database did not return the new administrator id")
        audit_append(
            conn,
            actor=Actor(type="system", id="local-bootstrap"),
            action="user.create",
            target_type="user",
            target_id=str(user_row[0]),
            outcome="success",
            detail={"role": "admin"},
        )
    return "created"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=15432)
    parser.add_argument("--database", default="abhedya")
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error("--port must be between 1 and 65535")
    try:
        result = bootstrap(host=args.host, port=args.port, database=args.database)
    except (OSError, ValueError, RuntimeError, psycopg.Error) as exc:
        parser.exit(1, f"local admin bootstrap refused: {exc}\n")
    print(f"local admin {result}; email={ADMIN_EMAIL}; credential_file={ADMIN_CREDENTIALS}")
    print("The generated password is stored in that ignored file and was not printed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
