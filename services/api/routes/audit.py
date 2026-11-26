"""Audit routes: R24 list, R25 export NDJSON, R26 checkpoints, R27 pubkey, R28 verify."""

from __future__ import annotations

import hashlib
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Literal, cast

from core.abh_core.audit import GENESIS_PREV_HASH, canonical, merkle_root, record_hash
from core.abh_core.audit import append as audit_append
from core.abh_core.settings import Settings
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse

from services.api.authz import ScopedAuth, authorize
from services.api.middleware import ApiError
from services.api.schemas import AuditRecordOut, CheckpointOut, VerifyResultOut

router = APIRouter(prefix="/audit", tags=["audit"])

_BODY_KEYS = (
    "v", "seq", "ts", "actor_type", "actor_id", "actor_role", "team_id", "action",
    "target_type", "target_id", "outcome", "ip", "request_id", "detail", "prev_hash",
)


def _row_to_record(row: tuple[object, ...]) -> AuditRecordOut:
    return AuditRecordOut(
        v=int(cast(int, row[0])),
        seq=int(cast(int, row[1])),
        ts=str(row[2]),
        actor_type=cast(Literal["user", "service", "system"], str(row[3])),
        actor_id=str(row[4]),
        actor_role=str(row[5]),
        team_id=str(row[6]),
        action=str(row[7]),
        target_type=str(row[8]),
        target_id=str(row[9]),
        outcome=cast(Literal["success", "denied", "error"], str(row[10])),
        ip=str(row[11]),
        request_id=str(row[12]),
        detail=cast(dict[str, object], row[13]),
        prev_hash=str(row[14]),
        hash=str(row[15]),
    )


@router.get("")
def list_audit(
    auth: Annotated[ScopedAuth, Depends(authorize("R24"))],
    action: str | None = None,
    actor_id: str | None = None,
    outcome: str | None = None,
    from_seq: int | None = None,
    to_seq: int | None = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    cursor: int | None = None,
) -> dict[str, object]:
    where_parts = ["true"]
    params: list[object] = []
    if auth.scope == "team":
        where_parts.append("team_id = %s")
        params.append(str(auth.ctx.user.team_id or ""))
    for col, val in (("action", action), ("actor_id", actor_id), ("outcome", outcome)):
        if val is not None:
            where_parts.append(f"{col} = %s")
            params.append(val)
    if from_seq is not None:
        where_parts.append("seq >= %s")
        params.append(from_seq)
    if to_seq is not None:
        where_parts.append("seq <= %s")
        params.append(to_seq)
    if cursor is not None:
        where_parts.append("seq > %s")
        params.append(cursor)
    params.append(limit + 1)
    sql = f"SELECT {', '.join(_BODY_KEYS)}, hash FROM audit_log WHERE {' AND '.join(where_parts)} ORDER BY seq LIMIT %s"
    with auth.ctx.transaction() as conn, conn.cursor() as cur:
        cur.execute(sql, params)
        rows = cur.fetchall()
    has_more = len(rows) > limit
    items = [_row_to_record(r) for r in rows[:limit]]
    return {"items": items, "next_cursor": str(items[-1].seq) if has_more else None}


@router.get("/export")
def export_audit(
    auth: Annotated[ScopedAuth, Depends(authorize("R25"))],
    kind: Annotated[Literal["records", "checkpoints"], Query()] = "records",
) -> StreamingResponse:
    with auth.ctx.transaction() as conn:
        audit_append(
            conn,
            actor=auth.ctx.actor,
            action="audit.export",
            target_type="audit_log",
            target_id=kind,
            outcome="success",
            ip=auth.ctx.ip,
            request_id=auth.ctx.request_id,
            detail={"kind": kind},
        )
        with conn.cursor() as cur:
            if kind == "records":
                cur.execute(f"SELECT {', '.join(_BODY_KEYS)}, hash FROM audit_log ORDER BY seq ASC")
                lines = [_row_to_record(r).model_dump_json() + "\n" for r in cur.fetchall()]
            else:
                cur.execute(
                    "SELECT log_id, tree_size, root_hash, head_hash, ts, signature "
                    "FROM audit_checkpoint ORDER BY tree_size ASC"
                )
                lines = [
                    CheckpointOut(
                        v=1, log_id=str(r[0]), tree_size=int(cast(int, r[1])),
                        root_hash=str(r[2]), head_hash=str(r[3]), ts=str(r[4]), signature=str(r[5]),
                    ).model_dump_json() + "\n"
                    for r in cur.fetchall()
                ]

    def _iter() -> Iterator[str]:
        yield from lines

    return StreamingResponse(_iter(), media_type="application/x-ndjson")


