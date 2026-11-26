# Henil · role A · identity, API and ledger · agent tasks A0 to A7

**You own:** `core/abh_core/`, `services/api/`, `services/notary/`, and their unit tests.
**You lead:** O2 (login and RBAC), O6 (central audit), O7 ledger side; you supply the API half of O3, O4, O5, O8.
**You never touch:** `contracts/`, `docs/`, `services/runner/`, `sandbox/`, `web/`, `tools/`, `tests/contract`, `tests/security`, other people's folders under `team/`.
**Where you run:** WSL 2 on your Legion for code, unit tests and your own PostgreSQL (`01_DEVICE_SETUP.md`). Anything that needs the runner or the full stack runs on the demo VM over SSH. In this file B is Parth and C is Bhavya.
**Current sequence:** `docs/16_BUILD_NOW_HOST_LATER.md` puts real A1 core/audit work before A0 API routes.
Do not write or register 501/`STUB-G0` routes. A0 is complete only when its routes have real behavior and tests.

## What others need from you, and when

| By | Deliver | Who waits |
| --- | --- | --- |
| Local first | A1 core audit and database interface, then real API routes in contract order; OpenAPI only from implemented routes | B, C, D |
| T0 + 4 h | `abh_core.audit` (`canonical`, `record_hash`, `merkle_root`, `append`) and `abh_core.settings`, `abh_core.db` | B (runner audits through it) |
| G1 | Login, `GET /auth/me`, `POST /envs`, `GET /envs`, `GET /audit`, `GET /audit/export`, notary producing checkpoints | B, C |
| G2 | Every rule in the matrix implemented | everyone |

## How to run each prompt (same ritual every time)
1. New agent session in the repository root.
2. Paste **P-GROUND** from `07_ANTI_HALLUCINATION.md`, then the task prompt below. Read the agent's plan
   before letting it write. Reject plans that exceed the stated line budget or touch other directories.
3. When it reports done, paste **P-CLAIMS**. For A2 to A6 also paste **P-REDTEAM**.
4. Paste **P-REVIEW**, fix real gaps, then **P-HANDOFF**. Run the two-minute human checks. Merge.

---

### A0 · Schemas and real route implementation (after A1; no 501 placeholders)
```
Task A0. Read docs/04_CONTRACTS.md sections 2, 3, 4 and contracts/rbac_matrix.yaml.
Create `services/api/schemas.py` with contract request and response models (unknown fields forbidden on input;
explicit output fields). Add a route only when its authorization, transaction, response and error behavior are real
and tested. Start with A2 authentication and the G1 paths; continue until all 31 matrix rules are implemented.
Generate `contracts/openapi.yaml` from the implemented FastAPI app, never by hand or from placeholder routes.
The frozen matrix remains the target; report each missing rule as pending until the full set is implemented.
Dependencies must be allowlisted, registry-checked and recorded before installation.
Done when all 31 routes have real behavior, their contract tests pass, the generated operation set equals the
matrix, and `make check-fast` exits 0. Until then, hand off each real route slice as incomplete A0.
```

### A1 · Core library and audit append (about 90 minutes) · tests T-KAT-01 to 03 (core side), unit tests
```
Task A1. Read docs/04_CONTRACTS.md sections 7.1 to 7.4, 9, 10, contracts/schema.sql (audit_log), and
contracts/audit_vectors.json. Read risks R-08, R-09, R-10, R-17 in docs/09_BUG_JOURNAL.md.
Build core/abh_core: settings.py (typed settings for the variables in section 9), db.py (connection pool
factory, no ORM), audit.py with exactly the public functions of section 10.
append() must: run inside the caller's transaction; take pg_advisory_xact_lock(4242001); read the tail; take
ts from the database clock formatted as the schema's check constraint demands; validate value types
recursively (reject float, None, NUL characters, keys outside [a-z0-9_], detail above 2048 canonical bytes,
actions outside the closed list of section 7.6); insert; return seq.
Write tests first: the vectors (canonical bytes, record hashes, Merkle roots for sizes 0 to 5, both checkpoint
signatures with the test key) and unit tests for every rejection branch. Add a test with 50 threads appending
concurrently against a real PostgreSQL that asserts seq is gapless and the chain verifies.
Budget: 300 lines for the whole package. Do not write a verifier here; tools/verify_audit.py belongs to C
and must stay independent, so do not create shared verification helpers for it.
Done when: `pytest tests/unit/core -q` passes and `pytest tests/contract/test_audit_vectors.py -k core -q`
passes, both shown with output; `make check-fast` exits 0.
```

### A2 · Authentication and sessions (about 2 hours) · tests T-AUTH-01 to 05
```
Task A2. Read docs/04_CONTRACTS.md section 2, rules R01 to R03 of the matrix, the tables app_user and session
in contracts/schema.sql, and decision D8 in docs/03_CONTEXT.md.
Implement login, logout, me. Requirements, each with a test:
- Argon2id through the allowlisted library with parameters at least m=19456 KiB, t=2, p=1; verify and
  rehash-if-needed on login.
- Session token: 32 bytes from the operating system CSPRNG, URL-safe base64, cookie abh_session with HttpOnly,
  Secure, SameSite=Strict, Path=/. Store only SHA-256 of the token. Idle 30 minutes, absolute 8 hours, both
  enforced on the server on every request.
- CSRF token per session, returned by login and me, required as X-CSRF-Token on unsafe methods.
- Lockout: 5 failures in 15 minutes locks the account for 15 minutes; audit auth.lockout; raise activity
  alert.login_bruteforce. Unknown email and wrong password give the same status, body and code path length
  (hash a dummy password for unknown emails).
- Middleware: X-Request-ID on every response; the security headers of section 2; the error envelope for every
  error including validation errors and unhandled exceptions (no stack traces to clients).
- Every login success and failure, and logout, is audited through abh_core.audit.append in the same
  transaction as the session change.
- A seed command creating the fixture teams and users of docs/06_VERIFICATION.md with random passwords
  written to secrets/demo_users.txt.
Never log passwords, tokens or CSRF values. Budget for this task: 250 lines.
Done when: the T-AUTH tests in tests/contract pass with output shown; `make check-fast` exits 0.
```

