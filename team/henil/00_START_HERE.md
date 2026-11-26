# Henil · start here

**Your role:** A: login, sessions, authorization, API endpoints, team/host quota admission, audit append and notary.
You own backend service files; Manas owns Compose/build integration and the primary host.
Current order: read `docs/16_BUILD_NOW_HOST_LATER.md`. Start real A1 core/audit behavior locally against real
PostgreSQL, then implement API routes with real behavior. A0's former 501 route stubs are suspended.

## Your folder
| File | What it is | When |
| --- | --- | --- |
| `00_START_HERE.md` | This page | now |
| `01_DEVICE_SETUP.md` | WSL 2 for backend development and unit checks | before A0 |
| `02_PROMPTS.md` | Your eight agent tasks A0 to A7, in order | one fresh session per task |
| `03_MY_OBJECTIVES_AND_TESTS.md` | The objectives you lead and the tests that decide them | before A1 |
| `CLAUDE.local.md` | Tells your agent who it works for and which machine it is on | copy to the repository root once |
| `work/JOURNAL.md`, `work/HANDOFFS.md` | Your bug journal and hand-off notes | every session |

Shared files you must read once (about 60 minutes, with the other three): `docs/00_START_HERE.md`,
`docs/02_MASTER_PLAN.md`, `docs/03_CONTEXT.md`, all of `docs/04_CONTRACTS.md` (you implement most of it),
`contracts/rbac_matrix.yaml`, and `docs/09_BUG_JOURNAL.md` part 2.

## One-time agent setup (inside WSL)
1. Clone the repository into `~/abhedya` in the Linux file system.
2. `cp team/henil/CLAUDE.local.md ./CLAUDE.local.md` (it is git-ignored).
3. Guard-rail test: ask the agent to add a comment to `contracts/schema.sql` and to `team/henil/02_PROMPTS.md`.
   Both must be refused. Ask it to append a line to `team/henil/work/JOURNAL.md`. That must work.

## Work sequence
1. Confirm `work/henil` and exact backend path ownership; provide Manas actual service build/start/readiness commands.
2. Deliver A1 shared core audit/database interfaces first, then real A0 API shapes/routes as behavior is implemented.
3. Implement authentication, RBAC, endpoints, quota admission, event stream, audit append and notary in prompt order.
4. Run your unit tests locally; coordinate every full-stack or runner-dependent test with Manas on the primary VM.
5. Fix failures reported by Bhavya's contract/security tests without editing those tests.
6. Open PRs from `work/henil` to `integration`; Manas reviews and merges.

To reach G1 in time, A2 and the minimal routes listed for G1 in `02_PROMPTS.md` come before everything else.

## What only you must never forget
1. Every mutating route has one shape: `authorize("<rule>")`, one transaction, state change plus
   `audit.append` inside it. No role or team comparison in a route body.
2. Never read `tools/verify_audit.py`. Bhavya never reads your ledger code. Two independent implementations
   agreeing on the vectors is one of the team's strongest proofs.
3. You never call Docker. Parth's runner never accepts network requests. You meet in database rows.
4. The ledger lock is held only for SQL. Anything slow inside the audit transaction stalls every writer (R-10).
5. WSL is for your code only. A full-stack check that was not run on the demo VM is not a check.

## Ritual for every task
new session → **P-GROUND** → the task from `02_PROMPTS.md` → read the plan → let it work → **P-CLAIMS** →
**P-REDTEAM** for A2 to A6 → **P-REVIEW** → **P-HANDOFF** → the two-minute human checks → merge when
   `make check-fast` is green; open a PR to `integration` for Manas to merge.
