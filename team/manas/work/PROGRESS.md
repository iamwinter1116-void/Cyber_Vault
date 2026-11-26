# ABHEDYA progress scorecard · 26 November 2026

Snapshot: `integration` at `20324e0`. `main` remains at `6dc40c8`.

## What the percentages mean

- **Integrated implementation coverage: 16/33 = 48.5%.** The denominator is the 33 named owner tasks in
  `team/{henil,parth,bhavya,manas}/02_PROMPTS.md`: A0–A7 (8), B0–B8 (9), C0–C8 (9), M0–M6 (7).
  A task gets one point only when a substantial part of its primary local deliverable is present in
  `integration`. A partial scaffold, a test collection without the feature, or a handoff alone gets zero.
  This measures integrated code/setup coverage; it does **not** say the task meets its done-when criteria.
- **Accepted mandatory objectives: 0/9 = 0%.** Per `docs/05_OBJECTIVES.md`, each objective needs its named
  tests to pass on the demo host with evidence. None has that evidence.
- **Passed gates: 0/5 = 0%.** G0–G4 each has unmet exit criteria in `docs/02_MASTER_PLAN.md`.

## Integrated implementation coverage tally

| Owner | Counted tasks | Not counted yet | Points |
| --- | --- | --- | ---: |
| Henil A0–A7 | A0 schemas, A1 core, A2 auth, A3 authz, A4 env/jobs/quotas, A5 monitoring/admin API, A6 notary/audit routes | A7 hardening remains incomplete: API budget and live checks | 7/8 |
| Parth B0–B8 | B0 scripts, B1 runner skeleton, B3 storage/reaper/limits code, B4 collector code, B5 exec jobs code | B2 probes/images, B6 file analysis, B7 AI target, B8 host/degraded verification | 5/9 |
| Bhavya C0–C8 | C0 contract harness, C1 verifier, C2 security test suite code | C3–C6 console, C7 scanners/evidence pack, C8 completed E2E/rehearsal | 3/9 |
| Manas M0–M6 | M0 repository and branch setup | M1 full build scaffold, M2 CI, M3 whole-stack integration, M4 host gates, M5 release rehearsal, M6 protected promotion | 1/7 |
| **Total** | | | **16/33** |

Counted tasks are **not** necessarily finished. For example B0 scripts are merged but `make preflight` has
only refused Windows at check 1, and A2 auth code is merged but its corrected denied-login path has not
passed a new real PostgreSQL test.

## Evidence and immediate gaps

- PRs #1–#7 and #9–#12 merged into `integration`; superseded conflicting PR #8 was closed. Parth B5's 50 pure runner tests independently passed on Manas's Windows host. His 14 real PostgreSQL tests and
  all Docker/runsc tests remain unrun. The runner is documented at 857/800 non-test code lines.
- Henil's API/notary code through `bcaa3bb` and his replacement `live_pg_suite.py` are merged. The original
  `test_pg_routes.py` was excluded because it could disable audit triggers and truncate a database without a
  disposable-database guard. The replacement requires explicit opt-in and separate owner/API/notary role DSNs;
  its real PostgreSQL run remains pending.
- Bhavya's verifier-side vector selection independently passed 22 tests; 7 core-side tests were not run in
  that invocation. Her live contract/security/e2e suites remain pending. T-ISO-03 currently permits an
  unsent ICMP probe while reporting the test green, so it cannot yet establish the full T-ISO-03 condition.
- `web/` and `sandbox/` have no implementation in `integration`. Compose currently runs only PostgreSQL;
  no API, runner, notary or proxy Compose block or CI workflow exists. The Make interface now refuses unavailable
  services and tests explicitly; it has not passed `make check-fast` or full-stack checks.
- O9's original model-stub design conflicts with Manas's no-stub instruction. A four-person change request
  for a real offline target is still required.

Update this tally only after inspecting the new `integration` commit and the owner handoff. Record local
implementation separately from accepted objectives and gates; do not infer a pass from source code alone.
