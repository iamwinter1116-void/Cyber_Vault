"""Report source line budgets without treating missing components as complete."""

from __future__ import annotations

import ast
import io
import re
import tokenize
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PYTHON_COMPONENTS = {"core/abh_core", "services/runner", "services/api", "services/notary", "tools/verify_audit.py"}
EXPECTED_COMPONENTS = PYTHON_COMPONENTS | {"sandbox", "web/src", "host"}
SOURCE_SUFFIXES = {".py", ".sh", ".ts", ".tsx", ".js", ".jsx", ".css", ".html", ".yaml", ".yml", ".json", ".yar", ".yara", ".rules", ".conf"}
SKIP_TOKENS = {
    tokenize.ENCODING,
    tokenize.ENDMARKER,
    tokenize.COMMENT,
    tokenize.NL,
    tokenize.NEWLINE,
    tokenize.INDENT,
    tokenize.DEDENT,
}


def python_lines(path: Path) -> int:
    """Count Python code lines, excluding comments and docstrings."""
    source = path.read_text(encoding="utf-8")
    docstrings: set[int] = set()
    for node in ast.walk(ast.parse(source, filename=str(path))):
        if not isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if node.body and isinstance(node.body[0], ast.Expr) and isinstance(node.body[0].value, ast.Constant):
            value = node.body[0].value
            if isinstance(value.value, str):
                docstrings.update(range(value.lineno, value.end_lineno + 1))
    lines: set[int] = set()
    for token in tokenize.generate_tokens(io.StringIO(source).readline):
        if token.type not in SKIP_TOKENS:
            lines.update(range(token.start[0], token.end[0] + 1))
    return len(lines - docstrings)


def other_lines(path: Path) -> int:
    """Count nonblank, non-comment source lines in shell, Docker, and web files."""
    count = 0
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith(("#", "//", "/*", "*", "*/")):
            count += 1
    return count


def documented_budgets() -> dict[str, int]:
    """Read limits from the frozen objectives instead of duplicating them here."""
    content = (ROOT / "docs/05_OBJECTIVES.md").read_text(encoding="utf-8")
    table = content.split("## Code budget", 1)[1].split("## Stretch objectives", 1)[0]
    pairs = re.findall(r"\|\s*`([^`]+)`[^|]*\|\s*(\d+)", table)
    budgets = {name.rstrip("/"): int(limit) for name, limit in pairs}
    if set(budgets) != EXPECTED_COMPONENTS or len(pairs) != len(EXPECTED_COMPONENTS):
        raise ValueError(f"Unexpected budget table in docs/05_OBJECTIVES.md: {sorted(budgets)}")
    return budgets


def report() -> int:
    failures = 0
    for name, limit in documented_budgets().items():
        target = ROOT / name
        if name in PYTHON_COMPONENTS:
            files = sorted(target.rglob("*.py")) if target.is_dir() else ([target] if target.is_file() else [])
        else:
            files = sorted(
                path for path in target.rglob("*")
                if path.is_file() and (path.suffix in SOURCE_SUFFIXES or path.name.startswith("Dockerfile"))
            ) if target.is_dir() else []
        if not files:
            print(f"{name}: MISSING (budget {limit})")
            failures += 1
            continue
        count = sum(python_lines(path) if path.suffix == ".py" else other_lines(path) for path in files)
        print(f"{name}: {count}/{limit} {'OVER' if count > limit else 'OK'}")
        failures += count > limit
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(report())
