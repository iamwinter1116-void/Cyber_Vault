"""Contract tests for abhedya-audit-v1 vectors (T-KAT-01..04, T-AUD-05)."""
from __future__ import annotations

import copy
import hashlib
import importlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from hypothesis import given, settings, strategies as st

REPO_ROOT = Path(__file__).resolve().parents[2]
VECTORS = json.loads((REPO_ROOT / "contracts" / "audit_vectors.json").read_text(encoding="utf-8"))


def _load_impl(impl_name: str) -> Any:
    if impl_name == "verifier":
        if str(REPO_ROOT / "tools") not in sys.path:
            sys.path.insert(0, str(REPO_ROOT / "tools"))
        return importlib.import_module("verify_audit")
    if impl_name == "core":
        if str(REPO_ROOT) not in sys.path:
            sys.path.insert(0, str(REPO_ROOT))
        for mod_name in ("abh_core.audit", "core.abh_core.audit"):
            try:
                return importlib.import_module(mod_name)
            except ImportError as exc:
                last_exc = exc
        pytest.fail(f"abh_core.audit not available yet: {last_exc}")
    raise ValueError(impl_name)


def _apply_tamper(
    records: list[dict[str, Any]],
    checkpoints: list[dict[str, Any]],
    mutation: dict[str, Any],
    verifier: Any,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    recs = copy.deepcopy(records)
    cps = copy.deepcopy(checkpoints)
    op = mutation["op"]
    if op == "none":
        return recs, cps
    if op == "set_field":
        for r in recs:
            if r["seq"] == mutation["seq"]:
                r[mutation["field"]] = mutation["value"]
        return recs, cps
    if op == "delete_record":
        return [r for r in recs if r["seq"] != mutation["seq"]], cps
    if op == "swap_records":
        ia = next(i for i, r in enumerate(recs) if r["seq"] == mutation["a"])
        ib = next(i for i, r in enumerate(recs) if r["seq"] == mutation["b"])
        recs[ia], recs[ib] = recs[ib], recs[ia]
        return recs, cps
    if op == "truncate_after":
        return [r for r in recs if r["seq"] <= mutation["seq"]], cps
    if op == "set_field_and_rehash_forward":
        prev = "0" * 64
        started = False
        for r in recs:
            if r["seq"] == mutation["seq"]:
                r[mutation["field"]] = mutation["value"]
                started = True
            if started:
                r["prev_hash"] = prev
                body = {k: v for k, v in r.items() if k != "hash"}
                r["hash"] = verifier.record_hash(body)
            prev = r["hash"]
        return recs, cps
    if op == "set_checkpoint_field":
        for c in cps:
            if c["tree_size"] == mutation["tree_size"]:
                c[mutation["field"]] = mutation["value"]
        return recs, cps
    if op == "delete_checkpoints":
        return recs, []
    raise ValueError(f"unknown tamper op: {op}")


def _write_ndjson(path: Path, items: list[dict[str, Any]]) -> None:
    lines = [json.dumps(item, separators=(",", ":"), ensure_ascii=False) for item in items]
    path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")


@pytest.mark.parametrize("impl", ["core", "verifier"])
@pytest.mark.parametrize("rec", VECTORS["records"], ids=lambda r: f"seq-{r['body']['seq']}")
def test_t_kat_01_canonical_bytes(impl: str, rec: dict[str, Any]) -> None:
    mod = _load_impl(impl)
    assert mod.canonical(rec["body"]) == rec["canonical_utf8"].encode("utf-8")


@pytest.mark.parametrize("impl", ["core", "verifier"])
def test_t_kat_02_hashes_and_merkle_roots(impl: str) -> None:
    mod = _load_impl(impl)
    leaf_hashes = [bytes.fromhex(r["hash"]) for r in VECTORS["records"]]
    for rec in VECTORS["records"]:
        assert mod.record_hash(rec["body"]) == rec["hash"]
    for size_str, expected_root in VECTORS["merkle_roots_by_tree_size"].items():
        size = int(size_str)
        assert mod.merkle_root(leaf_hashes[:size]).hex() == expected_root


def test_t_kat_03_checkpoint_signatures_verifier() -> None:
    mod = _load_impl("verifier")
    priv = Ed25519PrivateKey.from_private_bytes(bytes.fromhex(VECTORS["test_private_key_hex"]))
    for cp in VECTORS["checkpoints"]:
        sig = priv.sign(mod.canonical(cp["body"])).hex()
        assert sig == cp["signature"]


def test_t_kat_03_checkpoint_signatures_core() -> None:
    mod = _load_impl("core")
    priv = Ed25519PrivateKey.from_private_bytes(bytes.fromhex(VECTORS["test_private_key_hex"]))
    for cp in VECTORS["checkpoints"]:
        assert priv.sign(mod.canonical(cp["body"])).hex() == cp["signature"]


@pytest.mark.parametrize("case", VECTORS["tamper_cases"], ids=lambda c: c["name"])
def test_t_kat_04_verifier_tamper_cases(case: dict[str, Any], tmp_path: Path) -> None:
    verifier = _load_impl("verifier")
    base_records = [{**r["body"], "hash": r["hash"]} for r in VECTORS["records"]]
    base_cps = [{**c["body"], "signature": c["signature"]} for c in VECTORS["checkpoints"]]

    recs, cps = _apply_tamper(base_records, base_cps, case["mutation"], verifier)
    rec_file = tmp_path / "records.ndjson"
    cp_file = tmp_path / "checkpoints.ndjson"
    _write_ndjson(rec_file, recs)
    _write_ndjson(cp_file, cps)

    cmd = [
        sys.executable,
        str(REPO_ROOT / "tools" / "verify_audit.py"),
        "--records",
        str(rec_file),
        "--checkpoints",
        str(cp_file),
        "--pubkey",
        VECTORS["public_key_hex"],
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    expected_code = 0 if case["expected_verdict"] == "OK" else 2
    assert proc.returncode == expected_code, proc.stderr
    res = json.loads(proc.stdout)
    assert res["verdict"] == case["expected_verdict"]
    assert res["at"] == case["expected_at"]

    if "expected_verdict_with_witness" in case:
        wit_file = tmp_path / "witness.ndjson"
        _write_ndjson(wit_file, base_cps)
        proc_w = subprocess.run([*cmd, "--witness", str(wit_file)], capture_output=True, text=True, check=False)
        assert proc_w.returncode == 2
        res_w = json.loads(proc_w.stdout)
        assert res_w["verdict"] == case["expected_verdict_with_witness"]
        assert res_w["at"] == case["expected_at_with_witness"]


@pytest.mark.parametrize("bad_detail", [{"x": 1.5}, {"x": None}, {"BadKey": 1}, {"x": "a\x00b"}])
def test_verifier_rejects_forbidden_inputs_exit_3(bad_detail: dict[str, Any], tmp_path: Path) -> None:
    rec = {**VECTORS["records"][0]["body"], "detail": bad_detail, "hash": VECTORS["records"][0]["hash"]}
    rec_file = tmp_path / "records.ndjson"
    cp_file = tmp_path / "checkpoints.ndjson"
    _write_ndjson(rec_file, [rec])
    _write_ndjson(cp_file, [])
    proc = subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "tools" / "verify_audit.py"),
            "--records",
            str(rec_file),
            "--checkpoints",
            str(cp_file),
            "--pubkey",
            VECTORS["public_key_hex"],
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 3


@given(
    n_records=st.integers(min_value=1, max_value=20),
    mutation_kind=st.sampled_from(["edit_field", "delete", "insert", "swap", "truncate_below_cp", "alter_cp"]),
    seed_byte=st.integers(min_value=1, max_value=254),
)
@settings(max_examples=60, deadline=None)
def test_t_aud_05_verifier_property_based(n_records: int, mutation_kind: str, seed_byte: int) -> None:
    verifier = _load_impl("verifier")
    priv = Ed25519PrivateKey.from_private_bytes(bytes([seed_byte]) * 32)
    pub_hex = priv.public_key().public_bytes_raw().hex()
    log_id = hashlib.sha256(bytes.fromhex(pub_hex)).hexdigest()[:16]

    records: list[dict[str, Any]] = []
    leaves: list[bytes] = []
    prev = "0" * 64
    for seq in range(1, n_records + 1):
        body = {
            "v": 1, "seq": seq, "ts": f"2026-11-26T04:30:{seq:02d}.000000Z",
            "actor_type": "user", "actor_id": "u1", "actor_role": "analyst", "team_id": "t1",
            "action": "env.create", "target_type": "env", "target_id": f"e{seq}",
            "outcome": "success", "ip": "10.0.0.1", "request_id": f"r{seq}",
            "detail": {"n": seq}, "prev_hash": prev,
        }
        h = verifier.record_hash(body)
        records.append({**body, "hash": h})
        leaves.append(bytes.fromhex(h))
        prev = h

    cp_sizes = sorted({max(1, n_records // 2), n_records})
    cps: list[dict[str, Any]] = []
    for sz in cp_sizes:
        cp_body = {
            "v": 1, "log_id": log_id, "tree_size": sz,
            "root_hash": verifier.merkle_root(leaves[:sz]).hex(),
            "head_hash": records[sz - 1]["hash"],
            "ts": f"2026-11-26T04:31:{sz:02d}.000000Z",
        }
        sig = priv.sign(verifier.canonical(cp_body)).hex()
        cps.append({**cp_body, "signature": sig})

    ok_res = verifier.verify_ledger(records, cps, pub_hex)
    assert ok_res["verdict"] == "OK"

    m_recs = copy.deepcopy(records)
    m_cps = copy.deepcopy(cps)
    if mutation_kind == "edit_field":
        m_recs[0]["outcome"] = "denied"
    elif mutation_kind == "delete":
        m_recs.pop(0)
    elif mutation_kind == "insert":
        dup = copy.deepcopy(m_recs[0])
        m_recs.insert(0, dup)
    elif mutation_kind == "swap":
        if len(m_recs) >= 2:
            m_recs[0], m_recs[1] = m_recs[1], m_recs[0]
        else:
            m_recs[0]["seq"] = 2
    elif mutation_kind == "truncate_below_cp":
        m_recs.pop()
    elif mutation_kind == "alter_cp":
        m_cps[-1]["root_hash"] = "0" * 64

    bad_res = verifier.verify_ledger(m_recs, m_cps, pub_hex)
    assert bad_res["verdict"] != "OK"
