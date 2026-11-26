# Hand-off notes · Henil (role A)

The agent appends one note at the end of every session (prompt P-HANDOFF), in the format of
`docs/07_ANTI_HALLUCINATION.md` section 5. Newest at the bottom. Teammates read this file to learn what is
really finished: only what was run and seen belongs here.

## 2026-11-26 · M1 interface handoff to Manas (role A · Henil)

TASK: M1 service interface handoff (unblocking Manas M1 `compose.yaml` / `Makefile` / `db/init/`)
STATUS: partial (A0/A1 blocked pending M1 scaffold on `integration`)
CHANGED: `team/henil/work/HANDOFFS.md` (appended this handoff)
COMMANDS RUN (with exit codes):
  $ git fetch --all --prune && git status -> 0 (branch `work/henil`, clean; `origin/work/manas` at `71f9c52`, `origin/integration` at `6dc40c8`)
  $ wsl -d Ubuntu -- bash -lc "which python3 uv pytest ruff mypy psql 2>&1; python3 --version 2>&1" -> 0 (`python3` Python 3.14.4, `uv` at `/home/henillol/.local/bin/uv`; `pytest`/`ruff`/`mypy`/`psql` not yet installed)
TESTS: none (no application code written yet; waiting on M1 scaffold on `integration`)
VERIFIED FACTS:
  - `contracts/schema.sql` defines roles `abh_api`, `abh_runner`, `abh_notary` with passwords set at deploy time from `./secrets/`, and `REVOKE ALL ... FROM PUBLIC` + least-privilege `GRANT`s.
  - `docs/04_CONTRACTS.md` section 9 & 11 define the `api` and `notary` networks (`control` internal only), volumes, env vars, and canonical `Makefile` targets (`make openapi`, `make check-fast`, etc.).
  - `services/api`: FastAPI app on `control` network port `8000` (no published host port; behind `proxy`). Start command: `uvicorn services.api.main:app --host 0.0.0.0 --port 8000`. Health/readiness: `GET /api/v1/healthz` (R31, public) -> HTTP `200` `{"status": "ok", "db": true}` after verifying DB query. DB role: `abh_api` via `ABH_DB_DSN`. Mounts: `quarantine` (`rw`) at `ABH_QUARANTINE_DIR=/quarantine`, `ABH_NOTARY_PUBKEY_PATH=/run/secrets/notary_ed25519.pub` (`ro`).
  - `services/notary`: Python worker on `control` network (no inbound port). Start command: `python -m services.notary`. DB role: `abh_notary` via `ABH_DB_DSN`. Mounts: `ABH_NOTARY_KEY_PATH=/run/secrets/notary_ed25519` (`ro`, 32-byte Ed25519 seed, notary-only), `ABH_WITNESS_PATH=/witness/checkpoints.ndjson` (`rw`, notary-only volume).
  - `db/init/`: No ORM or separate migrations; `db/init` applies `contracts/schema.sql` once as DB owner and sets `abh_api`, `abh_runner`, `abh_notary` passwords from `./secrets/`.
  - `make openapi`: A0 will provide a Python script dumping `services.api.main:app` OpenAPI schema to `contracts/openapi.yaml` for `Makefile` to invoke.
UNVERIFIED / ASSUMED:
  - Python dependencies (`fastapi`, `uvicorn`, `psycopg[binary,pool]`, `pydantic`, `pydantic-settings`, `argon2-cffi`, `cryptography`, `python-multipart`, `pyyaml`) have not yet been registry-checked or recorded in `evidence/VERSIONS.lock`.
  - `team/henil/CLAUDE.local.md` is missing from the repo; local `CLAUDE.local.md` not yet created.
DEGRADED PATHS: none
NEW DEPENDENCIES: none
OPEN RISKS / QUESTIONS FOR HUMANS:
  - Manas: please wire `api`, `notary`, `db/init/`, and `Makefile` (`check-fast`, `openapi`) in M1 and merge to `integration`.
  - `team/henil/CLAUDE.local.md` is missing from `team/henil/`.
