# Team folders and ownership

Four named contributors build ABHEDYA. The current ownership agreement is [docs/TEAM_OWNERSHIP_AND_BRANCHING.md](../docs/TEAM_OWNERSHIP_AND_BRANCHING.md).

| Folder | Person | Role | Device | Exact implementation ownership |
| --- | --- | --- | --- | --- |
| `manas/` | Manas | D · maintainer, integration/release owner | Ryzen 9 9955HX, RTX 5070 Ti 12 GB, 32 GB RAM; primary Ubuntu VM host | `Makefile`, `compose.yaml`, `.github/`, `db/init/`, shared integration/release workflow and `team/manas/` |
| `parth/` | Parth | B · isolation and workloads | i7 HX class CPU, RTX 5050 8 GB, 24 GB RAM | `host/`, `services/runner/`, `sandbox/`, runner unit tests, `team/parth/` |
| `henil/` | Henil | A · identity, API and audit | Ryzen 7 260, RTX 5050 8 GB, 16 GB RAM | `core/abh_core/`, `services/api/`, `services/notary/`, their unit tests, `team/henil/` |
| `bhavya/` | Bhavya | C · console, verifier and proof | Ryzen 7, RTX 3050, 16 GB RAM | `web/`, `tools/verify_audit.py`, `tests/contract/`, `tests/security/`, `tests/e2e/`, `evidence/`, `team/bhavya/` |

## Folder contents

Each person's folder has:

| File | Purpose |
| --- | --- |
| `00_START_HERE.md` | Role, exact file ownership, handoffs and first steps |
| `01_DEVICE_SETUP.md` | Approved use of that person's machine |
| `02_PROMPTS.md` | Ordered task prompts owned by that person |
| `03_MY_OBJECTIVES_AND_TESTS.md` | Objective slice and proof expected from the owner |
| `CLAUDE.local.md` | Machine/person-specific local coding-agent instructions; copy to repo root locally and keep git-ignored |
| `work/JOURNAL.md` | Personal factual debugging notes |
| `work/HANDOFFS.md` | Personal session handoffs with commands/output actually observed |

## Boundaries

- One person directly edits the implementation paths listed in the ownership agreement.
- Other contributors review through pull requests and do not make silent cross-owner edits.
- Frozen contracts in `contracts/` require a change request approved by all four contributors.
- Every contributor works on their own `work/<name>` branch; all PRs target `integration`.
- Manas alone merges into `integration` and alone promotes `integration` into `main`.
- Only Manas operates the primary Docker stack. Parth may operate the backup VM only after an explicit host handoff.
- Each person edits only their own `team/<name>/work/` files.
