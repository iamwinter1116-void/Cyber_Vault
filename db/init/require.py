"""Refuse build targets whose real implementation is not present yet."""

from __future__ import annotations

import shutil
import subprocess
import sys
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SERVICES = {"db", "api", "runner", "notary", "proxy"}
PLACEHOLDER = re.compile(r"\b(?:TODO|FIXME|NotImplementedError|stub|mock)\b", re.IGNORECASE)


def require_file(path: str, reason: str) -> None:
    if not (ROOT / path).is_file():
        raise RuntimeError(f"{reason}: missing {path}")


def require_stack() -> None:
    result = subprocess.run(
        ["docker", "compose", "config", "--services"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    absent = sorted(SERVICES - set(result.stdout.splitlines()))
    if absent:
        raise RuntimeError(f"full stack unavailable; missing Compose services: {', '.join(absent)}")


def require_no_placeholders() -> None:
    findings = []
    for folder in ("core", "services", "host"):
        for path in (ROOT / folder).rglob("*"):
            if path.suffix not in {".py", ".sh"}:
                continue
            for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                if PLACEHOLDER.search(line):
                    findings.append(f"{path.relative_to(ROOT)}:{line_no}")
    if findings:
        raise RuntimeError("placeholder markers in non-test code: " + ", ".join(findings))


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: python db/init/require.py TARGET", file=sys.stderr)
        return 2
    target = sys.argv[1]
    if target not in {"up", "check-fast", "test-contract", "test-security", "test-e2e", "scan", "demo-reset", "placeholders"}:
        print(f"unknown target: {target}", file=sys.stderr)
        return 2
    try:
        if target in {"up", "test-security", "test-e2e"}:
            require_stack()
        if target in {"check-fast", "test-e2e"}:
            require_file("web/package.json", "console build unavailable")
        if target == "test-contract":
            require_file("contracts/openapi.yaml", "generated OpenAPI contract unavailable")
        if target == "demo-reset":
            require_file("db/init/demo_reset.py", "real demo reset unavailable")
        if target == "scan":
            require_file("db/init/run_scans.py", "real scan runner unavailable")
            missing = [name for name in ("docker-bench-security", "trivy", "semgrep", "gitleaks", "zap-baseline.py")
                       if shutil.which(name) is None]
            if missing:
                raise RuntimeError(f"scan tools unavailable: {', '.join(missing)}")
        if target == "placeholders":
            require_no_placeholders()
    except (OSError, subprocess.CalledProcessError, RuntimeError) as exc:
        print(f"REFUSED {target}: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
