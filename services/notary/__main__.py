"""Audit notary: genesis record, incremental tamper check, signed checkpoints, witness fsync."""

from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path
from typing import cast

import psycopg
from core.abh_core.audit import (
    GENESIS_PREV_HASH,
    Actor,
    canonical,
    merkle_root,
    record_hash,
)
from core.abh_core.audit import append as audit_append
from core.abh_core.db import create_pool
from core.abh_core.settings import Settings
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

_BODY_KEYS = (
    "v", "seq", "ts", "actor_type", "actor_id", "actor_role", "team_id", "action",
    "target_type", "target_id", "outcome", "ip", "request_id", "detail", "prev_hash",
)


def load_witness(path: Path) -> list[dict[str, object]]:
    if not path.exists():
        return []
    lines = [ln.strip() for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    return [cast(dict[str, object], json.loads(ln)) for ln in lines]


def verify_ledger_state(
    records: list[dict[str, object]],
    db_cps: list[dict[str, object]],
    witness_cps: list[dict[str, object]],
    pubkey: Ed25519PublicKey,
) -> tuple[str, int | None]:
    """Run verification steps 1-5 on records, DB checkpoints, and witness."""
    prev = GENESIS_PREV_HASH
    leaves: list[bytes] = []
    for idx, rec in enumerate(records, start=1):
        if rec.get("seq") != idx:
            return "SEQ_GAP", idx
        if rec.get("prev_hash") != prev:
            return "CHAIN_BREAK", idx
        body = {k: rec[k] for k in _BODY_KEYS}
        expected_hash = record_hash(body)
        if rec.get("hash") != expected_hash:
            return "HASH_MISMATCH", idx
        prev = expected_hash
        leaves.append(bytes.fromhex(expected_hash))

    db_by_size = {int(cast(int, cp["tree_size"])): cp for cp in db_cps}
    for wcp in witness_cps:
        tsize = int(cast(int, wcp["tree_size"]))
        if db_by_size.get(tsize) != wcp:
            return "CHECKPOINT_REGRESSION", tsize

    for cp in sorted(db_cps, key=lambda c: int(cast(int, c["tree_size"]))):
        tsize = int(cast(int, cp["tree_size"]))
        cp_body = {k: cp[k] for k in ("v", "log_id", "tree_size", "root_hash", "head_hash", "ts")}
        try:
            pubkey.verify(bytes.fromhex(str(cp["signature"])), canonical(cp_body))
        except (InvalidSignature, ValueError):
            return "BAD_SIGNATURE", tsize
        if tsize > len(leaves):
            return "TRUNCATED", tsize
        if merkle_root(leaves[:tsize]).hex() != cp["root_hash"] or leaves[tsize - 1].hex() != cp["head_hash"]:
            return "ROOT_MISMATCH", tsize
    return "OK", None


def run_tick(
    conn: psycopg.Connection[tuple[object, ...]],
    key: Ed25519PrivateKey,
    log_id: str,
    witness_path: Path,
    *,
    every_n: int,
    every_sec: int,
    last_cp_monotonic: float,
) -> tuple[bool, float]:
    """Run one notary verification + optional checkpoint cycle. Returns (ok, last_cp_monotonic)."""
    with conn.cursor() as cur:
        cur.execute(
            f"SELECT {', '.join(_BODY_KEYS)}, hash FROM audit_log ORDER BY seq ASC"
        )
        records = [dict(zip((*_BODY_KEYS, "hash"), r, strict=True)) for r in cur.fetchall()]
        if not records:
            audit_append(
                conn, actor=Actor(type="system", id="notary"),
                action="audit.genesis", target_type="audit_log", target_id=log_id, outcome="success",
            )
            return True, last_cp_monotonic
        cur.execute("SELECT log_id, tree_size, root_hash, head_hash, ts, signature FROM audit_checkpoint ORDER BY tree_size ASC")
        db_cps = [
            {"v": 1, "log_id": r[0], "tree_size": r[1], "root_hash": r[2], "head_hash": r[3], "ts": r[4], "signature": r[5]}
            for r in cur.fetchall()
        ]

    witness_cps = load_witness(witness_path)
    verdict, at = verify_ledger_state(records, db_cps, witness_cps, key.public_key())
    if verdict != "OK":
        detail: dict[str, object] = {"verdict": verdict}
        if at is not None:
            detail["at"] = at
        audit_append(
            conn, actor=Actor(type="system", id="notary"),
            action="audit.tamper_detected", target_type="audit_log", target_id=log_id, outcome="error", detail=detail,
        )
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO activity_event (severity, kind, message, data) VALUES ('critical', 'alert.tamper_detected', %s, %s::jsonb)",
                (f"Audit tamper detected: {verdict} at {at}", json.dumps(detail)),
            )
        return False, last_cp_monotonic

    last_size = int(cast(int, db_cps[-1]["tree_size"])) if db_cps else 0
    new_count = len(records) - last_size
    elapsed = time.monotonic() - last_cp_monotonic
    if new_count >= every_n or (new_count >= 1 and elapsed >= every_sec):
        leaves = [bytes.fromhex(str(r["hash"])) for r in records]
        with conn.cursor() as cur:
            cur.execute("SELECT to_char(clock_timestamp() AT TIME ZONE 'UTC', 'YYYY-MM-DD\"T\"HH24:MI:SS.US\"Z\"')")
            ts_row = cur.fetchone()
            assert ts_row is not None
            ts = str(ts_row[0])
            cp_body: dict[str, object] = {
                "v": 1, "log_id": log_id, "tree_size": len(records),
                "root_hash": merkle_root(leaves).hex(), "head_hash": leaves[-1].hex(), "ts": ts,
            }
            sig = key.sign(canonical(cp_body)).hex()
            cur.execute(
                "INSERT INTO audit_checkpoint (tree_size, root_hash, head_hash, ts, log_id, signature) "
                "VALUES (%s, %s, %s, %s, %s, %s)",
                (cp_body["tree_size"], cp_body["root_hash"], cp_body["head_hash"], ts, log_id, sig),
            )
        witness_path.parent.mkdir(parents=True, exist_ok=True)
        with witness_path.open("a", encoding="utf-8") as wf:
            wf.write(json.dumps({**cp_body, "signature": sig}, sort_keys=True, separators=(",", ":")) + "\n")
            wf.flush()
            os.fsync(wf.fileno())
        return True, time.monotonic()
    return True, last_cp_monotonic


def main() -> None:
    cfg = Settings()
    seed = Path(cfg.notary_key_path).read_bytes()[:32]
    key = Ed25519PrivateKey.from_private_bytes(seed)
    log_id = hashlib.sha256(key.public_key().public_bytes_raw()).hexdigest()[:16]
    witness_path = Path(cfg.witness_path)
    pool = create_pool(cfg.db_dsn, min_size=1, max_size=2)
    last_cp = time.monotonic()
    halted = False
    try:
        while not halted:
            with pool.connection() as conn, conn.transaction():
                ok, last_cp = run_tick(
                    conn, key, log_id, witness_path,
                    every_n=cfg.checkpoint_every_n, every_sec=cfg.checkpoint_every_sec, last_cp_monotonic=last_cp,
                )
                if not ok:
                    halted = True
            if not halted:
                time.sleep(5)
    finally:
        pool.close()


if __name__ == "__main__":
    main()
