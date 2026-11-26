"""Independent audit ledger verifier for abhedya-audit-v1."""
from __future__ import annotations
import argparse, hashlib, json, re, sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, NoReturn, Sequence
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

KEY_RE = re.compile(r"^[a-z0-9_]+$")
RECORD_KEYS = frozenset({
    "v", "seq", "ts", "actor_type", "actor_id", "actor_role", "team_id",
    "action", "target_type", "target_id", "outcome", "ip", "request_id", "detail", "prev_hash",
})
CP_KEYS = frozenset({"v", "log_id", "tree_size", "root_hash", "head_hash", "ts"})
GENESIS_PREV = "0" * 64


class InputError(ValueError):
    """Raised when CLI arguments or input files are malformed."""


def _validate(val: Any) -> None:
    if isinstance(val, bool) or isinstance(val, int) and abs(val) < (1 << 53):
        return
    if isinstance(val, str):
        if "\x00" in val:
            raise InputError("NUL character forbidden")
        return
    if isinstance(val, list):
        for item in val:
            _validate(item)
        return
    if isinstance(val, dict):
        for k, v in val.items():
            if not isinstance(k, str) or not KEY_RE.match(k):
                raise InputError(f"invalid key: {k!r}")
            _validate(v)
        return
    raise InputError(f"forbidden value type: {type(val).__name__}")


def canonical(obj: dict[str, Any]) -> bytes:
    """Return canonical UTF-8 JSON bytes per section 7.1."""
    _validate(obj)
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def record_hash(body: dict[str, Any]) -> str:
    """Return RFC 6962 leaf hash hex for an audit record body."""
    return hashlib.sha256(b"\x00" + canonical(body)).hexdigest()


def merkle_root(leaves: Sequence[bytes]) -> bytes:
    """Return RFC 6962 Merkle tree hash over raw 32-byte leaf hashes."""
    n = len(leaves)
    if n == 0:
        return hashlib.sha256(b"").digest()
    if n == 1:
        return leaves[0]
    k = 1 << ((n - 1).bit_length() - 1)
    return hashlib.sha256(b"\x01" + merkle_root(leaves[:k]) + merkle_root(leaves[k:])).digest()


def _load_ndjson(path: Path, expected_keys: frozenset[str], extra: str) -> list[dict[str, Any]]:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise InputError(f"cannot read {path}: {exc}") from exc
    items: list[dict[str, Any]] = []
    req = expected_keys | {extra}
    for lineno, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            continue
        try:
            obj = json.loads(line, parse_constant=lambda c: (_ for _ in ()).throw(InputError(c)))
        except json.JSONDecodeError as exc:
            raise InputError(f"{path}:{lineno}: invalid JSON: {exc}") from exc
        if not isinstance(obj, dict) or set(obj.keys()) != req:
            raise InputError(f"{path}:{lineno}: unexpected keys")
        _validate(obj)
        items.append(obj)
    return items


def _result(verdict: str, at: int | None, n_rec: int, n_cp: int, tail: int) -> dict[str, Any]:
    return {
        "ok": verdict == "OK", "verdict": verdict, "at": at,
        "records": n_rec, "checkpoints": n_cp, "unanchored_tail": tail,
        "checked_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


def verify_ledger(
    records: list[dict[str, Any]],
    checkpoints: list[dict[str, Any]],
    pubkey_hex: str,
    witness: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Run the 6-step verification algorithm (section 7.8)."""
    try:
        pub_bytes = bytes.fromhex(pubkey_hex)
        if len(pub_bytes) != 32:
            raise InputError("pubkey must be 32 bytes hex")
        pub = Ed25519PublicKey.from_public_bytes(pub_bytes)
    except ValueError as exc:
        raise InputError(f"invalid pubkey: {exc}") from exc

    n = len(records)
    cps = sorted(checkpoints, key=lambda c: int(c["tree_size"]))
    tail = n - (int(cps[-1]["tree_size"]) if cps else 0)
    leaves: list[bytes] = []
    prev = GENESIS_PREV

    for i, rec in enumerate(records, 1):
        if rec["seq"] != i or isinstance(rec["seq"], bool):
            return _result("SEQ_GAP", i, n, len(cps), tail)
        if rec["prev_hash"] != prev:
            return _result("CHAIN_BREAK", i, n, len(cps), tail)
        body = {k: rec[k] for k in RECORD_KEYS}
        expected = record_hash(body)
        if rec["hash"] != expected:
            return _result("HASH_MISMATCH", i, n, len(cps), tail)
        leaves.append(bytes.fromhex(expected))
        prev = expected

    for cp in cps:
        tsize = cp["tree_size"]
        if not isinstance(tsize, int) or isinstance(tsize, bool) or tsize < 0:
            raise InputError("invalid tree_size")
        cp_body = {k: cp[k] for k in CP_KEYS}
        try:
            pub.verify(bytes.fromhex(cp["signature"]), canonical(cp_body))
        except (InvalidSignature, ValueError):
            return _result("BAD_SIGNATURE", tsize, n, len(cps), tail)
        if tsize > n:
            return _result("TRUNCATED", tsize, n, len(cps), tail)
        exp_root = merkle_root(leaves[:tsize]).hex()
        exp_head = records[tsize - 1]["hash"] if tsize > 0 else GENESIS_PREV
        if cp["root_hash"] != exp_root or cp["head_hash"] != exp_head:
            return _result("ROOT_MISMATCH", tsize, n, len(cps), tail)

    if witness is not None:
        cp_set = {canonical(c) for c in cps}
        missing = [int(w["tree_size"]) for w in witness if canonical(w) not in cp_set]
        if missing:
            return _result("CHECKPOINT_REGRESSION", min(missing), n, len(cps), tail)

    return _result("OK", None, n, len(cps), tail)


class _Exit3Parser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        print(f"error: {message}", file=sys.stderr)
        sys.exit(3)


def main(argv: Sequence[str] | None = None) -> int:
    parser = _Exit3Parser(description="Verify abhedya-audit-v1 NDJSON ledger exports.")
    parser.add_argument("--records", required=True, type=Path)
    parser.add_argument("--checkpoints", required=True, type=Path)
    parser.add_argument("--pubkey", required=True)
    parser.add_argument("--witness", type=Path, default=None)
    args = parser.parse_args(argv)
    try:
        recs = _load_ndjson(args.records, RECORD_KEYS, "hash")
        cps = _load_ndjson(args.checkpoints, CP_KEYS, "signature")
        wit = _load_ndjson(args.witness, CP_KEYS, "signature") if args.witness else None
        res = verify_ledger(recs, cps, args.pubkey, wit)
    except InputError as exc:
        print(f"input error: {exc}", file=sys.stderr)
        return 3
    print(json.dumps(res, separators=(",", ":")))
    return 0 if res["ok"] else 2


if __name__ == "__main__":
    sys.exit(main())
