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

## 2026-11-26 · M1 Compose database slice

Task: Manas-owned M1 database wiring, local development evidence. Host: Windows with Docker Desktop 29.8.1 and
Compose 5.5.1; this is not the Linux demo host. Changed `compose.yaml` and `Makefile`.

- `compose.yaml` runs the pinned official PostgreSQL 16 image, applies the frozen schema through the existing
  `db/init/01-schema-and-roles.sh`, mounts ignored password files as Compose secrets, persists data in a named volume,
  and attaches only to an internal `control` network. The `db` service publishes no host port.
- `make db-up` waits for the real database health check; `make db-down` stops it without removing data;
  `make preflight` invokes Parth's actual `host/preflight.sh` when his branch is integrated.
- `docker compose config --quiet` and `git diff --check` exited 0. `make db-up` exited 0 and reported healthy.
- SQL observed 9 public tables and roles `abh_api`, `abh_runner`, `abh_notary`. All three can SELECT/INSERT
  `audit_log`; none can UPDATE/DELETE it. A wrong `abh_api` password over TCP to service `db` was rejected
  (psql exit 2); the correct password from its secret file connected as `abh_api`.
- `docker inspect sfic-db-1` reported empty port bindings and `5432/tcp: null` for published ports.
- `make db-down` then `make db-up` both exited 0. The PostgreSQL system identifier matched before and after;
  all 9 tables remained. The older standalone `abh-local-db` test container was stopped, not deleted.
- `make -n preflight` showed `sh host/preflight.sh`; the script is only on Parth's branch and was not run here.

Status: M1 database Compose slice passed locally. The full Compose stack, canonical remaining Make targets, CI,
Linux preflight, and G0 are still open. The API denied-login audit rollback reported above is still open on Henil's branch.
No mock, stub, simulation, or Linux-host pass is claimed.

## 2026-11-26 · M1 secrets target and teammate activity review

Task: Manas-owned `make secrets` and review of new owner heads. Host: Windows with Python 3.11 and an already
installed `cryptography` 50.0.1. Changed `Makefile` and `db/init/generate_secrets.py`.

- `make secrets PYTHON=python` exited 0 twice. It preserved the hashes of the four existing database password
  files and created a raw 32-byte Ed25519 seed plus its 32-byte public key as hex. A sign/verify operation using
  the generated pair passed. All six files are under ignored `secrets/`; no value was printed or committed.
- A temporary-directory run created six files, ran again without changes, then rejected a deliberately mismatched
  public key. The disposable test files were removed by Python's TemporaryDirectory.
- `git diff --check` exited 0. Default `PYTHON=python3` is for the eventual Linux host and was not run here;
  the Windows invocation explicitly overrides it with the installed `python` command.
- `origin/work/henil` advanced to `579d2af`: 31 API routes registered and a notary service. Its handoff reports
  29 unit tests passing but live PostgreSQL/witness checks pending; the API/notary line budgets are exceeded
  pending Henil's A7 trim. The denied-login audit rollback previously observed remains in `auth.py`.
- `origin/work/parth` advanced to `9c92eb9`: reconcile SQL, object cleanup, storage ladder and template loading.
  Its handoff reports 30 local tests passing and a 6-case PostgreSQL test not run. Runner package versions are
  listed there for Bhavya to add to `evidence/VERSIONS.lock`; that entry is not yet on Bhavya's branch.

Next: after Bhavya records the runner dependencies, execute Parth's six PostgreSQL tests on a disposable Compose
project with a temporary combined checkout of Parth and Henil. Do not count this as Docker/runsc acceptance.

## 2026-11-26 · Integration slice promotion

Task: keep `integration` useful for owner branches while preserving pending acceptance status. Manas merged three
reviewed PRs into `integration`; `main` was not changed.

- PR #1, Manas M1 work-order, Compose database, secret generator and Makefile slice: merge commit `5581509`.
  `docker compose config --quiet`, `make db-up`, schema/role/password/privilege checks and database persistence
  had passed locally. Full-stack and Linux acceptance remain pending.
