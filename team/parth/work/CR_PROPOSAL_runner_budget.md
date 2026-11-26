# Change-request PROPOSAL · services/runner code budget (role B, Parth)

Status: PROPOSAL for the four-person CR process (CLAUDE.md rule 8: budgets change only by CR). NOT approved.
Requested by Manas (2026-11-26): "Do a reduction pass first ... If it cannot fit within 800, bring a change
request with the measured count and why the remaining lines are necessary."

## Counting rule used
Official since PR #22: `make budget-report` (db/init/report_budgets.py, also run by `make check-fast`) counts
lines covered by Python tokens, excluding comments, blank lines and docstrings. On integration 9c8675b it
prints `services/runner: 850/800 OVER`; its per-file counts equal the ones below. Physical lines are given
for information only.

## Reduction pass (done)
- Removed the `DockerWork` Protocol: one implementation (`DockerOps`), so an abstraction with one user
  (docs/05 style limit); reconcile.py now types against `DockerOps` imported for type checking only.
- Removed `Template.title/description/sizes`: validated but never read after parsing (validation kept).
- Searched for unused module-level names in services/runner against services/ and tests/: none.
Result: 857 -> 850 code lines (1191 -> 1185 physical). Behaviour unchanged: Manas reran 7f86459 on his host,
50 pure tests passed and the 14 real-PostgreSQL tests passed on a fresh disposable database (his handoff).

## Measured now (code / physical)
reconcile 131/171 · collect 125/166 · launch 119/175 · jobs 98/125 · objects 85/107 · templates 83/113 ·
metrics 50/80 · main 47/63 · storage 46/78 · state 38/58 · exec_policy 28/48 · total 850/1185.

## Why the remaining lines are necessary (by required behaviour, not by file)
- Sandbox profile and its refusals (docs/04 section 8; T-ISO-02): launch.py, every row of the profile table,
  digest-only images, no ABH_ variables, workspace never a host directory.
- Template allowlist (B1): templates.py, the exact keys, digests, network none for file-analysis, share sums.
- State machine with audit + activity in one short transaction after Docker work (R-10): reconcile.py, state.py.
- Cleanup Manas asked for: unlabelled managed objects, orphan V1 images, failed-env retry (objects.py, storage.py).
- Storage ladder V1/V2/V3 until preflight picks one (docs/08 section 4): storage.py and the storage reading.
- Collectors (B4, docs/08 section 5): stats, NOTIFY, thresholds, throttle, OOM, unexpected exit, reconnect.
- Exec jobs (B5, R-14): in-sandbox argv, bounded output, deadline, job.finished, restart recovery.
Further cuts would remove one of these behaviours or a refusal path; none is optional in docs/04-08.

## Request
Raise the services/runner ceiling from 800 to 1000 lines as counted by `make budget-report`, to hold the
current 850 plus B6 file analysis (analyzer run, rule-match parse, verdict, detonation, cleanup check).
The 150-line allowance for B6 is an ESTIMATE from B5's measured 133 lines for a comparable job path; my
earlier B5 estimate (60) was wrong, so the B6 slice will be measured and reported at its commit.
B7 (ai_scan) is not included: it is blocked by the O9 change request, which should carry its own budget.
Alternative for the team: keep 800 and drop or shrink B6 (docs/02 cut order already allows cutting detonation).
