# 05 · Mandatory objectives

An objective is **met** only when every test listed for it passes on the demo host and its evidence file exists.
Test definitions are in `06_VERIFICATION.md`. O1 to O8 are the eight portal deliverables in portal order.
O9 comes from the problem specification sentence "test applications, suspicious files, and AI systems".
Leads: A = Henil, B = Parth, C = Bhavya. Each person's slice is in `team/<name>/03_MY_OBJECTIVES_AND_TESTS.md`.

| ID | Objective (portal wording) | What must be true | Lead | Tests that decide it |
| --- | --- | --- | --- | --- |
| **O1** | Functional platform with isolated testing environments | A user creates an environment from the console; it runs under `runsc` with the sandbox profile of `04` section 8; code inside cannot reach the host, the control plane, the internet or another environment | B | T-ISO-01, 02, 04, 06, 07; T-E2E-01 |
| **O2** | Secure user login and role-based access control | Argon2id hashes, opaque sessions with the cookie flags of `04` section 2, CSRF token, lockout; every rule of `rbac_matrix.yaml` enforced, deny by default | A | T-AUTH-01 to 05; T-RBAC-01 to 12; T-API-01 |
| **O3** | Separate environments for different users or teams | Every object carries a team; another team's object is indistinguishable from a missing one (404); networks, volumes and event streams are per team or per environment; platform roles cannot read a team's job output | A and B | T-ISO-03, 05; T-MON-03; T-RBAC-01 |
| **O4** | Real-time monitoring of user and system activities | Environment state changes, resource samples, alerts and audit records reach the console over one live stream within the latency targets of `04` section 6 | B collects, A streams, C shows | T-MON-01 to 04 |
| **O5** | Resource management for CPU, RAM and storage | Per-environment hard limits for CPU, memory, processes and storage; team quotas with admission control; expiry and cleanup; a hostile environment cannot degrade a neighbour beyond the stated bound | B (limits), A (quotas) | T-RES-01 to 06 |
| **O6** | Centralized audit logs | Every state-changing API call, every refusal and every runner and notary action writes exactly one record through the single append path, atomically with the change | A | T-AUD-01, 02, 06, 07 |
| **O7** | Tamper detection for audit records | Edits, deletions, reordering, truncation and full hash recomputation are each detected with the specified verdict by an independent verifier, and raise a console alert within 30 s | A (notary), C (verifier) | T-KAT-01 to 04; T-AUD-03, 04, 05, 08 |
| **O8** | Admin dashboard for users, environments and security activities | Console pages: overview, users and teams with quotas, environments with live usage and kill switch, live activity and alerts, audit with filter, export and verify | C | T-E2E-01 to 04 |
| **O9** | Three workload types | `app-target`: attack a vulnerable application from a toolbox. `file-analysis`: upload a file, get static triage and an optional no-network detonation report. `ai-redteam`: run garak probes against the stub model service and get findings mapped to OWASP LLM risk IDs | B | T-WL-01 to 03 |

## Definition of done for any task (all seven, no exceptions)
1. The named tests pass, shown by pasted command output.
2. `make check-fast` exits 0.
3. No contract file changed, or a CR exists.
4. No new dependency, or its registry check is recorded in `evidence/VERSIONS.lock` and the allowlist CR exists.
5. No placeholder: no `TODO`, `FIXME`, `NotImplementedError`, `mock`, `simulate`, or `STUB-G0` route in non-test code. Generate OpenAPI from implemented routes only; until all 31 are real, report the missing operations and G0/G2 as pending. The older `STUB-G0` exception is withdrawn by the current work-order decision in `16_BUILD_NOW_HOST_LATER.md`.
6. Every security-relevant branch has a test that takes the refusing path.
7. A hand-off note in the format of `07_ANTI_HALLUCINATION.md` section 5 is written.

## Code budget (non-test, non-generated lines; `make check-fast` prints the count)

| Component | Budget | Component | Budget |
| --- | --- | --- | --- |
| `core/abh_core` | 300 | `services/runner` | 800 |
| `services/api` | 1100 | `sandbox/` (Dockerfiles, vulnerable app, model stub, rules, probes) | 450 |
| `services/notary` | 150 | `tools/verify_audit.py` | 180 |
| `web/src` | 1800 | `host/` scripts | 150 |

Style limits: function at most 40 lines, file at most 300 lines, no abstraction with fewer than two call
sites, no wrapper that only renames a library call, full type annotations (mypy strict, TypeScript strict,
no `any`). Going over a budget needs one line in the bug journal saying why the extra lines are not removable.
The budget is a ceiling against bloat, not a target; fewer lines that pass the same tests are better.

## Stretch objectives (only after G4, in this order, each behind a flag that defaults to off)

| ID | Objective | Proof |
| --- | --- | --- |
| S1 | TOTP second factor for `admin` and `auditor` | Login without code refused; test with a fixed secret and clock |
| S2 | Interactive web terminal into `toolbox`, with session start and end audited | Terminal session works; R17 authorization applies; idle timeout closes it |
| S3 | External anchor for checkpoints (a remote git repository or a public timestamp service such as OpenTimestamps [S40]) | An anchor proof file per checkpoint verifies offline |
| S4 | Verification in the browser: the console recomputes the chain and checks signatures locally | The ten tamper cases give the same verdicts in the browser as in the CLI |
| S5 | System-call level activity from gVisor runtime monitoring for one template | Process start and network connect events of a sandbox appear as activity events |
| S6 | Signature scanning with ClamAV (`clamscan` [S43]) in the file pipeline | The antivirus test file is flagged by signature name |
| S7 | Inclusion proof for one record: the verifier prints the RFC 6962 audit path [S15] from a record to a signed checkpoint and checks it, the way Sigstore's Rekor pairs an inclusion proof with a checkpoint [S52] | For every record of the vector export the proof verifies against the checkpoint root; a proof for an altered record fails |
| S8 | A real small language model as a second AI target, running on a laptop GPU outside the platform and reached through one allowlisted address (network tier N1 in the notation of D12 [S49]) | T-ISO-04 still passes for every other address; the scan completes with the internet disconnected; the agent first researches the model server and its options under rule H2 |
