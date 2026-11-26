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
Change docs/05_OBJECTIVES.md line 33 from "| `services/runner` | 800 |" to
"| `services/runner` | 1000 |". The 150 lines above today's count are an ESTIMATE for B6 (measured and
reported at the B6 commit). B6 has two parts that the documents treat differently:
(a) Static file triage - MANDATORY. O9 (docs/05): "`file-analysis`: upload a file, get static triage";
    docs/02 section 5 cut 5 keeps it ("file detonation (keep static triage)"). Scope from docs/08 section 6:
    `analyzer` (network none, sample mounted read-only): SHA-256, type identification, `yr scan` over the
    baked rule directory; verdict rule of docs/04 section 5; result shape of docs/04 section 5; destroy the
    environment. T-WL-02: test file `malicious` with the rule name, text file `clean`, sample `<sha256>`
    mode 0400, no labelled container/network/volume left.
(b) Detonation - OPTIONAL in two separate senses. Per request: O9 says "an optional no-network detonation
    report", R20 takes `detonate` true or false, and docs/04 section 8 starts `detonator` (network none)
    only "when requested". Per build: docs/02 section 5 cut 5 lets the team cut file detonation when a gate
    slips (a team decision; docs/16 says the old dates are not live deadlines). Scope from docs/08 section
    6: sample copied to `/workspace`, 120 s deadline, exit code, duration, last 4 KiB, timeout flag; a
    timed-out detonation gives `suspicious`.
If (b) is cut: T-WL-02's detonation case and T-ISO-04's detonator subcheck are recorded out of scope and
detonation is not claimed as tested; how a request with `detonate: true` is then answered (R20 still
accepts the flag; the result's `detonation` is null) needs its own decision, because a silent fallback is
not allowed (CLAUDE.md rule 5). The split of the 150 lines between (a) and (b) is not estimated.
Known B6 work in existing code: templates.py requires both containers and DockerOps.provision starts every
container of a template, so today `detonator` would start even when not requested (docs/04 section 8).
B7 (ai_scan) is excluded and needs its own budget in the O9 change request.
Alternative: none that fits 800. The runner is already at 850 before any B6 line, and part (a) is
mandatory; cutting part (b) lowers B6's size, not the total below 800.
