"""Report source line budgets without treating missing components as complete."""

from __future__ import annotations

import ast
import io
import tokenize
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PYTHON_BUDGETS = {
    "core/abh_core": 300,
    "services/runner": 800,
    "services/api": 1100,
    "services/notary": 150,
    "tools/verify_audit.py": 180,
}
OTHER_BUDGETS = {
    "sandbox": 450,
    "web/src": 1800,
    "host": 150,
}
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


def report() -> int:
    failures = 0
    for name, limit in PYTHON_BUDGETS.items():
        target = ROOT / name
        files = sorted(target.rglob("*.py")) if target.is_dir() else ([target] if target.is_file() else [])
        if not files:
            print(f"{name}: MISSING (budget {limit})")
            failures += 1
            continue
        count = sum(python_lines(path) for path in files)
        print(f"{name}: {count}/{limit} {'OVER' if count > limit else 'OK'}")
        failures += count > limit
    for name, limit in OTHER_BUDGETS.items():
        target = ROOT / name
        files = sorted(
            path for path in target.rglob("*")
            if path.is_file() and path.suffix in {".sh", ".py", ".ts", ".tsx", ".js", ".jsx", ".css", ".html"}
            or path.is_file() and path.name.startswith("Dockerfile")
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
