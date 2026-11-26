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

## 2026-11-26 · Task A0/A2 local implementation slice (`services/api` schemas, middleware, security, R01–R03, R31)

TASK: A0/A2 · Canonical schemas, security middleware, Argon2id/CSPRNG sessions, R01–R03 + R31 (`docs/16_BUILD_NOW_HOST_LATER.md` local slice; no 501 stubs)
STATUS: partial (schemas, security helpers, middleware, error envelopes, and R31 healthz tested locally; DB-backed login/logout/me/lockout paths and T-AUTH-01..05 contract tests pending live PostgreSQL)
CHANGED:
  - `services/__init__.py` (1 line)
  - `services/api/__init__.py` (1 line)
  - `services/api/schemas.py` (218 lines)
  - `services/api/middleware.py` (78 lines)
  - `services/api/security.py` (53 lines)
  - `services/api/deps.py` (122 lines)
  - `services/api/main.py` (39 lines)
  - `services/api/routes/__init__.py` (1 line)
  - `services/api/routes/health.py` (26 lines)
  - `services/api/routes/auth.py` (218 lines; total `services/api` = 756 lines <= 1100 budget)
  - `tests/unit/api/__init__.py` (1 line)
  - `tests/unit/api/test_schemas_and_auth.py` (65 lines)
