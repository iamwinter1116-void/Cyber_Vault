"""Live-ledger tamper drill tool for T-AUD-04 / T-AUD-08 / T-E2E-04 (Bhavya-owned)."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any

RECORD_KEYS = (
    "v", "seq", "ts", "actor_type", "actor_id", "actor_role", "team_id",
    "action", "target_type", "target_id", "outcome", "ip", "request_id", "detail", "prev_hash",
)
GENESIS_PREV = "0" * 64


def _canonical(obj: dict[str, Any]) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _record_hash(body: dict[str, Any]) -> str:
    return hashlib.sha256(b"\x00" + _canonical(body)).hexdigest()


def apply_tamper_case(dsn: str, case_name: str, vectors_path: Path) -> None:
    import psycopg  # lazy import so CLI guard and --help work without DB driver

    vectors = json.loads(vectors_path.read_text(encoding="utf-8"))
    case = next((c for c in vectors["tamper_cases"] if c["name"] == case_name), None)
    if case is None:
        raise SystemExit(f"Unknown tamper case: {case_name}")
    mut = case["mutation"]
    op = mut["op"]

    with psycopg.connect(dsn) as conn:
        with conn.cursor() as cur:
            cur.execute("ALTER TABLE audit_log DISABLE TRIGGER audit_no_update_delete")
            cur.execute("ALTER TABLE audit_log DISABLE TRIGGER audit_no_truncate")
            try:
                if op == "none":
                    pass
                elif op == "set_field":
                    field = mut["field"]
                    val = json.dumps(mut["value"]) if field == "detail" else mut["value"]
                    cur.execute(f"UPDATE audit_log SET {field} = %s WHERE seq = %s", (val, mut["seq"]))
                elif op == "delete_record":
                    cur.execute("DELETE FROM audit_log WHERE seq = %s", (mut["seq"],))
                elif op == "swap_records":
                    a, b = mut["a"], mut["b"]
                    cur.execute("UPDATE audit_log SET seq = -1 WHERE seq = %s", (a,))
                    cur.execute("UPDATE audit_log SET seq = %s WHERE seq = %s", (a, b))
                    cur.execute("UPDATE audit_log SET seq = %s WHERE seq = -1", (b,))
                elif op == "truncate_after":
                    cur.execute("DELETE FROM audit_log WHERE seq > %s", (mut["seq"],))
                elif op == "set_field_and_rehash_forward":
                    field = mut["field"]
                    cur.execute(f"UPDATE audit_log SET {field} = %s WHERE seq = %s", (mut["value"], mut["seq"]))
                    cur.execute(f"SELECT {', '.join(RECORD_KEYS)}, hash FROM audit_log ORDER BY seq ASC")
                    rows = cur.fetchall()
                    prev = GENESIS_PREV
                    for row in rows:
                        rec = dict(zip((*RECORD_KEYS, "hash"), row))
                        if rec["seq"] >= mut["seq"]:
                            rec["prev_hash"] = prev
                            body = {k: rec[k] for k in RECORD_KEYS}
                            new_hash = _record_hash(body)
                            cur.execute("UPDATE audit_log SET prev_hash = %s, hash = %s WHERE seq = %s", (prev, new_hash, rec["seq"]))
                            prev = new_hash
                        else:
                            prev = rec["hash"]
                elif op == "set_checkpoint_field":
                    cur.execute(f"UPDATE audit_checkpoint SET {mut['field']} = %s WHERE tree_size = %s", (mut["value"], mut["tree_size"]))
                elif op == "delete_checkpoints":
                    cur.execute("DELETE FROM audit_checkpoint")
                else:
                    raise SystemExit(f"Unsupported tamper op: {op}")
            finally:
                cur.execute("ALTER TABLE audit_log ENABLE TRIGGER audit_no_update_delete")
                cur.execute("ALTER TABLE audit_log ENABLE TRIGGER audit_no_truncate")
        conn.commit()


def main() -> int:
    parser = argparse.ArgumentParser(description="Apply a superuser tamper drill case to the live audit ledger.")
    parser.add_argument("--case", required=True, help="Tamper case name from contracts/audit_vectors.json")
    parser.add_argument("--dsn", default=os.environ.get("ABH_SUPERUSER_DSN", os.environ.get("ABH_DB_DSN", "")))
    parser.add_argument("--vectors", type=Path, default=Path(__file__).resolve().parents[1] / "contracts" / "audit_vectors.json")
    args = parser.parse_args()

    if os.environ.get("ABH_ALLOW_TAMPER_DRILL") != "1":
        print("REFUSED: set ABH_ALLOW_TAMPER_DRILL=1 to run tamper-drill.", file=sys.stderr)
        return 2
    print("==================================================================")
    print("WARNING: ABHEDYA TAMPER DRILL ACTIVE — CORRUPTING LIVE AUDIT LOG")
    print(f"CASE={args.case}")
    print("==================================================================")
    if not args.dsn:
        print("ERROR: ABH_SUPERUSER_DSN or ABH_DB_DSN must be set.", file=sys.stderr)
        return 2
    apply_tamper_case(args.dsn, args.case, args.vectors)
    return 0


if __name__ == "__main__":
    sys.exit(main())
