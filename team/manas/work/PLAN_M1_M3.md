# Manas solo build and integration execution plan

Authority: `docs/04_CONTRACTS.md` sections 9 and 11, `docs/16_BUILD_NOW_HOST_LATER.md`, frozen contracts, and owner handoffs. On 26 November 2026, Manas directed that all remaining implementation work be completed from this checkout. Manas is the sole active implementer and integrator; former owner boundaries do not block edits needed to finish the product. Keep attribution and record cross-component changes. This plan tracks local implementation separately from Linux host acceptance.

## Current operating rules

1. Work in sequential phases. Write and review the phase plan before code; do not advance a phase until its local exit conditions are evidenced.
2. Frozen contracts remain authoritative. Changes to contracts, dependency allowlists, images, security assumptions, or code budgets require the documented change-control approvals before implementation. A solo-work decision does not silently approve pending CRs.
3. Implement real behavior only. No mocks, simulations, stubs, fake success paths, or claims based on unrun checks.
4. Use only recorded/approved dependencies. Record registry/version/hash evidence before installing new packages.
5. Local Windows/Docker Desktop checks are implementation evidence only. Linux Docker Engine/runsc checks and acceptance gates stay pending until run on a real Linux host.
6. Work on `work/manas`, open focused PRs to `integration`, and merge only evidence-supported slices. Never promote to `main` before its gates pass.
7. Do not wait for another person to implement a task. For blocked formal decisions, continue independent work and mark the dependency plainly.

## Updated demo direction — local website first

On 27 November 2026, Manas directed that the immediate demo be a locally served website, without requiring a sandbox or Ubuntu VM. This changes the order of work and the demo scope only; it does not change the frozen definitions of O1–O9 or permit simulated success. Continue building and validating website/control-plane features that work against real local services (currently PostgreSQL). Do not make the local demo depend on `runsc`, Docker sandbox creation, or the demo VM.

For the local website demo:

1. Bring up the real local database and API, then serve the console on loopback. Keep real login, authorization, user/team management, audit queries, verification, and activity behavior connected to the actual API and database.
2. Show only data returned by the API. If an API/service is unavailable, display an explicit unavailable/error state. Do not seed fake dashboard data, simulate an environment, or label a queued job as completed.
3. Keep environment creation/execution, file detonation, and AI red-team actions unavailable until their real workers and approved workload definitions exist. The website may explain their unavailable state; it must not present fabricated results.
4. Treat this as a local product demonstration, not acceptance of the nine objectives. The objective score remains 0/9 until the exact demo-host tests and evidence in `docs/05_OBJECTIVES.md` and `docs/06_VERIFICATION.md` pass. In particular, O1, O3, O5, and O9 require real isolation/workload behavior and cannot be marked complete by a website-only demo.

### Local website implementation sequence

| Slice | Work | Exit evidence |
| --- | --- | --- |
| L1 | Reconcile the pinned API/test packages with the registry; produce a hash-locked transitive dependency candidate for review; after the dependency rule is formally approved, install into an isolated local environment and run the existing API against the live PostgreSQL service | The candidate records exact package versions and artifact hashes without installation; after approval, API health reports the actual DB result and unauthenticated/authenticated routes return contract response shapes |
| L2 | Serve the console against that API; exercise login/session refresh, roles, users/teams/quotas, audit filters/export/verify, and live activity where the API supports it | Browser journeys use real API responses and database state; no browser console errors; each action's resulting API/database state is evidenced |
| L3 | Add clear unavailable states for workload actions that lack a real worker, without generating jobs that remain queued indefinitely | Browser evidence shows the exact unavailable reason and no DB mutation occurs when the unavailable control is used |
| L4 | Run the available local contract/unit/security checks and record every blocked test with its concrete prerequisite | Commands and outputs are recorded; local demo status is reported separately from O1–O9 and G0–G4 |

L1 currently has a dependency-control prerequisite: the installed Python environment lacks `psycopg`, `psycopg_pool`, and `argon2`, and the package/transitive approval question is still open. The backend work sequence is: (1) generate and review a transitive hash-lock proposal from the already recorded API/test versions without installing packages; (2) get the dependency rule recorded under the required CR process; (3) install that exact lock into an isolated local environment; (4) run the API against the real Compose PostgreSQL and exercise the disposable-database suite plus real auth, RBAC, audit, stream and admin routes; (5) fix only code defects evidenced by those runs and return the API to its documented budget. Do not install packages or silently switch dependency policy to make the demo start. This dependency-control path is independent of sandbox work.

## Whole-project solo sequence

| Phase | Scope | Exit condition |
| --- | --- | --- |
| 0 | Reconcile current branches, PRs, frozen contracts, and accepted evidence; update this plan | Current integration baseline and open decisions are recorded; no stale progress claims |
| 1 | Stabilize canonical build/test interfaces, dependency lock process, and reproducible budget report | Targets run real commands or refuse clearly; line counts match documented rules; safe checks have evidence |
| 2 | Complete approved service images and Compose integration for DB, API, runner, notary, proxy | All service build/start/readiness/role/mount interfaces are real; only proxy publishes; only runner gets Docker socket; clean local stack healthy |
| 3 | Complete missing runtime and workload implementation (B2/B6/B7 only after required CRs) | Real sandbox/probes/workloads exist within approved dependencies and budgets; unit and local integration evidence recorded |
| 4 | Complete verifier, console, scans, contract/security/E2E suites | Required local code and tests exist; OpenAPI is generated from implemented routes; all runnable checks pass; host tests remain separately listed |
| 5 | Linux host readiness and acceptance | Real Linux host passes B0 preflight, Docker/runsc and named acceptance tests; evidence includes host, commit, command, exit code, output |
| 6 | Gate review and release rehearsal | G0–G4 and O1–O9 evaluated strictly from required evidence; only then consider `integration` to `main` |

