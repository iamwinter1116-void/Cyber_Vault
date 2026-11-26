# Manas · role D · maintainer, integration and release owner

You are Manas, the repository maintainer and the only person who merges contributor work into `integration` or `main`.
Read `docs/16_BUILD_NOW_HOST_LATER.md` first. Build actual repository wiring from owner-provided interfaces now;
host setup and full-stack acceptance remain open until a real Linux host is available.
The build is split so you do not implement Parth's runner, Henil's API, or Bhavya's frontend/verifier/tests.
You own the build wiring and ensure those separately owned pieces become one runnable, reviewable system.

## Your folder and exact ownership

| File | Use |
| --- | --- |
| `00_START_HERE.md` | This operating guide |
| `01_DEVICE_SETUP.md` | Prepare the primary Ubuntu demo VM on your laptop |
| `02_PROMPTS.md` | Your M0–M6 maintainer tasks, in order |
| `03_MY_OBJECTIVES_AND_TESTS.md` | Integration objectives and release gate evidence |
| `CLAUDE.local.md` | Copy locally to repository root; it is git-ignored |
| `work/JOURNAL.md` | Your own factual debugging notes |
| `work/HANDOFFS.md` | Append one evidence-based handoff per work session |

You directly edit only `Makefile`, `compose.yaml`, `.github/`, `db/init/`, the ownership/branching document,
`team/manas/`, and release integration metadata agreed by the team. Feature implementation stays with its owner.
Do not edit contracts or another person's code to make integration appear green.

## Team and handoff map

| Owner | Owns | You receive |
| --- | --- | --- |
| Parth | Host setup, runner, sandbox profile, workloads, limits and collectors | Image/service requirements, required environment variables, ports, health checks and T-ISO/T-RES/T-WL evidence |
| Henil | Core library, API, authorization, quotas, audit and notary | API start command, DB role use, schema application order, migrations/init needs, readiness and audit behavior |
| Bhavya | Console, independent verifier, contract/security/e2e tests and evidence | Web build/start command, verifier CLI contract, test commands, fixture needs, evidence paths and expected browser routes |
| Manas | Build wiring, CI, primary VM, gates, PR review and release | Integrate the three owned contributions and report only evidence actually produced |

If an interface is unclear, ask its owner to specify the exact file, command, payload, state transition and test ID in a
small PR or issue. Do not invent a new port, variable, endpoint, dependency, database table, or permission.

## Branch workflow

1. Work only on `work/manas` for your own branch changes.
2. Contributors push only to `work/<their-name>` and open PRs into `integration`.
3. You review the changed paths and evidence; only you merge approved PRs into `integration`.
4. Every service owner reviews wiring that touches their service block. The owner remains responsible for fixing their code.
5. You promote tested `integration` to `main` only after the gate checklist passes.
6. Do not create a direct commit on `main` or `integration`; do not accept a direct push from another person.
7. Verify branch protection on the provided private GitHub repository. The connected account has write but not admin
   permission, so enforcement may require the repository owner/admin.

## First session checklist

- Read `docs/TEAM_OWNERSHIP_AND_BRANCHING.md`, `docs/02_MASTER_PLAN.md`, `docs/04_CONTRACTS.md`,
  `docs/05_OBJECTIVES.md` and `docs/06_VERIFICATION.md`.
- Check local Git state and confirm the provided private remote is empty before the initial push.
- Initialize `main`, commit the agreed planning baseline, set `origin`, then create and push `integration` and four `work/*` branches.
- Schedule the primary Linux host from `01_DEVICE_SETUP.md` later; keep host-dependent gate items open until then.
- Ask each owner to confirm their path boundary and first PR deliverable before implementation begins.
- Save branch names, host IP/URL and any secrets only in approved local config; never commit credentials.

## What counts as integration-ready

- The PR is limited to the author's owned paths or a pre-approved shared-file change.
- The required test IDs are named and test output, exit code and environment are recorded.
- `make check-fast` passes once the scaffold exists; stack tests run on the primary VM.
- Compose publishes only the proxy and keeps API, database, runner and notary on internal networks.
- Secrets are mounted from ignored files; no key or demo password appears in Git history.
- All components have health/readiness checks and deterministic startup/cleanup behavior.
- The integration branch can be reset and demoed without internet after dependencies are prepared.
- PR review confirms no contract drift, unapproved dependency, weakened test, silent degraded mode or owner-boundary violation.

## Your machine

Your laptop is the primary host because it has the most RAM: Ryzen 9 9955HX, RTX 5070 Ti 12 GB, 32 GB RAM.
The GPU is not a mandatory project dependency. Keep the Ubuntu VM at the documented 6 vCPU/12 GB baseline until
preflight evidence and a team decision justify a change. Manas alone starts, stops, resets and promotes the primary stack.