### A3 · Authorization engine, users, teams (about 2 hours) · tests T-RBAC-01 to 12
```
Task A3. Read contracts/rbac_matrix.yaml completely, including the comments on status codes and audit of
refusals, and docs/08_TECHNICAL_IMPLEMENTATION.md section 7.
Implement authz.py: load the matrix once; expose authorize(rule_id) as the single dependency that performs
session lookup, CSRF check, role check, object loading and scope check, and writes the denied audit record in
its own transaction. Route functions must contain no role or team comparison. At startup compare registered
routes with the matrix and exit with a clear message on any difference.
Implement R04 to R10 with business rules BR1 and BR2. A 404 for another team's object must be byte-identical
to the 404 for an unknown id. Disabling a user or changing a role deletes that user's sessions in the same
transaction.
Done when targeted tests for the implemented rules pass with real PostgreSQL and their output is recorded.
List every unimplemented matrix rule as pending; T-RBAC-05 cannot pass until all 31 real routes are registered.
```

### A4 · Environments, jobs, files, AI scans, quotas (about 2.5 hours) · tests T-RES-05, T-AUD-01, 02, 07, T-RBAC-11, 12
```
Task A4. Read docs/04_CONTRACTS.md sections 3 (R11 to R21), 4 (sizes and admission control), 5, and the env and
job tables. The runner (member B) acts on rows; you never call Docker.
Implement R11 to R21 using the single state-change pattern of docs/08 section 7: one transaction containing
the row lock on the team, the quota and host-capacity check, the insert or update, and the audit append.
R12 accepts only template app-target. R20 streams the upload to the quarantine directory while hashing and
enforcing 10 MiB, stores it as <sha256> with mode 0400, creates an S file-analysis environment with TTL 10
minutes and a job. R21 remains pending until the team approves a real AI target change request; do not queue a
job to a missing or simulated target. R14, R15 set desired_state. R17 refuses
with ENV_NOT_RUNNING unless observed_state is running, and records only the command's SHA-256 and first 200
characters in the audit detail.
Write the atomicity test T-AUD-07 yourself as a unit test too: when the audit insert fails, the state change
must be absent.
Done when all implemented routes have real behavior and applicable tests pass with output; list R21 and any
host-dependent tests as pending until their actual acceptance criteria can be met.
```

### A5 · Stream, events, metrics, overview, kill switch (about 2 hours) · tests T-MON-01, 03, 04 (API side)
```
Task A5. Read docs/04_CONTRACTS.md section 6, rules R16, R22, R23, R29, R30, and risks R-11 and R-16.
Implement the Server-Sent Events route: one listener task per process on channels abh_activity, abh_audit,
abh_metric; per-subscriber bounded queues; the scope filter applied on the server for every event type
(analyst receives no audit events; team roles receive only their team); heartbeat every 15 seconds; resume
from Last-Event-ID for activity events by replaying rows with a larger id.
Implement R16, R23, R29, R30. Overview numbers come from SQL, not from caches.
Raise alert.authz_denied_burst from the denied-audit path when one user reaches 5 denials in 60 seconds.
Done when: T-MON-01, T-MON-03, T-MON-04 pass against a running stack with a fake event inserted by SQL where the
runner is not ready yet; output shown; verified through the reverse proxy, not only directly.
```

### A6 · Notary and audit routes (about 2.5 hours) · tests T-AUD-03, 06, 08 and all T-KAT
```
Task A6. Read docs/04_CONTRACTS.md sections 7.5 to 7.8, docs/08 section 8, rules R24 to R28, and the
tamper_cases in contracts/audit_vectors.json.
Build services/notary (budget 150 lines): genesis record on an empty ledger; incremental verification of new
records every 5 seconds; checkpoint when 20 new records or 30 seconds with at least one new record; before
signing, recompute the root for every checkpoint in the witness file and compare the database checkpoint
table with the witness file; on any mismatch raise alert.tamper_detected, append audit.tamper_detected with
verdict and position in detail, and stop signing; otherwise sign with the 32-byte Ed25519 seed, insert the
checkpoint row, append the line to the witness file and fsync.
Implement R24 to R28. Export streams NDJSON in the exact format of section 7.7. R28 runs steps 1 to 4 of
section 7.8 over the database using abh_core.
Do not read or copy tools/verify_audit.py.
Done when: T-AUD-03 and T-AUD-06 pass; with the stack running, `make tamper-drill CASE=edit_field_no_rehash`
produces the alert and the audit record within 30 seconds (T-AUD-08), shown with timestamps; a live export
verifies OK with C's verifier including --witness. The tamper drill and the live export run on the demo VM;
give me the exact commands to run there over SSH and wait for the output I paste back.
```

### A7 · Hardening pass (remaining time before G3)
```
Task A7. Run `make test-contract` and Schemathesis (T-API-01). For each failure: write the smallest failing
unit test, fix the cause, rerun. Then run P-REDTEAM over services/api as a whole against TA2, TA4, TA5, TA6.
Then reduce: delete unused code, merge duplicated SQL helpers, and report the line count against the budget.
Do not add features. Done when: `make test-contract` exits 0 and the count is within budget, both shown.
```
