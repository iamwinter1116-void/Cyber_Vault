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
