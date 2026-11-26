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

Independent console slice started 26 November 2026: `web/` now has a real React/Vite UI for implemented API routes, cookie-backed session restoration, authenticated activity SSE, and live API overview fields. `npm run build` and `npm audit --audit-level=low` pass locally. This does not complete phase 2: Compose still contains only `db`, no browser-to-API journey was run, and Python/image dependency decisions remain unresolved. See the matching handoff.

## Phase 3 — CI and fast checks

Wire a pinned CI workflow to executable Make targets. Include strict lint/type/unit checks, OpenAPI drift and placeholder checks when their dependencies and generated contract exist. Fail on missing prerequisites. Verify the workflow on a real PR.

## Phase 4 — Whole-stack integration

Run contract and safe end-to-end checks against the real local stack, repair cross-component integration defects directly, and record commit, commands, exit codes, and pending Linux host tests. Do not promote to `main` until the required gates pass.
