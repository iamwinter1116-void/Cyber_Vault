"""abhedya-audit-v1 canonicalization, hashing, Merkle roots, and DB append."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Literal

import psycopg

Outcome = Literal["success", "denied", "error"]

ADVISORY_LOCK_ID = 4242001
GENESIS_PREV_HASH = "0" * 64
MAX_DETAIL_BYTES = 2048
MAX_INT_ABS = 1 << 53
_KEY_RE = re.compile(r"^[a-z0-9_]+$")

ACTIONS: frozenset[str] = frozenset({
    "auth.login", "auth.logout", "user.create", "user.update",
    "team.create", "team.quota_update", "env.create", "env.stop",
    "env.destroy", "env.exec", "file.submit", "ai.scan_start",
    "audit.export", "audit.verify", "admin.kill_switch", "authz.denied",
    "audit.genesis", "audit.tamper_detected", "auth.lockout",
    "env.provisioned", "env.stopped", "env.destroyed", "env.expired",
    "env.failed", "env.oom_killed", "job.finished", "isolation.degraded",
})


@dataclass(frozen=True)
class Actor:
    """Actor identity recorded in an audit_log entry."""

    type: Literal["user", "service", "system"]
    id: str
    role: str = ""
    team_id: str = ""


def _validate_value(val: object) -> None:
    if isinstance(val, bool):
        return
    if isinstance(val, int):
        if abs(val) >= MAX_INT_ABS:
            raise ValueError("integer exceeds 2^53 bound")
        return
    if isinstance(val, str):
        if "\x00" in val:
            raise ValueError("NUL character forbidden in string")
        return
    if isinstance(val, Mapping):
        for k, v in val.items():
            if not isinstance(k, str) or "\x00" in k or not _KEY_RE.match(k):
                raise ValueError(f"invalid object key: {k!r}")
            _validate_value(v)
        return
    if isinstance(val, Sequence) and not isinstance(val, (bytes, bytearray)):
        for item in val:
            _validate_value(item)
        return
    raise ValueError(f"forbidden value type: {type(val).__name__}")


def canonical(obj: Mapping[str, object]) -> bytes:
    """Serialize a mapping to abhedya-audit-v1 canonical UTF-8 JSON bytes."""
    _validate_value(obj)
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def record_hash(body: Mapping[str, object]) -> str:
    """Compute hex(SHA-256(0x00 || canonical(body))) for a record body."""
    return hashlib.sha256(b"\x00" + canonical(body)).hexdigest()


def merkle_root(leaf_hashes: Sequence[bytes]) -> bytes:
    """Compute RFC 6962 section 2.1 Merkle tree hash over 32-byte leaf hashes."""
    n = len(leaf_hashes)
    if n == 0:
        return hashlib.sha256(b"").digest()
    if n == 1:
        if len(leaf_hashes[0]) != 32:
            raise ValueError("leaf hash must be 32 bytes")
        return leaf_hashes[0]
    k = 1 << ((n - 1).bit_length() - 1)
    return hashlib.sha256(b"\x01" + merkle_root(leaf_hashes[:k]) + merkle_root(leaf_hashes[k:])).digest()


def append(
    conn: psycopg.Connection[tuple[object, ...]],
    *,
    actor: Actor,
    action: str,
    target_type: str,
    target_id: str,
    outcome: Outcome,
    ip: str = "",
    request_id: str = "",
    detail: Mapping[str, object] | None = None,
) -> int:
    """Append one audit_log row inside the caller's transaction and return seq."""
    if action not in ACTIONS:
        raise ValueError(f"unknown audit action: {action!r}")
    detail_obj: Mapping[str, object] = {} if detail is None else detail
    detail_bytes = canonical(detail_obj)
    if len(detail_bytes) > MAX_DETAIL_BYTES:
        raise ValueError(f"detail exceeds {MAX_DETAIL_BYTES} canonical bytes")

    with conn.cursor() as cur:
        cur.execute("SELECT pg_advisory_xact_lock(%s)", (ADVISORY_LOCK_ID,))
        cur.execute("SELECT seq, hash FROM audit_log ORDER BY seq DESC LIMIT 1")
        tail = cur.fetchone()
        if tail is None:
            seq = 1
            prev_hash = GENESIS_PREV_HASH
        else:
            if not isinstance(tail[0], int) or not isinstance(tail[1], str):
                raise RuntimeError("unexpected audit_log tail row types")
            seq = tail[0] + 1
            prev_hash = tail[1]
        cur.execute("SELECT to_char(clock_timestamp() AT TIME ZONE 'UTC', 'YYYY-MM-DD\"T\"HH24:MI:SS.US\"Z\"')")
        ts_row = cur.fetchone()
        if ts_row is None or not isinstance(ts_row[0], str):
            raise RuntimeError("failed to read database clock_timestamp")
        ts = ts_row[0]
        body: dict[str, object] = {
            "v": 1, "seq": seq, "ts": ts,
            "actor_type": actor.type, "actor_id": actor.id,
            "actor_role": actor.role, "team_id": actor.team_id,
            "action": action, "target_type": target_type, "target_id": target_id,
            "outcome": outcome, "ip": ip, "request_id": request_id,
            "detail": detail_obj, "prev_hash": prev_hash,
        }
        rec_hash = record_hash(body)
        cur.execute(
            "INSERT INTO audit_log (v, seq, ts, actor_type, actor_id, actor_role, team_id, "
            "action, target_type, target_id, outcome, ip, request_id, detail, prev_hash, hash) "
            "VALUES (1, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s)",
            (
                seq, ts, actor.type, actor.id, actor.role, actor.team_id,
                action, target_type, target_id, outcome, ip, request_id,
                detail_bytes.decode("utf-8"), prev_hash, rec_hash,
            ),
        )
    return seq