- PR #3, Henil's original A1 core commit `d3b772e`: merge commit `8db71ed`. The core and its unit test files
  were unchanged on Henil's later branch. Henil's handoff reports 19 unit/vector, ruff and mypy passes;
  Manas's earlier real PostgreSQL 50-thread append check passed with the same core. Later API code was excluded.
- PR #4, Parth's B0 scripts through corrected commit `28cf689`: merge commit `26a71e0`. `git diff --check` passed;
  Git-for-Windows `sh -n` and `dash -n` passed on both scripts; total 150 lines. Windows `sh host/preflight.sh`
  exited 1 at check 1 (`FAIL 1 os: MINGW64_NT...`), with no later check run. On the merged integration tree,
  `make preflight` invoked that script and Make exited 2 after the same check-1 refusal. The real Linux B0 checks
  are all pending.
- `work/manas` was fast-forwarded locally to `origin/integration` after these merges. No contributor's feature
  source was edited by Manas; the two slice PRs pointed at the owners' original commits.

Open: Parth PR #2 runner needs its six real PostgreSQL tests and dependency entries in Bhavya's lock file.
Henil's later API/notary code still has the denied-login audit rollback observed against PostgreSQL, an API
line-budget overage, and unrun live checks. Bhavya's test/console branch has no open PR yet. No G0–G4 gate
or Linux-dependent objective is green.

## 2026-11-26 · Follow-up PR review after owner sync

Task: review merge readiness of the current owner branches after integration at `26a71e0`. No additional merge
was made in this review.

- `origin/work/parth` at `e67a81b` is synced with integration. In a detached temporary worktree of that commit,
  `python -m pytest tests/unit/runner/test_launch.py tests/unit/runner/test_templates.py
  tests/unit/runner/test_state.py tests/unit/runner/test_storage.py -q` exited 0: 32 passed in 0.12 s.
  `python -m compileall -q services/runner tests/unit/runner` exited 0. The six-case
  `tests/unit/runner/test_reconcile_pg.py` was not run; Docker/runsc/storage calls remain untested. PR #2 stays open.
- Earlier owner commit `400dfe9` was separately checked in a detached worktree: 22 tests passed using
  `python -m unittest discover -s tests/unit/runner -p 'test_*.py' -v`, and compileall passed. A direct
  module-path unittest invocation failed because this Windows Python installation resolves another `tests`
  package first; discovery from the runner test directory passed. That commit has since been superseded by
  Parth's wrapper removal, so it was not separately merged.
- `origin/work/bhavya` at `b25ee1e` records `psycopg==3.3.9` and `psycopg-pool==3.3.3` but not
  `psycopg-binary`, `docker`, or `pydantic-settings` in `evidence/VERSIONS.lock`. This Windows host has no
  system `libpq`; installing the runner's requested `psycopg[binary,pool]` must wait for the binary entry.
  `git diff --check origin/integration...origin/work/bhavya` reports a trailing blank line in
  `evidence/bug-journal.md`; Bhavya's full branch has no PR and no live-stack test result.
- `origin/work/henil` at `154a881` is synced with integration but its `auth.py` still raises `ApiError`
  inside the transaction after appending denied-login audit events. Manas's real PostgreSQL test previously
  observed zero denied rows after a 401. The full API branch has no PR and remains unmerged.

Next: obtain the missing dependency log entries from Bhavya, run Parth's six tests on a disposable Compose
database, and re-review PR #2. Henil owns the auth rollback fix. No Linux-host result is claimed.

## 2026-11-26 · Integrated local slices and progress baseline

