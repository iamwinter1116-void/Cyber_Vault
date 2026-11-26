# API dependency resolution proposal

**Status: proposal only. No package has been installed from these candidate locks.** The local API cannot start in the current Python environment because `psycopg`, `psycopg_pool`, and `argon2` are absent. The repository dependency/change-control rule still requires review and formal approval for automatically resolved packages before installation. These files do not authorize a dependency-policy change.

## Candidate artifacts

Two candidates are provided so the runtime image can avoid test-only dependencies:

- `API_REQUIREMENTS_RUNTIME.in`: ten direct runtime pins already present in `evidence/VERSIONS.lock` (`argon2-cffi`, `cryptography`, `fastapi`, `psycopg[binary]`, `psycopg-pool`, `pydantic`, `pydantic-settings`, `python-multipart`, `PyYAML`, and `uvicorn`).
- `API_REQUIREMENTS_RUNTIME.lock`: universal Python 3.11 hash-locked closure of 27 packages (10 direct and 17 resolver-added), containing 510 artifact hashes. It passed uv's hash-required dry-run install resolution. This is a review candidate, not an approved production lock.
- `API_REQUIREMENTS_DEV.in`: the same 10 runtime pins plus five already recorded test/tool pins (`hypothesis`, `httpx`, `mypy`, `pytest`, and `ruff`).
- `API_REQUIREMENTS_DEV.lock`: universal Python 3.11 hash-locked closure of 44 packages (15 direct and 29 resolver-added), containing 867 artifact hashes. It passed uv's hash-required dry-run install resolution. This is a review candidate for an isolated developer/test environment.

The local Manas interpreter is CPython 3.11 x64. Universal resolution was requested, but Linux/Python 3.13 service-image compatibility still needs validation against the approved image choice. The resolver output does not constitute a package security or license review; the resolver-added package list must be reviewed and accepted through the repository's change-control process.

## Reproduction

```powershell
uv --version
# uv 0.12.9 (9f9286029 2026-09-01 x86_64-pc-windows-msvc)

uv pip compile team/manas/work/API_REQUIREMENTS_RUNTIME.in `
  --python-version 3.11 --universal --generate-hashes `
  --output-file team/manas/work/API_REQUIREMENTS_RUNTIME.lock
# Resolved 27 packages

uv pip compile team/manas/work/API_REQUIREMENTS_DEV.in `
  --python-version 3.11 --universal --generate-hashes `
  --output-file team/manas/work/API_REQUIREMENTS_DEV.lock
# Resolved 44 packages
```

Both commands only resolve metadata and hashes; neither installs packages. Direct pins were compared with their input files and retained unchanged. The following dry-run commands exited 0 and reported “Would download” / “Would install” the stated package counts; no installation occurred:

```powershell
uv pip install --dry-run --no-cache --require-hashes --system -r team/manas/work/API_REQUIREMENTS_RUNTIME.lock
uv pip install --dry-run --no-cache --require-hashes --system -r team/manas/work/API_REQUIREMENTS_DEV.lock
```

## Decision and next steps

Use the existing change-request process to decide whether resolver-added packages may be recorded and installed, and to approve the reviewed closure. Do not edit frozen dependency policy or install from these candidate locks before that decision. If approved, record accepted package metadata/hashes in the repository's canonical lock/evidence format, validate the exact lock for the selected Linux/Python target, install it into an isolated environment, and then run the API against the real local Compose PostgreSQL. If rejected, revise the direct package set or use another policy-compliant resolution.

This dependency-control prerequisite is independent of sandbox/VM work; it is the current reason the real API cannot start in this local Python environment. The local PostgreSQL is healthy and has been tested separately, but no API endpoint, authenticated flow, or objective is accepted by this proposal.

## Verification state

- `uv pip compile` -> exit 0 for both runtime and dev inputs; resolved 27 and 44 packages respectively.
- `uv pip install --dry-run --no-cache --require-hashes --system` -> exit 0 for both lock files; no package installed.
- `python -m compileall -q core services tools` -> exit 0; syntax compilation only, not import or runtime validation.
- The current environment contains FastAPI, Uvicorn, Pydantic, pydantic-settings, PyYAML, cryptography, and httpx; it does not contain `psycopg`, `psycopg_pool`, `argon2`, or `argon2_cffi_bindings`.
- No API process, authentication route, API-to-PostgreSQL query, disposable-DB suite, ruff, or mypy run was performed against these candidate locks.
- The transitive package review/approval remains pending. No package security/license review is claimed.
