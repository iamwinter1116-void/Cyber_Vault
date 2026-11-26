# Hand-off notes · Manas (role D)

## 2026-11-26 · Phase 0 branch preparation and Phase 1 interface inventory

Current task: M1 repository scaffold, preceded by verified Manas branch setup. Host: local Windows checkout `N:\SFIC`;
this is not the Ubuntu demo VM and no runtime/security result is claimed. Baseline commit before this note:
`6dc40c8df5381240b79c32148eb8b1525ef8e508`.

Observed commands and results:
- `git fetch origin` exited 0; `git switch work/manas` exited 0.
- `git status --short --branch` showed `## work/manas...origin/work/manas` with no changed files before this note.
- `git rev-parse HEAD` and `git rev-parse origin/work/manas` both returned the baseline commit above.
- `git rev-parse --abbrev-ref --symbolic-full-name '@{u}'` returned `origin/work/manas`.
- Copied `team/manas/CLAUDE.local.md` to root `CLAUDE.local.md`; `git check-ignore -v CLAUDE.local.md`
  confirmed `.gitignore:1` excludes it.
- `git ls-remote --heads origin` showed all six branches at the same baseline commit before this note.

Phase 1 inventory: `Makefile`, `compose.yaml`, and `db/init/` do not exist. The Parth, Henil, and Bhavya handoff
files contain only their templates; all four remote work branches still point to the planning baseline. No service
implementation, owner Dockerfile, start command, or health command is available to validate. The contract defines
five services, network/mount/DB-role boundaries, variable names, and canonical Makefile targets, but M1 explicitly
requires each owner's executable service interface before wiring their service block.

Required owner handoffs before Phase 1 can close:
- Parth: runner build context/image, exact start and readiness commands, runtime dependencies, socket/volume mounts,
  host preflight script path and command, and workload image requirements.
- Henil: API and notary build contexts/images, exact start and readiness commands, database role/DSN use, schema/init
  requirements, migrations if any, and health response behavior.
- Bhavya: web build output and proxy/static serving contract, contract/security/e2e test commands, verifier CLI, and
  evidence output paths.

State: Phase 0 complete; Phase 1 incomplete pending owner handoffs. No application code, mock, stub, or simulation
was added; no product or security test was run or claimed to pass. Next action after verified handoffs: implement M1 on
`work/manas`, then run the checks required by its done-when criteria on the proper host.

## 2026-11-26 · Local instruction distribution repair

While checking Henil's M1 handoff, confirmed that `.gitignore` ignored `CLAUDE.local.md` at every directory depth;
none of the four `team/<name>/CLAUDE.local.md` files was tracked in the baseline. Changed the ignore rule to
`/CLAUDE.local.md` so only the root machine-specific copy remains ignored, and staged all four team templates.
`git check-ignore -v CLAUDE.local.md` reports the root rule; `git check-ignore -v team/henil/CLAUDE.local.md`
has no output, meaning the distributable template is no longer ignored. `git diff --cached --check` exited 0.
No application implementation or runtime/security test is claimed by this repository setup fix.

## 2026-11-26 · Real local PostgreSQL integration slice

Task: M1 database initialization, local development evidence only. Host: Manas Windows machine with Docker Desktop
29.8.1, not the Linux demo host. Database: official `postgres:16` image at digest
`sha256:07abc3f43c9395b0bdbbab36bc25ddb0e8d83cd4fcafb5fb7d6abe14ff156dd8`, reporting PostgreSQL 16.16.
Container `abh-local-db` uses a named data volume and publishes only `127.0.0.1:15432` for local testing.
Generated owner/API/runner/notary passwords in ignored `secrets/`; no values were printed or committed.

Changed: `db/init/01-schema-and-roles.sh` applies frozen `contracts/schema.sql` once and sets passwords for the three
runtime roles from secret files. No schema or owner feature code changed.

Observed checks:
- Docker daemon and PostgreSQL container started; initialization log shows the schema and three `ALTER ROLE` commands.
- `docker exec ... sh -n /docker-entrypoint-initdb.d/01-schema-and-roles.sh` exited 0.
- Real PostgreSQL has 9 public tables and roles `abh_api`, `abh_runner`, `abh_notary`.
- `has_table_privilege` shows all three can SELECT/INSERT audit_log and none can UPDATE/DELETE it.
- `pg_isready` reported accepting connections; Windows loopback port 15432 is reachable.
- A host-side connection with an incorrect `abh_api` password was rejected. Container-local loopback uses PostgreSQL
  image trust rules, so only the host-side rejection is used as password evidence.
- A temporary read-only checkout of Henil commit `7b4f792` ran `pytest tests/unit -q`: 22 passed, exit 0.
- Against the live database, 50 concurrent calls to Henil's actual `audit.append` produced seq 1..50 with no gaps;
  all stored `prev_hash` links and recomputed record hashes matched. The temporary test exited 0.
- After `docker restart abh-local-db`, `pg_isready` passed and the 50 rows persisted.

Blocking defect found in Henil's real API slice: a live `GET /api/v1/healthz` returned 200 with
`{"status":"ok","db":true}`. A real unknown-email `POST /api/v1/auth/login` returned 401, but the audit row count
increased by 0; the contract requires one denied record. The temporary test failed on that assertion. In
`services/api/routes/auth.py`, the denied append occurs inside a transaction that exits by raising `ApiError`,
which rolls back the append. Henil owns the fix; no API code was changed here.

Status: local DB initialization and core append evidence passed. M1 full stack, G0, T-AUTH contract suite, sandbox,
and security acceptance remain open. No mock, stub, simulation or Linux-host pass is claimed.