COMMANDS RUN (with exit codes):
  $ wsl -d Ubuntu -- env PYTHONPATH=/mnt/e/CyberVault/Cyber_Vault /home/henillol/.venv-cybervault/bin/pytest /mnt/e/CyberVault/Cyber_Vault/tests/unit -v -> 0 (22 passed in 1.56s)
  $ wsl -d Ubuntu -- /home/henillol/.venv-cybervault/bin/ruff check /mnt/e/CyberVault/Cyber_Vault/core /mnt/e/CyberVault/Cyber_Vault/services /mnt/e/CyberVault/Cyber_Vault/tests/unit -> 0 (All checks passed!)
  $ wsl -d Ubuntu -- env MYPYPATH=/mnt/e/CyberVault/Cyber_Vault /home/henillol/.venv-cybervault/bin/mypy --strict /mnt/e/CyberVault/Cyber_Vault/core/abh_core /mnt/e/CyberVault/Cyber_Vault/services/api /mnt/e/CyberVault/Cyber_Vault/tests/unit -> 0 (Success: no issues found in 16 source files)
  $ wsl -d Ubuntu -- wc -l /mnt/e/CyberVault/Cyber_Vault/services/api/*.py /mnt/e/CyberVault/Cyber_Vault/services/api/routes/*.py -> 0 (756 total)
TESTS: 22/22 unit tests passed (`tests/unit/core` + `tests/unit/api`); T-AUTH-01..05 against real PostgreSQL/HTTPS not yet run
VERIFIED FACTS:
  - Input schemas forbid extra fields (`extra="forbid"`); `EnvCreate` restricts `template` to `"app-target"`.
  - Argon2id PHC string starts with `$argon2id$` and includes `m=19456,t=2,p=1`; CSPRNG session token decodes to 32 bytes; SHA-256 digest is 64 hex chars.
  - Middleware sets `X-Request-ID`, `Content-Security-Policy: default-src 'self'`, `X-Content-Type-Options: nosniff`, `Referrer-Policy: no-referrer`, `Cache-Control: no-store`, and canonical error envelopes for 401/422/500 without leaking stack traces.
  - PyPI verified for `fastapi==0.165.0`, `uvicorn==0.54.0`, `argon2-cffi==25.1.0`, `python-multipart==0.0.34`, `PyYAML==6.0.4`, `httpx==0.28.1`, `types-PyYAML==6.0.12.20261122`.
UNVERIFIED / ASSUMED:
  - Live PostgreSQL execution of `POST /api/v1/auth/login`, `POST /api/v1/auth/logout`, `GET /api/v1/auth/me`, lockout, and `healthz` `db=true` is unverified until PostgreSQL is available.
  - Remaining 27 rules in `contracts/rbac_matrix.yaml` (`R04`–`R30`) are not yet registered (per `docs/16_BUILD_NOW_HOST_LATER.md`, no 501 stubs).
DEGRADED PATHS: none
NEW DEPENDENCIES (allowlisted, PyPI-verified, pending `evidence/VERSIONS.lock`):
  - `fastapi==0.165.0`, `uvicorn==0.54.0`, `argon2-cffi==25.1.0`, `python-multipart==0.0.34`, `PyYAML==6.0.4`, `httpx==0.28.1`, `types-PyYAML==6.0.12.20261122`
OPEN RISKS / QUESTIONS FOR HUMANS:
  - `services/api` is at 756/1100 lines; will keep A3–A6 compact and refactor shared SQL helpers in A7 to stay within the 1100-line ceiling.
NEXT: A3 (`authz.py` RBAC matrix engine + `users`/`teams`/`templates` routes `R04`–`R10`), while continuing 5-min checks on `origin/integration`.

## 2026-11-26 · Task A3 local implementation slice (`authz.py` + `R04`–`R10`)

TASK: A3 · RBAC matrix engine (`authz.py`) and `users`/`teams`/`templates` routes (`R04`–`R10`)
STATUS: partial (matrix loading, 31-rule validation, startup unknown-route refusal, ruff, mypy --strict, and unit tests pass; DB-backed R04–R10 and T-RBAC-01..12 pending PostgreSQL + Bhavya contract suite)
CHANGED:
  - `services/api/authz.py` (128 lines)
  - `services/api/routes/users.py` (158 lines; R04–R06 with BR1/BR2 + session invalidation)
  - `services/api/routes/teams.py` (141 lines; R07–R09 with live SQL usage)
  - `services/api/routes/templates.py` (42 lines; R10 `[T0.H2.N2]` templates)
  - `services/api/main.py` (44 lines; mounts new routers + runs `verify_route_coverage`)
  - `tests/unit/api/test_authz.py` (22 lines)
COMMANDS RUN (with exit codes):
  $ wsl -d Ubuntu -- env PYTHONPATH=/mnt/e/CyberVault/Cyber_Vault /home/henillol/.venv-cybervault/bin/pytest /mnt/e/CyberVault/Cyber_Vault/tests/unit -v -> 0 (24 passed)
  $ wsl -d Ubuntu -- /home/henillol/.venv-cybervault/bin/ruff check /mnt/e/CyberVault/Cyber_Vault/core /mnt/e/CyberVault/Cyber_Vault/services /mnt/e/CyberVault/Cyber_Vault/tests/unit -> 0 (All checks passed!)
  $ wsl -d Ubuntu -- env MYPYPATH=/mnt/e/CyberVault/Cyber_Vault /home/henillol/.venv-cybervault/bin/mypy --strict /mnt/e/CyberVault/Cyber_Vault/core/abh_core /mnt/e/CyberVault/Cyber_Vault/services/api /mnt/e/CyberVault/Cyber_Vault/tests/unit -> 0 (Success: no issues found in 21 source files)
TESTS: 24/24 unit tests passed; T-RBAC-01..12 against live DB pending PostgreSQL
VERIFIED FACTS:
  - `contracts/rbac_matrix.yaml` parses 31 rules; startup check passes for all mounted routes and raises `RuntimeError` if an unmapped `/api/v1` route is registered.
UNVERIFIED / ASSUMED:
  - Live PostgreSQL execution of R04–R10, BR1 (`LAST_ADMIN`), BR2 (`SELF_ROLE_CHANGE`), session deletion on disable/role change, and `alert.authz_denied_burst` (5 denials in 60s) is unverified without PostgreSQL.
DEGRADED PATHS: none
NEW DEPENDENCIES: none
OPEN RISKS / QUESTIONS FOR HUMANS:
  - `services/api` is currently ~1230 lines (over the 1100-line ceiling); will deduplicate SQL/helper code in Task A7 (or earlier) to bring it under 1100 lines.
NEXT: A4 (`envs`, `jobs`, `files`, `ai-scans`, quota admission `R11`–`R21`), while continuing 5-min checks on `origin/integration`.

