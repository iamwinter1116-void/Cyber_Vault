"""Unit and known-answer vector tests for core.abh_core."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import cast

import pytest
from core.abh_core.audit import (
    ACTIONS,
    Actor,
    append,
    canonical,
    merkle_root,
    record_hash,
)
from core.abh_core.db import create_pool
from core.abh_core.settings import Settings
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

VECTORS_PATH = Path(__file__).resolve().parents[3] / "contracts" / "audit_vectors.json"


def _load_vectors() -> dict[str, object]:
    return cast(dict[str, object], json.loads(VECTORS_PATH.read_text(encoding="utf-8")))


def test_vectors_canonical_and_record_hash() -> None:
    vectors = _load_vectors()
    records = cast(list[dict[str, object]], vectors["records"])
    for rec in records:
        body = cast(dict[str, object], rec["body"])
        expected_canon = cast(str, rec["canonical_utf8"]).encode("utf-8")
        assert canonical(body) == expected_canon
        assert record_hash(body) == rec["hash"]


def test_vectors_merkle_roots() -> None:
    vectors = _load_vectors()
    records = cast(list[dict[str, object]], vectors["records"])
    roots = cast(dict[str, str], vectors["merkle_roots_by_tree_size"])
    leaf_hashes = [bytes.fromhex(cast(str, r["hash"])) for r in records]
    for size in range(len(records) + 1):
        assert merkle_root(leaf_hashes[:size]).hex() == roots[str(size)]


def test_vectors_checkpoint_signatures() -> None:
    vectors = _load_vectors()
    seed = bytes.fromhex(cast(str, vectors["test_private_key_hex"]))
    pubkey_hex = cast(str, vectors["public_key_hex"])
    key = Ed25519PrivateKey.from_private_bytes(seed)
    assert key.public_key().public_bytes_raw().hex() == pubkey_hex
    log_id = hashlib.sha256(key.public_key().public_bytes_raw()).hexdigest()[:16]
    assert log_id == vectors["log_id"]

    checkpoints = cast(list[dict[str, object]], vectors["checkpoints"])
    for cp in checkpoints:
        body = cast(dict[str, object], cp["body"])
        canon = canonical(body)
        assert canon == cast(str, cp["canonical_utf8"]).encode("utf-8")
        sig = key.sign(canon).hex()
        assert sig == cp["signature"]


@pytest.mark.parametrize(
    "bad_obj",
    [
        {"a": 1.5},
        {"a": None},
        {"a": "hello\x00world"},
        {"a\x00b": "ok"},
        {"BadKey": 1},
        {"bad-key": 1},
        {"": 1},
        {"a": 1 << 53},
        {"a": -(1 << 53)},
        {"a": b"bytes"},
        {"nested": [{"ok": True, "bad": None}]},
    ],
)
def test_canonical_rejects_forbidden_values(bad_obj: dict[str, object]) -> None:
    with pytest.raises(ValueError):
        canonical(bad_obj)


def test_canonical_accepts_boundary_integers() -> None:
    max_ok = (1 << 53) - 1
    out = canonical({"pos": max_ok, "neg": -max_ok, "flag": True, "list": [1, "x"]})
    assert b"9007199254740991" in out


def test_merkle_root_rejects_bad_leaf_length() -> None:
    with pytest.raises(ValueError):
        merkle_root([b"short"])


def test_append_rejects_unknown_action_and_oversized_detail() -> None:
    actor = Actor(type="system", id="test")
    with pytest.raises(ValueError, match="unknown audit action"):
        append(None, actor=actor, action="not.a.real.action", target_type="t", target_id="1", outcome="success")  # type: ignore[arg-type]

    oversized = {"msg": "x" * 2045}
    assert len(canonical(oversized)) > 2048
    with pytest.raises(ValueError, match="2048"):
        append(None, actor=actor, action="auth.login", target_type="t", target_id="1", outcome="success", detail=oversized)  # type: ignore[arg-type]


def test_actions_closed_list_count() -> None:
    assert len(ACTIONS) == 27


def test_settings_defaults_and_empty_dsn() -> None:
    s = Settings()
    assert s.session_idle_min == 30
    assert s.session_abs_hours == 8
    assert s.sandbox_runtime == "runsc"
    assert s.allow_degraded is False
    assert s.checkpoint_every_n == 20
    assert s.checkpoint_every_sec == 30
    assert s.audit_retention_days == 180
    with pytest.raises(ValueError):
        create_pool("")
