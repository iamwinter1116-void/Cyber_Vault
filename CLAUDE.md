# ABHEDYA · secure, isolated, auditable cybersecurity testing platform

Four people, four owners, one shared repository. Roles: **A = Henil** (identity, API, quota, audit/notary),
**B = Parth** (isolation engine and workloads), **C = Bhavya** (console, independent verifier and tests),
**D = Manas** (maintainer, integration, release and primary host). `CLAUDE.local.md` identifies the person and
machine for a local agent session; if it is missing, stop and ask for it.

## Current state

Current work order: read `docs/16_BUILD_NOW_HOST_LATER.md` before choosing a task. Build real local slices now;
keep Linux-host acceptance pending until an actual host is available. No mock, simulated success, 501 route stub,
or placeholder gate pass. The current work-order decision suspends older VM-first and `STUB-G0` instructions.

This repository currently contains the instruction pack, frozen contracts, and planning documents. The product
implementation folders are not present yet. Do not claim an objective is implemented until the code and required
evidence are in the shared repository and the specified tests pass on the required host.

## Source of truth

- Frozen contracts: `contracts/schema.sql`, `contracts/rbac_matrix.yaml`, `contracts/audit_vectors.json`, and once
  generated `contracts/openapi.yaml`; see `docs/04_CONTRACTS.md`. Do not change without a CR approved by all four.
- `docs/03_CONTEXT.md`: threat model, decisions, dependency allowlist and explicit limits.
- `docs/05_OBJECTIVES.md` and `docs/06_VERIFICATION.md`: objective definition of done and exact test IDs.
- `docs/09_BUG_JOURNAL.md`: known risks and change-request format.
- `docs/TEAM_OWNERSHIP_AND_BRANCHING.md`: current four-person ownership, file boundaries, branch route and merge rule.
- `docs/16_BUILD_NOW_HOST_LATER.md`: current parallel work order and separation of local evidence from host acceptance.
- `docs/specs/`: detailed product/technical/backend/architecture specifications; frozen contracts take precedence.
- `team/<person>/`: each person's setup and prompts. Only `team/<person>/work/` is freely editable by that person.

## Directory ownership — edit only your own area

| Owner | Paths |
| --- | --- |
| A · Henil | `core/`, `services/api/`, `services/notary/`, their unit tests, `team/henil/work/` |
| B · Parth | `host/`, `services/runner/`, `sandbox/`, runner unit tests, `team/parth/work/` |
| C · Bhavya | `web/`, `tools/verify_audit.py`, `tests/contract/`, `tests/security/`, `tests/e2e/`, `evidence/`, `team/bhavya/work/` |
| D · Manas | `Makefile`, `compose.yaml`, `.github/`, `db/init/`, `team/manas/work/` |

Unit tests are owned by the component owner. Bhavya owns independent contract/security/e2e tests; feature owners must
not weaken, skip, delete, or mock them. Frozen shared contracts and documents are not personal work areas.

## Branch and merge rules

- Each person commits on `work/<name>`: `work/parth`, `work/henil`, `work/bhavya`, or `work/manas`.
- Every PR targets `integration`. No direct work or push to `integration` or `main`.
- **Manas alone merges** contributor PRs into `integration` and **Manas alone promotes** `integration` into `main`.
- Each PR states paths, objective/test IDs, commands, exit codes, actual output, and contract/security impact.
- If a PR touches another owner's path, the path owner must make the edit or explicitly pair and review it.
- Remote: `https://github.com/iamwinter1116-void/Cyber_Vault` (private). The connected account has write but not admin permission;
  verify branch protection and do not claim Manas-only merges are server-enforced until the owner/admin enables it.
- Git pushes require human approval under `.claude/settings.json`; do not push unless the user has authorized the push.

## Commands

- Fast check: `make check-fast` · one test: `uv run pytest path/to/test.py::test_name -q`
- Contract tests: `make test-contract` · security tests: `make test-security` (primary Ubuntu VM only)
- Stack lifecycle: `make up`, `make down`, `make demo-reset` (Manas only on primary host)
- Host checks: `make preflight` (Ubuntu VM with Docker Engine and `runsc`)

## Machine rules

- Any action that starts, inspects, or limits a sandbox runs only on the real Ubuntu demo VM with Docker Engine and
  gVisor. Never count WSL or Docker Desktop as security evidence.
- Manas operates the only active primary stack. Parth's VM is a cold backup and can run only after Manas announces a
  host handoff and stops the primary stack.
- Henil and Bhavya use WSL for code and light checks; stack-dependent tests run on the primary VM under Manas's coordination.
- GPU hardware is not required by mandatory objectives; do not pass GPUs or host devices into a sandbox.

## Rules without exceptions

1. No claim without the command, exit code, host/commit context and observed output.
2. External facts come from the installed tool's help/source and official version-specific documentation; otherwise say `UNVERIFIED:`.
3. Dependencies must be allowlisted, registry-checked and recorded in `evidence/VERSIONS.lock` before installation.
4. Never weaken, skip, delete or mock a contract, security or e2e test.
5. No silent fallback. Degraded isolation must be visible in the console/activity/ledger and in the handoff.
6. No placeholders in non-test code. Leave a feature out and report it rather than faking it.
7. Keep code small, typed and within budgets in `docs/05_OBJECTIVES.md`.
8. Stop for a CR before changing contracts, security tests, dependencies, sandbox capabilities/privilege/mounts/socket, or budgets.
9. Never commit credentials, private signing keys, demo passwords or generated `.env` files.
10. `I don't know` and `I could not verify this` are correct answers.

## End each session with a handoff

Append a factual note to your own `team/<name>/work/HANDOFFS.md` using `docs/07_ANTI_HALLUCINATION.md` section 5.
Include only commands run, their exit codes, outputs observed, files changed, and the next owner/action.
