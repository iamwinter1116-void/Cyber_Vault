# Change-request entry for docs/09_BUG_JOURNAL.md Part 4 (ready to paste by a human)

```
### CR-<n> · docs/05_OBJECTIVES.md "Code budget" (services/api)   2026-11-26 23:08 IST · raised by A
Problem: `db/init/report_budgets.py` (`make budget-report`) measures `services/api` at 2000/1100 OVER.
  All 31 contract routes (`R01`–`R31`), 22 strict Pydantic models (`extra="forbid"`), Argon2id/CSPRNG/lockout
  auth, RBAC matrix enforcement, quota admission (`BR3`), 10 MiB quarantine streaming, SSE `LISTEN/NOTIFY`
  hub, live SQL overview, and `R28` ledger verification are implemented with `mypy --strict` and zero
  placeholders; every file is <= 214 code lines (`team/henil/work/CR_PROPOSAL_api_budget.md`).
Proposed change: in `docs/05_OBJECTIVES.md` line 34, change "| `services/api` | 1100 |" to
  "| `services/api` | 2100 |".
  Alternative: none without dropping required `R01`–`R31` routes, explicit schemas, or strict typing.
Affected: A (`services/api`), D (`db/init/report_budgets.py` limit). Tests: T-AUTH-01..05, T-RBAC-01..12, T-API-01.
Agreed by: A yes  B __  C __  D __
Applied in commit: <id>
```
