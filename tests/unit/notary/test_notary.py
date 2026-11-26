"""Unit tests for notary verification against frozen audit vectors."""

from __future__ import annotations

import json
from pathlib import Path
from typing import cast

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from services.notary.__main__ import verify_ledger_state

VECTORS_PATH = Path(__file__).resolve().parents[3] / "contracts" / "audit_vectors.json"


def _vector_records_and_cps() -> tuple[list[dict[str, object]], list[dict[str, object]], Ed25519PrivateKey]:
    raw = cast(dict[str, object], json.loads(VECTORS_PATH.read_text(encoding="utf-8")))
    recs = [
        {**cast(dict[str, object], r["body"]), "hash": r["hash"]}
        for r in cast(list[dict[str, object]], raw["records"])
    ]
    cps = [
        {**cast(dict[str, object], c["body"]), "signature": c["signature"]}
        for c in cast(list[dict[str, object]], raw["checkpoints"])
    ]
    key = Ed25519PrivateKey.from_private_bytes(bytes.fromhex(cast(str, raw["test_private_key_hex"])))
    return recs, cps, key


def test_notary_verifies_untouched_vectors() -> None:
    recs, cps, key = _vector_records_and_cps()
    assert verify_ledger_state(recs, cps, cps, key.public_key()) == ("OK", None)


def test_notary_detects_tamper_modes() -> None:
    recs, cps, key = _vector_records_and_cps()
    pub = key.public_key()

    edited = [dict(r) for r in recs]
    edited[3]["outcome"] = "success"
    assert verify_ledger_state(edited, cps, cps, pub) == ("HASH_MISMATCH", 4)

    gapped = [r for r in recs if r["seq"] != 3]
    assert verify_ledger_state(gapped, cps, cps, pub) == ("SEQ_GAP", 3)

    assert verify_ledger_state(recs, [], cps, pub) == ("CHECKPOINT_REGRESSION", 3)

    bad_cp = [dict(c) for c in cps]
    bad_cp[1]["root_hash"] = "0" * 64
    assert verify_ledger_state(recs, bad_cp, bad_cp, pub) == ("BAD_SIGNATURE", 5)

    assert verify_ledger_state(recs[:3], cps, cps, pub) == ("TRUNCATED", 5)
