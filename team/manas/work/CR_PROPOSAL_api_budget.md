# Change request proposal · API code budget

**Status: proposal only; no budget change is approved or applied.** This file is a decision-ready draft for `docs/09_BUG_JOURNAL.md` and must not be read as authorization to exceed the frozen budget.

## Problem and evidence

The frozen `docs/05_OBJECTIVES.md` budget is 1,100 code lines for `services/api`. The repository's official counter currently reports 2,000, an overage of 900. `python db/init/report_budgets.py` on 27 November 2026 exited 1 and printed `services/api: 2000/1100 OVER`.

The official counter's per-file values are:

| File | Count |
| --- | ---: |
| `authz.py` | 102 |
| `deps.py` | 97 |
| `main.py` | 48 |
| `middleware.py` | 56 |
| `openapi_export.py` | 9 |
| `quota.py` | 110 |
| `routes/admin.py` | 100 |
| `routes/audit.py` | 199 |
| `routes/auth.py` | 167 |
| `routes/envs.py` | 211 |
| `routes/health.py` | 18 |
| `routes/jobs.py` | 184 |
| `routes/monitor.py` | 214 |
| `routes/teams.py` | 123 |
| `routes/templates.py` | 32 |
| `routes/users.py` | 138 |
| `schemas.py` | 162 |
| `security.py` | 30 |
| **Total** | **2,000** |

Henil's A7 handoff says all 31 routes have startup matrix parity and that the implementation has strict Pydantic request/output shapes, Argon2id/session behavior, RBAC, quota admission, file upload, SSE, audit and ledger verification. Its unit, ruff, and mypy results were run in Henil's WSL environment and are recorded in `team/henil/work/HANDOFFS.md`; they were not re-run in this Manas session. Manas ran `python -m compileall -q core services tools` on this checkout and it exited 0, which proves syntax compilation only.

Henil's `team/henil/work/JOURNAL.md` says further compression below 1,100 would require dropping explicit field typing or merging unrelated route modules. This CR proposes a bounded ceiling increase; it does not authorize new features or remove required checks.

## Proposed change

In `docs/05_OBJECTIVES.md` line 34, change the `services/api` code budget from `1100` to `2100`. The measured implementation is 2,000, leaving 100 lines (5%) of implementation/defect-fix headroom. Keep the same counting rule and all other budgets unchanged.

## Affected work and proof

- Affected component: `services/api` and `make check-fast` budget report.
- No contract, route, dependency, image, security behavior, or test condition changes.
- After approval and application, `python db/init/report_budgets.py` must report `services/api: 2000/2100 OK`; the overall report may still fail on the runner overage and missing `sandbox/`.
- API unit, contract, security and end-to-end checks remain independently required; the ceiling change does not mark them passed.

## Decision

Please record yes/no for all four members in the official `docs/09_BUG_JOURNAL.md` change-request entry. Until then, keep this proposal out of the official budget and do not describe 2,000 lines as compliant.