@router.get("/checkpoints")
def list_checkpoints(_auth: Annotated[ScopedAuth, Depends(authorize("R26"))]) -> dict[str, list[CheckpointOut]]:
    with _auth.ctx.transaction() as conn, conn.cursor() as cur:
        cur.execute("SELECT log_id, tree_size, root_hash, head_hash, ts, signature FROM audit_checkpoint ORDER BY tree_size ASC")
        items = [
            CheckpointOut(
                v=1, log_id=str(r[0]), tree_size=int(cast(int, r[1])),
                root_hash=str(r[2]), head_hash=str(r[3]), ts=str(r[4]), signature=str(r[5]),
            )
            for r in cur.fetchall()
        ]
    return {"items": items}


def _read_pubkey_hex() -> str:
    p = Path(Settings().notary_pubkey_path)
    if not p.exists():
        raise ApiError("INTERNAL", 500, "Notary public key unavailable")
    return p.read_text(encoding="utf-8").strip()


@router.get("/pubkey")
def get_pubkey(_auth: Annotated[ScopedAuth, Depends(authorize("R27"))]) -> dict[str, str]:
    pubkey_hex = _read_pubkey_hex()
    log_id = hashlib.sha256(bytes.fromhex(pubkey_hex)).hexdigest()[:16]
    return {"public_key_hex": pubkey_hex, "log_id": log_id, "algorithm": "ed25519"}


@router.post("/verify", response_model=VerifyResultOut)
def verify_audit(auth: Annotated[ScopedAuth, Depends(authorize("R28"))]) -> VerifyResultOut:
    """Run steps 1-4 of docs/04_CONTRACTS.md sec 7.8 over DB using abh_core."""
    pubkey_hex = _read_pubkey_hex()
    pubkey = Ed25519PublicKey.from_public_bytes(bytes.fromhex(pubkey_hex))
    with auth.ctx.transaction() as conn, conn.cursor() as cur:
        cur.execute(f"SELECT {', '.join(_BODY_KEYS)}, hash FROM audit_log ORDER BY seq ASC")
        recs = [dict(zip((*_BODY_KEYS, "hash"), r, strict=True)) for r in cur.fetchall()]
        cur.execute("SELECT log_id, tree_size, root_hash, head_hash, ts, signature FROM audit_checkpoint ORDER BY tree_size ASC")
        cps = [
            {"v": 1, "log_id": r[0], "tree_size": r[1], "root_hash": r[2], "head_hash": r[3], "ts": r[4], "signature": r[5]}
            for r in cur.fetchall()
        ]
        verdict, at = "OK", None
        prev = GENESIS_PREV_HASH
        leaves: list[bytes] = []
        for idx, rec in enumerate(recs, start=1):
            if rec["seq"] != idx:
                verdict, at = "SEQ_GAP", idx
                break
            if rec["prev_hash"] != prev:
                verdict, at = "CHAIN_BREAK", idx
                break
            expected = record_hash({k: rec[k] for k in _BODY_KEYS})
            if rec["hash"] != expected:
                verdict, at = "HASH_MISMATCH", idx
                break
            prev = expected
            leaves.append(bytes.fromhex(expected))
        if verdict == "OK":
            for cp in cps:
                tsize = int(cast(int, cp["tree_size"]))
                cp_body = {k: cp[k] for k in ("v", "log_id", "tree_size", "root_hash", "head_hash", "ts")}
                try:
                    pubkey.verify(bytes.fromhex(str(cp["signature"])), canonical(cp_body))
                except (InvalidSignature, ValueError):
                    verdict, at = "BAD_SIGNATURE", tsize
                    break
                if tsize > len(leaves):
                    verdict, at = "TRUNCATED", tsize
                    break
                if merkle_root(leaves[:tsize]).hex() != cp["root_hash"] or leaves[tsize - 1].hex() != cp["head_hash"]:
                    verdict, at = "ROOT_MISMATCH", tsize
                    break
        last_cp_size = int(cast(int, cps[-1]["tree_size"])) if cps else 0
        audit_append(
            conn,
            actor=auth.ctx.actor,
            action="audit.verify",
            target_type="audit_log",
            target_id="ledger",
            outcome="success",
            ip=auth.ctx.ip,
            request_id=auth.ctx.request_id,
            detail={"verdict": verdict, "records": len(recs)},
        )
    return VerifyResultOut(
        ok=(verdict == "OK"),
        verdict=verdict,
        at=at,
        records=len(recs),
        checkpoints=len(cps),
        unanchored_tail=max(0, len(recs) - last_cp_size),
        checked_at=datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
    )
