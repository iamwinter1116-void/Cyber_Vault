# Local instructions · Henil · role A (identity, API, quota, audit)

Copy this file to the repository root as `CLAUDE.local.md`. It is git-ignored and you cannot edit it.

- You work for **Henil**, role **A**. Your tasks are A0 to A7 in `team/henil/02_PROMPTS.md`.
- You write only in `core/`, `services/api/`, `services/notary/`, their unit-test folders,
  `tests/unit/notary/` and `team/henil/work/`.
- **Machine:** WSL 2 (Ubuntu) on Henil's 16 GB Lenovo Legion. The repository lives inside the Linux
  file system (for example `~/abhedya`), never under `/mnt/c`. If `pwd` starts with `/mnt/`, stop and say so.
- On this machine you may run: Python, `uv`, `make check-fast`, unit tests, and a PostgreSQL container for your
  own tests, using the same image tag as the `db` service in `compose.yaml`.
- On this machine you must **not** run: `make preflight`, `make test-security`, `make up` with the runner, or
  anything that needs `runsc`. Those run only on the demo VM. If a "done when" command needs the runner or the
  full stack, say so and give Henil the exact command to run over SSH on the demo VM as user `henil`; never
  start or stop the stack there.
- Manas operates the primary Ubuntu demo VM and shared stack. Coordinate full-stack verification with him; do not run it.
- Never open, read or copy `tools/verify_audit.py`. The verifier must stay independent of your ledger code.
- Journal entries go to `team/henil/work/JOURNAL.md`. Hand-off notes go to `team/henil/work/HANDOFFS.md`.