Manas merged PR #2 (Parth runner) as an incomplete local slice at `e1d5cde`, PR #5 (Henil API/notary
code through `bcaa3bb`, excluding the unsafe later PostgreSQL test) at `82673ec`, and PR #6 (Bhavya
verifier/tests) at `0a664f9`. `main` remained at `6dc40c8`. The PR bodies list each pending host and live
test. On Parth `2075dbf`, Manas independently ran five runner modules: 44 passed, exit 0; compileall
exited 0. On Bhavya `79a89f2`, compileall and verifier CLI help exited 0; verifier-side vector selection
with the versions in her lock file exited 0 with 22 passed and 7 core-side cases deselected.

`team/manas/work/PROGRESS.md` records a conservative 15/33 = 45.5% integrated-implementation coverage
from the 33 named owner task prompts. This is not objective acceptance: 0/9 mandatory objectives and
0/5 gates have the required host evidence. The later Henil database test still needs a disposable-database
guard and separate owner/API DSNs before it can be run or integrated. Bhavya's dependency lock and security
test discrepancies remain open. No Linux-host pass is claimed.

## 2026-11-26 · M1 phase 1 database and Make interface

TASK: M1 phase 1, using `team/manas/work/PLAN_M1_M3.md`.
STATUS: local command wiring and database initialization verified; M1 remains partial because `api`, `runner`, `notary`, `proxy`, console, and approved dependency entries are absent.
CHANGED: `Makefile`, `db/init/require.py`, `team/manas/work/PLAN_M1_M3.md`, this handoff.
COMMANDS RUN (Windows Docker Desktop, `work/manas`):
  - `docker compose config --quiet` -> 0; the existing `sfic-db-1` stayed healthy throughout.
  - `make secrets` -> 0, existing secret files preserved; `make db-up` -> 0, database healthy.
  - `docker compose -p abh-m1-check -f compose.yaml -f T:\CyberVaultReview\m1-db-override.yaml up -d --wait db` -> 0 on a new `abhedya_test` database. SQL verification -> 0: nine public tables, two audit protection triggers, `abh_api` cannot UPDATE audit_log; TCP login as `abh_api`, `abh_runner`, and `abh_notary` -> 0. `down -v` -> 0 removed only the disposable project; `sfic-db-1` remained healthy.
  - `make up`, `check-fast`, `test-contract`, `test-security`, `test-e2e`, `scan`, `demo-reset` -> nonzero refusal, each naming its missing real service, console, OpenAPI file, scan runner, or reset script.
  - `python db/init/require.py placeholders` -> 1: `services/api/schemas.py:154` still names `stub-vulnerable` and `stub-guarded` (Henil-owned O9 contract interpretation; no edit made here).
  - `make openapi` -> nonzero: `ModuleNotFoundError: psycopg` in this Windows Python environment. `make tamper-drill` without opt-in -> nonzero refusal; no database change.
  - `python -m compileall -q db/init` -> 0; `git diff --check` -> 0.
VERIFIED FACTS: Canonical Make target names now map to existing code or an explicit refusal. The fresh DB init script applies the frozen schema and role passwords. No host isolation or gate test was run.
UNVERIFIED: Full stack startup, owner service container images, TypeScript checks, OpenAPI generation, CI, runner PostgreSQL suite, and Linux/runsc tests.
DEGRADED PATHS: none.
NEW DEPENDENCIES: none installed.
OPEN RISKS / NEXT OWNERS: Bhavya must record missing allowlisted package versions (`psycopg-binary`, `docker`, `pydantic-settings` and service build dependencies) in `evidence/VERSIONS.lock` before installation. Henil owns the O9 stub-named schema field. Owners must supply actual service image/build definitions before M1 phase 2 Compose wiring.

## 2026-11-26 · Parth B5 integration review

