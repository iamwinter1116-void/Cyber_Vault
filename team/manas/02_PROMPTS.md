# Manas · role D · maintainer, integration and release prompts M0–M6

Shared authority: `docs/TEAM_OWNERSHIP_AND_BRANCHING.md`, frozen contracts, `docs/05_OBJECTIVES.md` and `docs/06_VERIFICATION.md`.
These prompts own repository wiring and integration; they do not transfer feature-code ownership from Parth, Henil or Bhavya.

## M0 · Initialize repository and branches

Confirm the current directory has no `.git` and inspect the provided private GitHub repository before changing it.
Initialize Git on `main`, set `origin` to `https://github.com/iamwinter1116-void/Cyber_Vault`, commit the agreed
planning baseline, then create `integration`, `work/manas`, `work/parth`, `work/henil`, and `work/bhavya`.
Record the actual branch list and commit ID. `main` and `integration` are not direct-work branches.

Done when: Git shows all six local branches at the baseline; the working tree is clean; all six refs are pushed;
the handoff records the branch workflow; branch protection is verified or explicitly marked pending repository admin access.

## M1 · Repository scaffold and build interface

Create only the shared build files you own: `Makefile`, `compose.yaml`, `.github/` workflow, and `db/init/` application
wrapper. Use the canonical target names from `docs/04_CONTRACTS.md` section 11. Ask Henil, Parth and Bhavya for exact
service build/start/health commands before wiring them. Do not create fake service stubs outside an explicitly named G0 stub.

Done when: every target resolves to a documented command; the database applies the frozen schema; secrets are read from
ignored files; the proxy is the only published service; service blocks remain isolated and can be filled by their owners.

## M2 · CI and branch hygiene

Wire CI to the repository's real Makefile targets, starting with `make check-fast` and contract tests that can run without
the Docker stack. Do not mark skipped security tests as passing. Add checks for generated OpenAPI drift and placeholder
count only after the owning test/build code exists. Document that GitHub branch protection is a manual remote setting.

Done when: CI uses pinned/approved actions and dependencies, secrets are not printed, and failed required checks prevent
Manas from merging a PR to `integration`.

## M3 · Service integration contract review

For each owner PR, verify expected ports, health checks, environment variables, database role, volume mounts, restart
behavior and shutdown semantics against `docs/04_CONTRACTS.md` and the service owner's handoff. Keep API and runner
communication row-based through PostgreSQL; do not add HTTP/RPC between them. Keep Docker socket mounted only in runner.

Done when: each service owner signs off their own compose block; the whole stack reaches healthy state from a clean start;
stopping and restarting the runner converges from database desired state without duplicate containers.

## M4 · Gate captain and primary host operations

Schedule a single test window on the primary VM. Announce resets before running them. Bhavya calls out test IDs and
captures results; the feature owner fixes failures on their own branch. You record gate status and merge-ready evidence;
do not alter the contract or silence a failing test to make a gate green.

Done when: every gate is reported with command, exit code, output location, active host, commit ID, and remaining risks.

## M5 · Release and demo rehearsal

Only after integration has passed the G4 criteria, create the demo tag from `main`. Run the offline reset/rehearsal on the
primary VM, verify the backup handoff plan, retain evidence and a recovery snapshot. Do not claim a feature works unless
the evidence pack points to the successful test/output for the current main commit.

Done when: two offline rehearsals are recorded, evidence pack is committed, the VM image and secrets are backed up safely,
and the team can restore the platform without internet.

## M6 · PR merge and protected-branch operations

For each PR: verify author branch is `work/<owner>`, target is `integration`, path ownership is respected, review is
complete, test evidence matches the current head commit, and conflicts are resolved by file owner. Merge using a merge
commit or squash policy the team agrees on; keep attribution. Never merge a contributor branch directly into `main`.

For promotion: create a PR from `integration` to `main`; check gate status, evidence, open change requests and current
demo commit; merge it yourself only. When a remote is available, enforce the same rule in repository settings.
