# Local instructions · Manas · role D · maintainer and primary host

Copy this file to the repository root locally as `CLAUDE.local.md`; it is git-ignored.

- You work for Manas, the maintainer. Your prompts are `team/manas/02_PROMPTS.md` M0–M6.
- Direct edits are limited to `Makefile`, `compose.yaml`, `.github/`, `db/init/`, and `team/manas/`.
- Shared docs/specs remain read-only except through the agreed change-request workflow.
- Do not edit `core/`, `services/api/`, `services/notary/`, `services/runner/`, `host/`, `sandbox/`, `web/`, `tools/`,
  or another person's tests. Ask the owner to make a requested feature edit.
- Frozen contracts are in `contracts/`; a change requires an agreed CR from Parth, Henil, Bhavya and you.
- Your laptop is the primary host: Ryzen 9 9955HX, RTX 5070 Ti 12 GB, 32 GB RAM. Verify OS, CPU count, free disk,
  virtualization and the actual VM before making host claims. GPU is not required for mandatory objectives.
- Only you run `make up`, `make down`, and `make demo-reset` on the primary host. Announce resets to the team first.
- Only you merge contributor branches into `integration`; only you merge `integration` into `main`.
- Contributors use `work/<name>` branches and PR into `integration`; no direct commits to shared branches.
- Remote protection is not active until a remote exists and settings are configured. Never claim it is enforced before then.
- Journal and handoff files are only `team/manas/work/JOURNAL.md` and `team/manas/work/HANDOFFS.md`.
- Do not report implementation or test success without the exact command, exit code, output, host and commit.
