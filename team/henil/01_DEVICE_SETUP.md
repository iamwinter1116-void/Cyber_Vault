# Henil · Lenovo Legion setup for backend development

Known hardware: Ryzen 7 260 octa-core, RTX 5050 8 GB, 16 GB RAM. Use this system for API/core/notary development,
unit checks and review. Manas owns the primary Ubuntu VM and the only active Docker stack.

## 1. WSL 2 development environment

| Step | Do | Check |
| --- | --- | --- |
| 1 | Enable WSL 2 with Ubuntu using Microsoft's current official instructions | `wsl -l -v` shows your distribution on version 2 |
| 2 | Clone the shared repository into the Linux filesystem, such as `~/abhedya`; do not use `/mnt/c` for Linux tooling | `pwd` starts under `/home/` |
| 3 | Copy `team/henil/CLAUDE.local.md` to the repo root as local `CLAUDE.local.md` | Local file exists and is git-ignored |
| 4 | Install only the project-approved Python tooling and use `uv`/`make` from the Linux environment | `make check-fast` runs after Manas's scaffold lands |
| 5 | Run core/API/notary unit tests against a local PostgreSQL instance only when needed | Local test DB is disposable and uses the canonical schema |

WSL may use up to a configured share of system memory. Keep enough memory available for Windows and the editor; do not
raise WSL limits without evidence. The RTX 5050 is not needed by the mandatory backend objectives.

## 2. Your scope and environment boundary

- Edit only `core/abh_core/`, `services/api/`, `services/notary/`, their unit tests, and `team/henil/work/`.
- Do not run a local runner stack, `runsc` preflight, security suite, or `make up`.
- Do not operate or reset Manas's primary demo VM. Send him the exact full-stack command and ask for an announced test window.
- Do not read `tools/verify_audit.py`; Bhavya's verifier must remain independent of your ledger implementation.
- Do not edit `tests/contract/`, `tests/security/`, or `tests/e2e/`; report a defect against the contract and let Bhavya own the test.
- Never change a contract locally. Use the CR process and four-person approval.

## 3. Handoffs

For each PR, state the API rule IDs, request/response shape, DB role, transaction/audit behavior, test IDs, and the command
output observed. Coordinate the API/runner database-row interface with Parth and the service health/environment wiring
with Manas. The full team branch path is `work/henil` → PR to `integration` → Manas merge.

## 4. Source and assumptions

Use the official WSL instructions for setup and verify current behavior on this laptop. Device specifications came from
the team; available disk, Windows edition and WSL configuration still need local verification.
