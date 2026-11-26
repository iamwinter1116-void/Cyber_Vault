# Manas build and integration execution plan

Authority: `docs/04_CONTRACTS.md` sections 9 and 11, `docs/16_BUILD_NOW_HOST_LATER.md`, and the owner handoffs. This plan tracks local implementation separately from Linux host acceptance.

## Phase 1 — Database and real command interface

1. Verify the existing Compose database is healthy, the frozen schema is present, and the three application roles have distinct credentials and expected access.
2. Wire every canonical Make target to a real implemented command or an explicit nonzero refusal naming the missing component. Preserve `preflight`, `secrets`, `db-up`, and `db-down`.
3. Check Make parsing, run safe targets, inspect failure exits for unavailable stack pieces, and record exact results.

Done when the database checks and every currently runnable target execute successfully, while targets dependent on absent services fail clearly. This phase does not imply M1 or G0 is complete.

Local result on 26 November 2026: phase 1 command wiring and database checks complete. `make secrets` and `make db-up` exited 0; a fresh `abh-m1-check` Compose project initialized `abhedya_test` with nine tables, both audit protection triggers, and authenticated all three application roles, then was removed with its volume. Full-stack targets refused because the services are absent. `make openapi` still fails because the Python environment lacks `psycopg`; the package lock is incomplete. M1 remains partial.

Additional local database evidence: after PR #14 recorded the runner's direct packages, a second disposable Docker Desktop project (`abh-pg-suite`) ran `tests/unit/runner/live_pg_suite.py` against real PostgreSQL: 14 passed. The project and its volume were removed. This does not verify Docker sandbox calls or any Linux/runsc condition. Phase 2 still needs the missing API/build dependency entries and owner image definitions.

## Phase 2 — Service build and Compose wiring

Use the actual owner-provided image/build definitions, runtime command, health response, and dependency pins for `api`, `runner`, `notary`, and `proxy`. Verify only the proxy publishes a host port and only runner mounts the Docker socket. Run a clean stack and service-level health checks on Docker Desktop as local integration evidence. Leave Linux isolation acceptance open.

## Phase 3 — CI and fast checks

Wire a pinned CI workflow to executable Make targets. Include strict lint/type/unit checks, OpenAPI drift and placeholder checks when their dependencies and generated contract exist. Fail on missing prerequisites. Verify the workflow on a real PR.

## Phase 4 — Whole-stack integration

Run contract and safe end-to-end checks against the real local stack, repair only Manas-owned build wiring, and send component failures to their owners. Record commit, commands, exit codes, and pending Linux host tests. Do not promote to `main` until the required gates pass.