## Phase 0 — Current-state reconciliation

Completed 26 November 2026. `origin/integration` is `59e49dcab76e43f05f0737a3396d7fe42f804fb4`; `origin/main` is `6dc40c8df5381240b79c32148eb8b1525ef8e508`; `work/manas` started this phase at `7210a8a0faeed07b08b59ae554b1ebb84343c424`. Open PRs: #20 Bhavya test changes at `6ddf152` and #26 Parth votes at `f959a09`; both remain open pending review/formal decisions. Parth has voted yes on both CRs; A, C and D slots remain blank. Current implementation and acceptance score remains the last verified 16/33 integrated tasks, 0/9 accepted objectives, 0/5 gates; re-count only after new integration changes. This plan update is the first solo-execution change. Next independent work: complete the exact build interface and dependency evidence workflow without applying pending CRs, then integrate only service images/choices that are already approved.

## Phase 1 — Database and real command interface

1. Verify the existing Compose database is healthy, the frozen schema is present, and the three application roles have distinct credentials and expected access.
2. Wire every canonical Make target to a real implemented command or an explicit nonzero refusal naming the missing component. Preserve `preflight`, `secrets`, `db-up`, and `db-down`.
3. Check Make parsing, run safe targets, inspect failure exits for unavailable stack pieces, and record exact results.

Done when the database checks and every currently runnable target execute successfully, while targets dependent on absent services fail clearly. This phase does not imply M1 or G0 is complete.

Local result on 26 November 2026: phase 1 command wiring and database checks complete. `make secrets` and `make db-up` exited 0; a fresh `abh-m1-check` Compose project initialized `abhedya_test` with nine tables, both audit protection triggers, and authenticated all three application roles, then was removed with its volume. Full-stack targets refused because the services are absent. `make openapi` still fails because the Python environment lacks `psycopg`; the package lock is incomplete. M1 remains partial.

Additional local database evidence: after PR #14 recorded the runner's direct packages, a second disposable Docker Desktop project (`abh-pg-suite`) ran `tests/unit/runner/live_pg_suite.py` against real PostgreSQL: 14 passed. The project and its volume were removed. This does not verify Docker sandbox calls or any Linux/runsc condition. Phase 2 still needs the missing API/build dependency entries and owner image definitions.

## Phase 2 — Service build and Compose wiring

Use the actual implementation handoffs and approved image/build definitions, runtime command, health response, and dependency pins for `api`, `runner`, `notary`, and `proxy`. As sole implementer, reconcile any stale or incomplete interface directly in its owning code and this Compose work, preserving contracts. Verify only the proxy publishes a host port and only runner mounts the Docker socket. Run a clean stack and service-level health checks on Docker Desktop as local integration evidence. Leave Linux isolation acceptance open.

Independent console slice expanded 26 November 2026 to cover O8 UI workflows: user/team administration, quotas, kill switch, audit filter/export/verify/checkpoint, tamper banner, activity SSE, and environment metric reads, all through implemented API routes. `npm run build` and `npm audit --audit-level=low` pass locally; `/login` returned HTTP 200. The API proxy returned connection refused because no API process is running, so no authenticated browser journey ran. This does not complete phase 2: Compose still contains only `db`; Python/image dependency decisions and the service interfaces remain unresolved. See the matching handoffs.

## Phase 3 — CI and fast checks

Wire a pinned CI workflow to executable Make targets. Include strict lint/type/unit checks, OpenAPI drift and placeholder checks when their dependencies and generated contract exist. Fail on missing prerequisites. Verify the workflow on a real PR.

## Phase 4 — Whole-stack integration

Run contract and safe end-to-end checks against the real local stack, repair cross-component integration defects directly, and record commit, commands, exit codes, and pending Linux host tests. Do not promote to `main` until the required gates pass.

### L1 backend dependency resolution progress · 27 November 2026

The installed Python environment lacks `psycopg`, `psycopg_pool`, and `argon2`, and the package/transitive approval question remains open. The candidate has been split into a runtime closure (27 packages, 510 artifact hashes; 10 direct plus 17 resolver-added) and a developer/test closure (44 packages, 867 artifact hashes; 15 direct plus 29 resolver-added). Both `uv pip install --dry-run --no-cache --require-hashes --system` commands exited 0 without installing anything. See `team/manas/work/API_DEPENDENCY_PROPOSAL.md`; neither candidate constitutes approval. The next steps are to review the lock and record the required dependency decision, install only the approved runtime/developer locks into isolated environments, run the API against the real Compose PostgreSQL, then exercise the disposable-database suite and real auth, RBAC, audit, stream and admin routes. This dependency-control path is independent of sandbox work.

### L1 local PostgreSQL credential handoff progress · 27 November 2026

`db/init/generate_secrets.py` now also generates one role-specific libpq password file for each service role (`abh_api`, `abh_runner`, `abh_notary`) from the existing generated passwords. It validates the existing password format, creates each file once, preserves matching files, and refuses a mismatch without printing credential values. `make secrets` and Python syntax compilation exited 0. Each generated file was exercised against the real local Compose PostgreSQL as its corresponding role; all three connections succeeded and returned only the expected role name. A Linux container inspection found that a Windows-host bind-mounted passfile appears mode `777`, which libpq rejects for password-file use. The successful probe therefore copied the mounted secret into private container tmpfs and set mode `600` before connecting. Compose still has no API service and does not yet consume these new files; API startup remains pending the formal dependency/image decisions and a real service-entrypoint design.
