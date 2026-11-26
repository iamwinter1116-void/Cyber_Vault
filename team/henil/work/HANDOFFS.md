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