TASK: Review Parth `f755530` and PR #12, then refresh the implementation scorecard.
STATUS: merged as an incomplete local B5 slice at integration `20324e0`; no objective or gate accepted.
COMMANDS RUN (Windows Python 3.11, detached Parth worktree): explicit `python -m pytest` of six pure runner modules -> 50 passed, exit 0; `python -m compileall -q services/runner tests/unit/runner` -> 0; `git diff --check` -> 0. `unittest discover` failed due this Python installation resolving a different `tests` package, so the explicit pytest invocation was used. No PostgreSQL or Docker exec call was run.
VERIFIED FACTS: PR #12 touched only Parth-owned code/tests and his handoff. The live PostgreSQL suite requires a disposable database and explicit opt-in, and is excluded from ordinary test collection. The runner's 857/800 code-line overage is documented by Parth; B6 remains constrained. `team/manas/work/PROGRESS.md` now counts B5, giving 16/33 = 48.5% integrated implementation coverage.
UNVERIFIED: 14 live PostgreSQL tests, Docker exec behavior, gVisor, isolation/resource tests, ruff/mypy, and the proposed sandbox image CR. G0–G4 and O1–O9 remain unaccepted.
NEXT: Bhavya's dependency log and the four-person sandbox-image decision are needed before those dependent tests and image builds.

## 2026-11-26 · Disposable PostgreSQL runner suite on Docker Desktop

TASK: Exercise Parth's guarded real PostgreSQL suite without a Linux/runsc host, after Bhavya's dependency entries merged in PR #14.
STATUS: 14 runner SQL tests passed as local database evidence; no sandbox Docker/runsc objective or gate accepted.
HOST / BASE: Manas Windows laptop, `work/manas` synced to `integration` `0f8db47`. Existing `sfic-db-1` was left running and healthy.
SETUP: Installed only recorded direct package versions into `T:\CyberVaultReview\pydeps-runner` with `pip --no-deps`: psycopg 3.3.9, psycopg-binary 3.3.9, psycopg-pool 3.3.3, docker 7.2.0, pydantic-settings 2.16.3, PyYAML 6.0.4, pytest 8.4.2, cryptography 50.0.0. The pre-existing host `pydantic` was 2.13.4 and is not recorded in VERSIONS.lock, so this is not a reproducible full-stack dependency lock.
COMMANDS / RESULTS:
  - Temporary Compose override set `POSTGRES_DB=abhedya_test`. The first attempt kept the database on `control` only; Docker Desktop did not publish the requested host port (`Test-NetConnection` false). No test ran on that attempt.
  - The disposable `abh-pg-suite` project was recreated with a second, test-only `test_access` network and `127.0.0.1:55432:5432`; `docker port` showed the loopback binding. The repository Compose file was not changed.
  - With `ABH_TEST_ALLOW_DISPOSABLE_DB=1`, separate owner and `abh_runner` DSNs, and the isolated package target on `PYTHONPATH`, `python -m pytest tests/unit/runner/live_pg_suite.py -q` -> exit 0, `14 passed in 2.70s`. Password values were read from ignored secret files and not printed.
  - `docker compose -p abh-pg-suite ... down -v` -> exit 0; the disposable container, networks and volume were removed. `docker compose ps` still showed the normal `db` healthy.
  - A read-only import attempt for Henil's live suite -> exit 1, `ModuleNotFoundError: No module named 'argon2'`. No unrecorded API package was installed and that suite was not run.
VERIFIED: Real PostgreSQL transaction/role behavior for the 14 runner tests on Docker Desktop. NOT VERIFIED: Docker container launch/exec, gVisor, Linux isolation/resource limits, Henil's API/notary live suite, full Makefile or gate acceptance.
NEXT OWNERS: Bhavya needs to record the remaining allowlisted API/build package versions (including `argon2-cffi`, `fastapi`, `pydantic`, `uvicorn`, `python-multipart`, `ruff`, `mypy`) before a reproducible API image and Henil suite can be run. Henil then handles any API/notary test failure. Parth's sandbox image CR and runner budget remain open.

## 2026-11-26 · Parth reduction PR #16 review

