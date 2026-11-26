# Change-request PROPOSAL · services/api code budget (role A, Henil)

Status: PROPOSAL for the four-person CR process (`CLAUDE.md` rule 8; `docs/05_OBJECTIVES.md` Code budget). NOT approved.
Requested by Manas (2026-11-26): "make budget-report measures services/api at 2000/1100. Please provide a reduction plan or a separate four-person budget CR; do not treat the existing journal note as approval."

## Counting rule used
Official since PR #22: `db/init/report_budgets.py` (`make budget-report`) counts lines covered by Python tokens, excluding comments, blank lines, and docstrings. On `integration` `59e49dc` it prints `services/api: 2000/1100 OVER`.

## Measured now (per-file code lines via `report_budgets.py`)
- `routes/monitor.py`: 214 (`R22` SSE `LISTEN/NOTIFY` hub, `Last-Event-ID` replay, 15s heartbeat, scope filter; `R23` `/events`)
- `routes/envs.py`: 211 (`R11`–`R17` list/create/get/stop/destroy/metrics/exec + scope enforcement)
- `routes/audit.py`: 199 (`R24`–`R28` list/NDJSON export/checkpoints/pubkey/verify steps 1–4)
- `routes/jobs.py`: 184 (`R18`–`R21` list/get/10 MiB `0400` quarantine upload streaming/ai-scan submission)
- `routes/auth.py`: 167 (`R01`–`R03` Argon2id login, 5-fail lockout, `auth.lockout` + `alert.login_bruteforce`, logout, me)
- `schemas.py`: 162 (22 strict Pydantic models for all 11 resource shapes and request bodies in `04` sec 3–4)
- `routes/users.py`: 138 (`R04`–`R06` list/create/update + `BR1` `LAST_ADMIN`, `BR2` `SELF_ROLE_CHANGE`, session invalidation)
- `routes/teams.py`: 123 (`R07`–`R09` list with live SQL usage, create, quota update)
- `quota.py`: 110 (`SELECT ... FOR UPDATE` team + host-capacity admission control `BR3`)
- `authz.py`: 102 (`contracts/rbac_matrix.yaml` loader, `authorize()`, `record_denied()` + `alert.authz_denied_burst`, startup coverage check)
- `routes/admin.py`: 100 (`R29` live SQL overview, `R30` kill switch)
- `deps.py`: 97 (session cookie SHA-256 lookup, 30m idle / 8h abs expiry, `X-CSRF-Token` check)
- `middleware.py`: 56 (`X-Request-ID`, security headers, canonical error envelopes for `ApiError`/422/HTTP/500)
- `main.py`: 48 (FastAPI app factory, lifespan pool, 10 router mounts, startup matrix check)
- `routes/templates.py`: 32 (`R10` `[T0.H2.N2]` allowlisted templates)
- `security.py`: 30 (Argon2id `m=19456,t=2,p=1`, dummy verify, 32-byte CSPRNG tokens)
- `routes/health.py`: 18 (`R31` `/healthz` with `SELECT 1`)
- `openapi_export.py`: 9 (`make openapi` dump script)
Total: **2000** code lines (with `0` placeholders, `0` `# type: ignore`s, `mypy --strict` passing, every file <= 214 code lines).

## Why 1100 lines is not achievable without breaking contracts or typing
- All 31 routes (`R01`–`R31`) in `contracts/rbac_matrix.yaml` are implemented with real SQL, `mypy --strict` annotations, explicit Pydantic schemas, and no ORM.
- Even aggressive helper extraction across pagination/row-mappers would save ~150–200 lines (~1800 lines), still well above 1100.

## Request
Raise the `services/api` ceiling in `docs/05_OBJECTIVES.md` from `1100` to `2100` code lines as counted by `db/init/report_budgets.py` (leaving 100 lines of headroom for contract-test fixes).
Alternative for the team: none without removing required `R01`–`R31` routes, explicit Pydantic output schemas, or `mypy --strict` typing.