NEXT: A0 (once Manas's M1 scaffold is on `integration`)

## 2026-11-26 · Task A1 local implementation slice (`core/abh_core`)

TASK: A1 · Core library and audit append (`docs/16_BUILD_NOW_HOST_LATER.md` local slice)
STATUS: partial (pure unit, vector, ruff, and mypy --strict checks pass; 50-thread live PostgreSQL test and `make check-fast` pending local PostgreSQL and Manas's `Makefile`)
CHANGED:
  - `core/__init__.py` (1 line)
  - `core/abh_core/__init__.py` (23 lines)
  - `core/abh_core/settings.py` (27 lines)
  - `core/abh_core/db.py` (28 lines)
  - `core/abh_core/audit.py` (147 lines; total `core/abh_core/*.py` = 225 lines <= 300 budget)
  - `tests/unit/core/test_audit.py` (111 lines)
COMMANDS RUN (with exit codes):
  $ wsl -d Ubuntu -- env PYTHONPATH=/mnt/e/CyberVault/Cyber_Vault /home/henillol/.venv-cybervault/bin/pytest /mnt/e/CyberVault/Cyber_Vault/tests/unit/core -v -> 0 (19 passed in 0.62s)
  $ wsl -d Ubuntu -- /home/henillol/.venv-cybervault/bin/ruff check /mnt/e/CyberVault/Cyber_Vault/core /mnt/e/CyberVault/Cyber_Vault/tests/unit/core -> 0 (All checks passed!)
  $ wsl -d Ubuntu -- env MYPYPATH=/mnt/e/CyberVault/Cyber_Vault /home/henillol/.venv-cybervault/bin/mypy --strict /mnt/e/CyberVault/Cyber_Vault/core/abh_core /mnt/e/CyberVault/Cyber_Vault/tests/unit/core -> 0 (Success: no issues found in 5 source files)
  $ wsl -d Ubuntu -- wc -l /mnt/e/CyberVault/Cyber_Vault/core/abh_core/*.py -> 0 (225 total)
TESTS: T-KAT-01, T-KAT-02, T-KAT-03 (core unit side in `tests/unit/core/test_audit.py`) + rejection/boundary/settings unit tests (19/19 passed); 50-thread PostgreSQL concurrency test and `tests/contract/test_audit_vectors.py` not yet run (no PostgreSQL or Bhavya contract suite locally)
VERIFIED FACTS:
  - `contracts/audit_vectors.json` canonical bytes, record hashes, Merkle roots (sizes 0..5), and Ed25519 checkpoint signatures match `core.abh_core.audit` byte-for-byte.
  - PyPI JSON verified for: `pydantic==2.14.4`, `pydantic-settings==2.16.3`, `psycopg==3.3.9`, `psycopg-pool==3.3.3`, `psycopg-binary==3.3.9`, `cryptography==50.0.2`, `pytest==9.2.0`, `ruff==0.17.6`, `mypy==2.4.1`.
UNVERIFIED / ASSUMED:
  - `core.abh_core.audit.append()` SQL (`pg_advisory_xact_lock(4242001)`, `clock_timestamp()`, `INSERT INTO audit_log`) and 50-thread concurrency against real PostgreSQL 16+ have not yet been executed (no `psql`/`postgres`/`docker` installed in WSL).
DEGRADED PATHS: none
NEW DEPENDENCIES (allowlisted in `docs/03_CONTEXT.md` sec 6, PyPI-verified, pending `evidence/VERSIONS.lock` by Bhavya/Manas):
  - `pydantic==2.14.4`, `pydantic-settings==2.16.3`, `psycopg==3.3.9`, `psycopg-pool==3.3.3`, `psycopg-binary==3.3.9`, `cryptography==50.0.2`, `pytest==9.2.0`, `ruff==0.17.6`, `mypy==2.4.1`
OPEN RISKS / QUESTIONS FOR HUMANS:
  - Need PostgreSQL 16+ (or Manas's `compose.yaml` `db` service) to run the 50-thread concurrency test and `schema.sql` validation.
NEXT: A0/A2 real API schemas + auth slice (`services/api/`), while continuing 5-min integration checks.

