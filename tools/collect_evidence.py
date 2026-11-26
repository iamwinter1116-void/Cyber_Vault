"""Evidence pack generator for C7 / make evidence (Bhavya-owned)."""
from __future__ import annotations

import argparse
import xml.etree.ElementTree as ET
from pathlib import Path

OBJECTIVES = [
    ("O1", "Isolated testing environments", ["T-ISO-01", "T-ISO-02", "T-ISO-04", "T-ISO-06", "T-ISO-07", "T-E2E-01"]),
    ("O2", "Secure login and RBAC", ["T-AUTH-01", "T-AUTH-02", "T-AUTH-03", "T-AUTH-04", "T-AUTH-05", "T-RBAC-01", "T-API-01"]),
    ("O3", "Team separation", ["T-ISO-03", "T-ISO-05", "T-MON-03", "T-RBAC-01"]),
    ("O4", "Real-time monitoring", ["T-MON-01", "T-MON-02", "T-MON-03", "T-MON-04"]),
    ("O5", "Resource management", ["T-RES-01", "T-RES-02", "T-RES-03", "T-RES-04", "T-RES-05", "T-RES-06"]),
    ("O6", "Centralized audit logs", ["T-AUD-01", "T-AUD-02", "T-AUD-06", "T-AUD-07"]),
    ("O7", "Tamper detection", ["T-KAT-01", "T-KAT-02", "T-KAT-03", "T-KAT-04", "T-AUD-03", "T-AUD-04", "T-AUD-05", "T-AUD-08"]),
    ("O8", "Admin dashboard", ["T-E2E-01", "T-E2E-02", "T-E2E-03", "T-E2E-04"]),
    ("O9", "Three workload types", ["T-WL-01", "T-WL-02", "T-WL-03"]),
]


def _parse_junit_results(tests_dir: Path) -> dict[str, str]:
    statuses: dict[str, str] = {}
    if not tests_dir.exists():
        return statuses
    for xml_file in sorted(tests_dir.glob("*.xml")):
        root = ET.parse(xml_file).getroot()
        for tc in root.iter("testcase"):
            name = tc.attrib.get("name", "")
            if tc.find("failure") is not None or tc.find("error") is not None:
                statuses[name] = "FAIL"
            elif tc.find("skipped") is not None:
                statuses[name] = "SKIP"
            else:
                statuses[name] = "PASS"
    return statuses


def _status_for_id(test_id: str, results: dict[str, str]) -> str:
    norm = test_id.lower().replace("-", "_")
    matched = [v for k, v in results.items() if norm in k.lower()]
    if not matched:
        return "NOT_RUN"
    return "FAIL" if "FAIL" in matched else ("SKIP" if "SKIP" in matched else "PASS")


def build_evidence(repo_root: Path) -> None:
    ev_dir = repo_root / "evidence"
    ev_dir.mkdir(parents=True, exist_ok=True)
    prior_src = repo_root / "docs" / "14_PRIOR_ART.md"
    if prior_src.exists():
        (ev_dir / "prior-art.md").write_text(prior_src.read_text(encoding="utf-8"), encoding="utf-8")

    parts: list[str] = []
    bug_src = repo_root / "docs" / "09_BUG_JOURNAL.md"
    if bug_src.exists():
        parts.append(bug_src.read_text(encoding="utf-8"))
    for jpath in sorted((repo_root / "team").glob("*/work/JOURNAL.md")):
        parts.append(f"\n---\n<!-- {jpath.relative_to(repo_root).as_posix()} -->\n" + jpath.read_text(encoding="utf-8"))
    (ev_dir / "bug-journal.md").write_text("\n".join(parts), encoding="utf-8")

    results = _parse_junit_results(ev_dir / "tests")
    lines = ["# Evidence Index (generated)", "", "| Objective | Description | Test ID | Status | Evidence |", "| --- | --- | --- | --- | --- |"]
    for oid, desc, tids in OBJECTIVES:
        for tid in tids:
            lines.append(f"| {oid} | {desc} | {tid} | {_status_for_id(tid, results)} | `evidence/tests/` |")
    (ev_dir / "INDEX.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate ABHEDYA evidence pack from JUnit XML and journals.")
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    build_evidence(args.repo_root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
