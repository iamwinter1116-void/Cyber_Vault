# Bhavya · role C · console, independent verifier and proof · agent tasks C0 to C8

**You own:** `web/`, `tools/verify_audit.py`, `tests/contract/`, `tests/security/`, `tests/e2e/`, and `evidence/`.
**You lead:** O8 (admin dashboard), O7 verifier side, the display half of O4, and independent test proof.
Manas owns the Makefile, Compose, CI and integration/release gates.
**You never touch:** `contracts/`, `docs/`, `core/`, `services/`, `sandbox/`, `host/`, other people's folders under `team/`.
**Where you run:** edit on your Ryzen 7 / RTX 3050 / 16 GB laptop in WSL 2; run stack-dependent tests on Manas's primary VM over SSH when he opens a test window. In this file A is Henil, B is Parth, and D is Manas.
**You are the team's sceptic.** Your tests are written from the contracts, not from A's and B's code. Your
verifier never imports their code. When your test and their code disagree, the contract decides.

## What others need from you, and when

| By | Deliver | Who waits |
| --- | --- | --- |
| T0 + 1 h | Contract test harness and known-answer test collection plan; Manas supplies the repo/build scaffold | A, B, D |
| G0 | `tests/contract/test_audit_vectors.py` and `test_rbac_matrix.py` runnable (failing is fine) | A |
| T0 + 6 h | `tools/verify_audit.py` passing all vectors | A (notary end-to-end check) |
| T0 + 12 h | `tests/security/` complete, red where features are missing | A, B (they build until green) |
| G2 | Console pages for every objective | everyone |
| G3, G4 | Scans, evidence pack, demo rehearsal, outsider session | everyone |

## How to run each prompt
Same ritual: new session → **P-GROUND** → task prompt → **P-CLAIMS** → **P-REVIEW** → **P-HANDOFF** →
two-minute human checks → merge. For C1 and C2 add one instruction at the top of the session:
`Do not open any file under core/ or services/. Work only from docs/04_CONTRACTS.md and contracts/.`

---

### C0 · Contract test harness (about 60 minutes, after Manas M1 scaffold)
```
Task C0. Read `docs/04_CONTRACTS.md` sections 1 to 4, `contracts/rbac_matrix.yaml`, `contracts/audit_vectors.json`,
and `docs/06_VERIFICATION.md` sections 1 to 3. Work after Manas has created the scaffold and shared build files.
Write only `tests/contract/conftest.py`, `tests/contract/test_audit_vectors.py`, and
`tests/contract/test_rbac_matrix.py`. Use a stack URL from the environment, fixture users named by the verification
plan, and a database connection only where the test requires an assertion. Generate RBAC cases directly from the
matrix; do not duplicate its allow map in test code. Parameterize known-answer checks over independent `core` and
`verifier` implementations, importing each lazily so a missing implementation produces a clear failure rather
than hiding the other side. Do not write the Makefile, pyproject, Compose, CI, or service stubs; those are Manas's
owned paths. Do not weaken or skip a failing contract assertion.
Done when: `pytest tests/contract --collect-only -q` lists the generated cases; the output and count are recorded;
test ownership is limited to Bhavya paths; Manas merges your PR into `integration` after review.
```

### C1 · Independent verifier (about 2 hours) · tests T-KAT-01 to 04 (verifier side), T-AUD-05
```
Task C1. Do not open any file under core/ or services/. Read docs/04_CONTRACTS.md section 7 completely and
contracts/audit_vectors.json. Read risks R-08 and R-17.
Write tools/verify_audit.py: one file, at most 180 lines, standard library plus the allowlisted cryptography
package for Ed25519 only. Command line and exit codes exactly as in section 7.8. Implement the six steps in
the stated order; the first failure wins. Reject input records that contain a float, null, or unknown keys
with exit code 3.
Write the tests first: canonical bytes, hashes, roots for sizes 0 to 5, both signatures, and the ten
tamper_cases (implement the six mutation operations named in the vectors in the test helper, not in the tool).
Then add the property-based test T-AUD-05: generate random valid ledgers with random checkpoints signed by a
generated key, apply one random mutation, assert the verdict is never OK; assert OK for unmutated ledgers.
Done when: `pytest tests/contract/test_audit_vectors.py -k verifier -q` and the property test pass with output
shown, including the number of generated examples; `python tools/verify_audit.py --help` prints usage.
```

### C2 · Security test suite (about 3 hours, start as soon as C1 is merged) · tests of `06` sections 4 to 7
```
Task C2. Do not open files under core/ or services/. Read docs/06_VERIFICATION.md sections 4, 5, 6, 7 and
docs/04_CONTRACTS.md sections 6, 7, 8. Member B provides probe scripts in sandbox/probes/ callable through the
exec API; code against the names listed in team/parth/02_PROMPTS.md task B2.
Write tests/security with one test per ID: T-ISO-01 to 07, T-STATIC-01, T-RES-01 to 06, T-AUD-01 to 04 and
06 to 08, T-MON-01 to 04. Each test states its ID in its name and asserts exactly the pass condition written
in the verification plan. Tests drive the system only through the public API, the Docker CLI for inspection,
and a superuser database connection for the tamper drills.
Write the tamper tool behind `make tamper-drill CASE=<name>`: it applies one of the vector tamper operations
to the live ledger as superuser (disabling the append-only triggers inside its transaction and re-enabling
them), including the smart attacker who recomputes every later hash. Print a loud warning banner; refuse to
run unless ABH_ALLOW_TAMPER_DRILL=1.
Add to T-ISO-06 one assertion taken from the fixtures of docs/06: no sandbox can read
/var/lib/abhedya/flag_host, and analyst.bravo cannot read the file that holds flag_env.
Tests must fail, not skip, when a feature is missing. No mocks. No retries. Timing assertions use the latency
targets in the contracts.
Done when: `pytest tests/security --collect-only -q` lists every ID above; run against the current stack, the
report shows which pass and which fail, and every failure message names the unmet pass condition.
```