TASK: Review and merge Parth's type-only runner reduction and two unapproved change-request proposals.
STATUS: PR #16 merged at integration `0833e1c`; implementation coverage unchanged at 16/33. Neither proposal is approved by the merge.
COMMANDS RUN: On detached `7f86459` (Windows), `python -m pytest` over six pure runner modules -> 50 passed, exit 0. The guarded `tests/unit/runner/live_pg_suite.py` on a fresh disposable `abhedya_test` PostgreSQL project -> 14 passed in 2.49s, exit 0. The disposable project and volume were removed (`down -v` exit 0); normal `db` remained healthy. `git diff --check` -> 0.
VERIFIED: The code change removes unused runtime fields and a type-only protocol; no sandbox policy code changed. Parth's recorded count is now 850/800 non-test runner lines, still over budget.
UNVERIFIED: Docker/runsc behavior, sandbox images, host acceptance, and the proposed 1000-line budget and base images. All four approvals remain required for a budget or dependency-contract change.

## 2026-11-26 · Manas M1 budget reporting and PR #20/#21 review

TASK: Review Bhavya's PR #20 and Parth's PR #21; make the documented code budgets visible from `make check-fast`.
STATUS: PR #21 merged as docs only. PR #20 held for owner fixes. M1 budget-report slice written locally;
  `make check-fast` remains red because existing overages and absent components are reported as failures.
CHANGED: `db/init/report_budgets.py`, `Makefile`, `team/manas/work/PROGRESS.md`, this handoff.
COMMANDS AND RESULTS (Manas Windows host, work/manas before commit):
  `python db/init/report_budgets.py` -> exit 1; core 180/300, runner 850/800 OVER, API 2000/1100 OVER,
  notary 131/150, verifier 144/180, host 136/150, sandbox/web missing.
  `make check-fast` -> exit 1 at the new budget report; later ruff/mypy/TypeScript/unit steps did not run.
  `python -m pytest tests/unit/runner/test_launch.py tests/unit/runner/test_templates.py
   tests/unit/runner/test_state.py tests/unit/runner/test_storage.py tests/unit/runner/test_metrics.py
   tests/unit/runner/test_exec_policy.py -q` -> exit 0, 50 passed in 0.10 s.
  `python -m compileall -q db/init/report_budgets.py` -> exit 0. `git diff --check` -> exit 0.
REVIEW: PR #20 (`cdc62e9`) owner paths only, local tests reported by Bhavya but live tests unrun. Held because
  its module RBAC fixture requests R17 immediately after R12 without waiting for observed_state=running;
  T-RES-01's 5 s alert timer begins after up to 30 s of job polling, T-RES-02 checks only the DB row after
  DELETE, T-RES-03 omits host-space and neighbour conditions, T-RES-05 permits 201, and T-RES-06 inspects
  only containers. T-ISO-04 probes only toolbox, not target; T-WL-01 resolves `target` from bravo's own
  app-target network, which may resolve bravo's target rather than test alpha's name.
UNVERIFIED: no Linux/runsc acceptance; the budget count follows Python tokenizer non-comment lines excluding
  docstrings and plain source-line counting elsewhere. It reproduces Parth's 850 runner count; owner CRs are
  still pending. No objective or gate green. `contracts/openapi.yaml` remains absent.
NEXT: ask Bhavya to correct PR #20's live-test setup and assertions; request owner decision on dependency
  transitives so Manas can generate OpenAPI with recorded packages. Continue M1 Compose once owners provide
  build images, startup/health commands and approved dependency/image decisions.

## 2026-11-26 · Budget reporter source coverage and Bhavya PR #20 follow-up

TASK: Correct Manas's budget reporter after Parth found that YAML/rule files under sandbox were omitted;
  review Bhavya's revised PR #20 at d6f972e and Parth's docs-only PR #23.
STATUS: PR #23 merged as decision papers only; both CRs remain unapproved. PR #20 stays open for live-test
  assertion fixes. No objective or gate green.
CHANGED: `db/init/report_budgets.py` now reads limits directly from the docs/05 code-budget table, validates
  the expected component set, and includes YAML/JSON/YARA/rule source in sandbox and web counts.
