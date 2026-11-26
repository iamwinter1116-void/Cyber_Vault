# Local instructions · Bhavya · role C · console, independent verifier and tests

Copy to the repository root locally as `CLAUDE.local.md`; it is git-ignored.

- You work for Bhavya, role C; tasks C0–C8 are in `team/bhavya/02_PROMPTS.md`.
- Edit only `web/`, `tools/verify_audit.py`, `tests/contract/`, `tests/security/`, `tests/e2e/`, `evidence/`, and `team/bhavya/work/`.
- Do not edit `Makefile`, `compose.yaml`, `.github/`, backend services, runner, sandbox, contracts, or another person's folder.
- Use WSL 2 on your 16 GB Ryzen 7 / RTX 3050 laptop for code, lint/type checks, the standalone verifier, and light tests.
- Do not start local Docker. Full security/e2e suites run against the primary Ubuntu VM, coordinated by Manas.
- Manas owns the primary stack and merge queue; do not start/stop/reset it. Send exact test commands and arrange a window.
- For C1/C2, do not read `core/` or `services/`; derive verifier and tests from contracts/vectors only.
- Do not weaken, skip, delete, or mock contract/security/e2e checks to make implementation pass.
- GPU hardware is not needed for mandatory objectives.
- All PRs target `integration`; Manas alone merges them, and only Manas promotes `integration` to `main`.
- Journal and handoff files are only `team/bhavya/work/JOURNAL.md` and `team/bhavya/work/HANDOFFS.md`.