### C3 · Console shell, login, environments (about 3 hours) · tests T-E2E-01
```
Task C3. Read docs/04_CONTRACTS.md sections 2, 3, 4, 6 and docs/08 section 10. Use contracts/openapi.yaml as the
only source for request and response types (generate the TypeScript types from it; do not hand-write them).
Build: a fetch wrapper (credentials included, X-CSRF-Token from memory, error envelope mapped to typed
errors, 401 redirects to login); a useStream hook around EventSource that updates the query cache from
activity, metric, audit and heartbeat events and shows a visible "live / reconnecting" indicator; the layout
with navigation by role; Login; Environments (table with state, isolation tier badge, live CPU, memory and
storage against limits, create dialog with template and size, stop, destroy with confirmation); Environment
detail (charts for the last 15 minutes, command box that submits R17 and shows the job result, event list).
Rules: no token or user data in localStorage or sessionStorage; never insert untrusted text as HTML; every
mutating button is disabled while its request is in flight; every page has loading, empty and error states.
Budget for this task: 800 lines.
Done when: against the running stack, the journey of T-E2E-01 works in the browser, shown by a recorded
Playwright run or screenshots at each step; `make check-fast` exits 0.
```

### C4 · Audit and activity pages (about 2 hours) · tests T-E2E-03, T-E2E-04
```
Task C4. Read docs/04_CONTRACTS.md sections 6 and 7.5 to 7.8, rules R23 to R28.
Build: Activity (live feed, severity filter, critical alerts pinned); Audit (table with filters for action,
actor, outcome and sequence range; record detail drawer showing all 15 fields and the hash; Export buttons
for records and checkpoints; Verify button showing the VerifyResult; checkpoint list with tree size, root and
time; ledger status badge). A critical alert.tamper_detected event must turn a full-width banner red on every
page without reload, naming the verdict and position.
Done when: T-E2E-03 passes; during `make tamper-drill CASE=edit_field_no_rehash` the banner appears within 30
seconds (T-E2E-04), shown with timestamps.
```

### C5 · Admin pages (about 2 hours) · test T-E2E-02
```
Task C5. Read rules R04 to R09, R29, R30 and the Overview shape.
Build: Overview (users, teams, environments by state, host allocation bars from Overview.host, alerts in the
last hour, isolation badge that turns red when degraded, ledger status with the last checkpoint); Users
(list, create, disable, role change, with the LAST_ADMIN and SELF_ROLE_CHANGE errors shown in plain words);
Teams (list with usage against each quota, quota edit); Kill switch (per team and global, with typed
confirmation).
Done when: T-E2E-02 passes and each action's audit record is visible on the Audit page.
```

### C6 · File and AI pages (about 90 minutes) · supports T-WL-02, T-WL-03
```
Task C6. Read docs/04_CONTRACTS.md section 5 and rules R18 to R21.
Build: Files (upload with size check before sending, detonate toggle, job list, report view with verdict
badge, hash, type, rule matches, detonation result); AI red team (target and probe set choice, job list,
result table by probe with attempts, failures and OWASP LLM risk ID, overall failure rate).
State the limits on the page in one line each: dynamic analysis covers Linux executables and scripts only
and runs for at most 120 seconds, so "clean" does not mean safe (limit L8); the AI target is a built-in stub
service and results are scanner-flagged, not verified by a person (limit L9). Show each environment's
isolation profile (the bracketed prefix of the template description, decision D12) in the badge tooltip.
Done when: both journeys work in the browser against the running stack, shown by screenshots.
```

### C7 · Scanners and evidence pack (about 2 hours, at G3) · X-01 to X-07
```
Task C7. Read docs/06_VERIFICATION.md section 9 and docs/13_DEMO_AND_EVIDENCE.md section 3.
Implement `make scan`: run each scanner from its official container image or release, confirming its command
syntax from its own help output, and write results to evidence/scans/. If a scanner cannot be run, record
"not run" with the reason; never fabricate a result file. Implement `make evidence`: collect test reports,
scan results, preflight, VERSIONS.lock, the witness file, an export of the ledger with a verifier run,
docs/09_BUG_JOURNAL.md followed by the three team/*/work/JOURNAL.md files as evidence/bug-journal.md,
docs/14_PRIOR_ART.md as evidence/prior-art.md, and
generate evidence/INDEX.md that lists each objective O1 to O9 with its test IDs, pass or fail from the JUnit
files, and the evidence path.
Done when: `make scan` and `make evidence` complete; INDEX.md is generated from the reports, not typed.
```

### C8 · End-to-end run, outsider session, rehearsal (gate G4)
```
Task C8. Read docs/13_DEMO_AND_EVIDENCE.md and docs/08 section 12. Write tests/e2e as one Playwright journey
per demo step. Implement `make demo-reset`, including the two planted flags of the fixtures in docs/06
(flag_env through the public API as analyst.alpha; flag_host on the host, root-owned, mode 0400; both copied
to secrets/flags.txt). Then help me rehearse: run the reset, run the journey with the machine's internet
disconnected, time each step, and list anything that depended on the network or took longer than its slot.
Done when: two consecutive offline runs pass; the timing table is pasted.
```