COMMANDS AND RESULTS (Manas Windows host, work/manas before commit):
  `python db/init/report_budgets.py` -> exit 1; core 180/300, runner 850/800 OVER, API 2000/1100 OVER,
  sandbox MISSING, notary 131/150, verifier 144/180, web MISSING, host 136/150.
  `python -c '...documented_budgets()...'` -> exit 0; all eight documented limits read; .yaml and .yar
  are selected source suffixes. `python -m compileall -q db/init/report_budgets.py` -> exit 0.
  `git diff --check` -> exit 0.
REVIEW: Bhavya fixed the RBAC wait and target probing. T-RES-01 still looks for any prior alert in a new
  five-second window after job completion, so it cannot prove event-to-alert latency. T-RES-02 records a
  configured pids limit, not evidence that it contained the fork bomb; its hostile env lacks fallback cleanup
  if assertions fail. T-RES-03 measures free space before provisioning two envs and allows an unapproved 16 MiB
  surplus above the exact quota. T-RES-04 never measures CPU use and samples health for only about four seconds.
  T-RES-05 still lacks denied-audit and SQL-sum assertions. T-RES-06 restarts the runner after requesting the
  env without proving it was mid-provision, and its duplicate check is vacuous because Docker names are unique.
  T-ISO-04 can omit the detonator subcheck through an environment flag without linking a recorded cut decision.
UNVERIFIED: no Linux/runsc or live-stack checks run in this review. Source counting for non-Python files is
  nonblank/non-comment lines; no sandbox/web source exists yet to measure.
NEXT: send Bhavya the remaining precise assertions; keep PR #20 open. Continue the dependency/image and
  runner/API budget CR reviews before implementing service Compose blocks or generating OpenAPI.

## 2026-11-26 · Independent PR #20 collection and M1 readiness recheck

TASK: Recheck revised Bhavya PR #20 at d6f972e without modifying her paths; confirm what Manas can wire now.
STATUS: PR #20 remains open. PR #23 (decision papers) and PR #24 (budget reporter fix) merged; neither
  approves a CR. M1 phase 2 remains incomplete.
COMMANDS AND RESULTS (Manas Windows laptop):
  Fresh detached worktree at d6f972e: `python -m compileall -q tests/contract tests/security tests/e2e
  tools/collect_evidence.py` -> exit 0. `git diff --check origin/integration...HEAD` -> exit 0.
  With isolated recorded runner dependencies on PYTHONPATH, `pytest tests/contract/test_rbac_matrix.py
  --collect-only -qq` -> exit 0, 181 cases. `pytest tests/security --collect-only -q` -> exit 0,
  28 cases. `pytest tests/e2e --collect-only -q` -> exit 0, 4 cases.
  `pytest tests/security/test_isolation.py::test_t_static_01_compose_and_runner_no_dangerous_flags -q`
  -> exit 0, 1 passed. Full contract collection -> exit 1: this isolated host lacks hypothesis;
  187 cases collected before that import error. Bhavya reported full collection on her own host;
  this is an environment limitation, not a verdict on that code.
  `docker compose config --services` -> exit 0, only `db`.
  `make openapi` -> exit 1, ModuleNotFoundError for psycopg in the current Python environment.
  `make check-fast` -> exit 1 at budget report: runner 850/800, API 2000/1100, sandbox and web missing.
REVIEW: T-RES-01 alert timing still is not tied to the OOM timestamp; T-RES-02 does not assert which
  resource contained the fork bomb and leaves the hostile env if an assertion fails; T-RES-03 measures free
  space before two envs are provisioned and allows quota +16 MiB; T-RES-04 does not measure CPU; T-RES-05
  omits denied-audit and SQL-sum checks; T-RES-06 does not ensure restart mid-provision and its uniqueness
  assertion uses Docker-unique names. T-ISO-04's detonation bypass depends on an environment flag without
  a recorded cut decision. No live security test was run here.
NEXT: Bhavya revises PR #20; all four review image/dependency and runner-budget CRs. Manas wires real
  services only after owner images and package decisions, then runs OpenAPI and local integration checks.
