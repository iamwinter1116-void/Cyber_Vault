# 06 · Verification plan

Principle: the platform is the target. A test counts only if it could fail. Each test below states the
procedure and the single pass condition. None of them asks a human or an AI whether the result "looks right".

Rules for all tests
- Security tests run against the real stack: real PostgreSQL, real Docker, real `runsc`. No mocks of the
  database or the container engine in `tests/contract`, `tests/security`, `tests/e2e`.
- No `skip`, `xfail`, retries or sleeps longer than the latency target being tested.
- The author of the code under test does not edit its contract or security test. A red test means fix the
  code or raise a change request.
- Fixtures (`make demo-reset`): teams `alpha`, `bravo`; users `admin`, `auditor`, `lead.alpha`,
  `analyst.alpha`, `analyst2.alpha`, `lead.bravo`, `analyst.bravo`. Passwords are generated at seed time into
  `secrets/demo_users.txt`.
- `make demo-reset` also plants two flags for judge X-08: `flag_env`, a random string written through the public
  API into a file under `/workspace` of an environment owned by `analyst.alpha`, and `flag_host`, a random
  string in `/var/lib/abhedya/flag_host` on the demo host, owner root, mode 0400. Both values are copied to
  `secrets/flags.txt` and appear in no image, environment variable or audit record.
- Every run writes JUnit XML to `evidence/tests/`.

## 1. Known-answer tests (ledger format) · `make test-contract`

| ID | Procedure | Pass condition |
| --- | --- | --- |
| T-KAT-01 | For each record in `audit_vectors.json`, compute `canonical(body)` with `abh_core` and, separately, with `tools/verify_audit.py` | Bytes equal `canonical_utf8` in both |
| T-KAT-02 | Compute record hashes and Merkle roots for tree sizes 0 to 5 in both implementations | All equal the vectors |
| T-KAT-03 | Sign both checkpoint bodies with the test key in `abh_core`; verify both signatures in the verifier | Signatures equal the vectors (Ed25519 is deterministic); verification succeeds |
| T-KAT-04 | Apply each of the ten `tamper_cases` to the vector export and run the verifier, with and without `--witness` where the case says so | Verdict and `at` equal `expected_verdict` and `expected_at`; exit code 0 only for `untouched` |

## 2. Authentication · `make test-contract`

| ID | Procedure | Pass condition |
| --- | --- | --- |
| T-AUTH-01 | Create a user, read `password_hash` from the database | Starts with `$argon2id$`, parameters at least m=19456, t=2, p=1 |
| T-AUTH-02 | Log in over HTTPS, inspect `Set-Cookie` and the `session` table | Flags `HttpOnly`, `Secure`, `SameSite=Strict`; token decodes to 32 bytes; table holds only its SHA-256 |
| T-AUTH-03 | Six wrong passwords, then the right one; repeat with an unknown email | Sixth and seventh attempts return `ACCOUNT_LOCKED`; `auth.lockout` audited; unknown-email response body identical to wrong-password body |
| T-AUTH-04 | Use a session after logout; after the user is disabled; after 31 idle minutes (clock advanced in the database) | 401 each time |
| T-AUTH-05 | Send each state-changing route with a valid cookie and no `X-CSRF-Token`, then with a wrong one | 403 `CSRF_FAILED`, no state change |

## 3. Authorization · `make test-contract`

| ID | Procedure | Pass condition |
| --- | --- | --- |
| T-RBAC-01 | Generated from `rbac_matrix.yaml`: every rule called as anonymous and as each of the four roles | 401 for anonymous on non-public rules; 403 for roles not listed; not 401 or 403 for listed roles |
| T-RBAC-02 | Every rule with a path parameter, called by an allowed role of team alpha on a bravo object | 404, body identical to the 404 for a random UUID |
| T-RBAC-03 | Rules with scope `own`: `analyst2.alpha` on an object of `analyst.alpha` | 403 |
| T-RBAC-04 | Every list rule as each role | Only in-scope rows; counts equal a direct SQL count for that scope |
| T-RBAC-05 | Compare the API's registered routes with the matrix | Sets are equal; the app refuses to start when a route is missing from the matrix |
| T-RBAC-06 | Inspect every JSON response in the suite | No key outside the shapes of `04` section 4; never `password_hash`, `totp_secret`, `token_sha256`, `csrf_token` of others |
| T-RBAC-07 | `admin` and `auditor` call R17 to R21 on any team | 403: platform roles cannot run commands or read job output |
| T-RBAC-08 | Disable a logged-in user; change a logged-in user's role | Next request with the old cookie is 401 |
| T-RBAC-09 to 12 | Business rules BR1 to BR4, in that order | 409 with the named code, audited as denied |
| T-API-01 | Schemathesis against `contracts/openapi.yaml` with a session per role, stateful phase on | No 5xx; every response conforms to the schema |

## 4. Isolation · `make test-security`

| ID | Procedure | Pass condition |
| --- | --- | --- |
| T-ISO-01 | `docker inspect` every container labelled `abh.managed=true` | `HostConfig.Runtime` is `runsc` for all, or the stack is visibly in degraded mode with the alert raised |
| T-ISO-02 | Same inspect output against `04` section 8 | Every row of the profile table holds: capabilities dropped, no-new-privileges, read-only root, non-root user, not privileged, no host namespaces, only allowed mounts, limits set, labels set |
| T-ISO-03 | From alpha's `toolbox`: TCP connect and ICMP to every IP of bravo's containers, and DNS lookup of their names | All fail or time out within 3 s |
| T-ISO-04 | From any sandbox: connect to the bridge gateway address on 443, 5432, 8000; to the host's LAN address on the same ports; to a public IP on 53 and 443 | All fail. From a `detonator` container: no network interface other than loopback |
| T-ISO-05 | As `analyst.alpha`: fetch, stop, delete, exec, read metrics and jobs of a bravo environment; subscribe to the stream and trigger bravo events | 404 on every call; zero bravo events received |
| T-ISO-06 | Inside each sandbox: list environment variables and mounts; look for a Docker socket; try to write outside `/tmp` and `/workspace` | No `ABH_`, database or key material; no socket; writes fail with a read-only error |
| T-ISO-07 | Compare `uname -r` inside a sandbox with the host | Different release strings (the sandbox reports gVisor's kernel, not the host's). If equal, the runtime is not `runsc`: fail |
| T-STATIC-01 | Search `compose.yaml` and the runner's launch code | Docker socket mounted only in `runner`; no `privileged`, no `network_mode: host`, no `cap_add` anywhere |

## 5. Resources · `make test-security`

| ID | Procedure | Pass condition |
| --- | --- | --- |
| T-RES-01 | In an S environment allocate memory until killed, while a second environment runs a 1 s loop of `echo` | Container OOM-killed; `alert.oom_killed` on the stream within 5 s; `env.oom_killed` audited; the neighbour's loop never misses more than one beat |
| T-RES-02 | Start a fork bomb in an S environment | For 30 s: `GET /healthz` under 1 s; neighbour exec returns within 5 s; afterwards the environment stops and is removed within 15 s. Record in evidence which limit contained it |
| T-RES-03 | Write to `/workspace` until failure | Write fails with "no space" at or below `storage_mb`; host free space dropped by no more than the quota; neighbour can still write |
| T-RES-04 | Burn all CPUs inside an S environment for 20 s | Its cgroup CPU usage over the window is at most 115 % of `cpu_millis`; `GET /healthz` p95 under 300 ms during the burn |
| T-RES-05 | Request environments until the team quota, then one more; then set a lower quota and request again | 409 `QUOTA_EXCEEDED`, audited as denied; `Team.usage` equals the SQL sum |
| T-RES-06 | Create an environment with TTL 1 minute; also kill the runner mid-provision and restart it | After expiry: row `destroyed`, `env.expired` audited, and no container, network or volume with that `abh.env_id` label remains; after restart the runner converges without duplicates |

## 6. Audit ledger · `make test-security`

| ID | Procedure | Pass condition |
| --- | --- | --- |
| T-AUD-01 | Call every rule that has `audit:` in the matrix once successfully | Exactly one new record per call with that action, the caller as actor, the right target and `request_id` |
| T-AUD-02 | Trigger each refusal type (403 role, 404 scope, 409 business rule, failed login) | One record with `outcome=denied` each; anonymous 401s on other routes add no ledger record |
| T-AUD-03 | As `abh_api`, `abh_runner`, `abh_notary`: attempt UPDATE, DELETE, TRUNCATE on `audit_log` and `audit_checkpoint` | Permission denied for each role |
| T-AUD-04 | As database superuser with the triggers disabled, apply each tamper case to the live ledger (`make tamper-drill CASE=...`), export, run the verifier with the witness file | Verdict and position as specified for each of the ten cases |
| T-AUD-05 | Hypothesis: generate random valid logs (1 to 200 records, random checkpoints), apply one random mutation (edit any field, delete, insert, swap, truncate below a checkpoint, alter a checkpoint) | The verifier never returns OK for a mutated log; always OK for the unmutated one |
| T-AUD-06 | 200 concurrent API calls that each write an audit record | `seq` is 1..n with no gaps or duplicates; verifier OK |
| T-AUD-07 | Make the audit insert fail (revoke INSERT temporarily) and call a state-changing route | 500, and the state change is absent: no row, no container |
| T-AUD-08 | With the stack running, apply `edit_field_no_rehash`, then separately `smart_attacker_rehash_before_checkpoint_3` style changes to live rows | Within 30 s: `alert.tamper_detected` on the stream, console banner, `audit.tamper_detected` appended, and the notary signs no further checkpoint over the altered history |

## 7. Monitoring · `make test-security`

| ID | Procedure | Pass condition |
| --- | --- | --- |
| T-MON-01 | Subscribe to R22, create and stop an environment | `env.state_changed` events for each transition within 3 s of the database change |
| T-MON-02 | Keep one environment running for 30 s | At least 6 `metric` events; values within plausible bounds (0 ≤ mem ≤ limit × 1.05) |
| T-MON-03 | `analyst.alpha` and `analyst.bravo` subscribe; trigger activity in both teams | Each receives only its team's events; `auditor` receives both; `analyst` receives no `audit` events |
| T-MON-04 | Disconnect the stream, generate 10 events, reconnect with `Last-Event-ID` | All 10 received once, in order |

## 8. Workloads and end to end

| ID | Procedure | Pass condition |
| --- | --- | --- |
| T-WL-01 | Create `app-target`; from `toolbox` request the target's home page by container name | HTTP 200 inside the environment; the same name does not resolve from another environment |
| T-WL-02 | Upload the industry-standard antivirus test file and a benign text file, detonate a script that tries to open a network connection | Test file verdict `malicious` with the rule name; text file `clean`; detonation report shows the connection failed; sample stored as `<sha256>` with mode 0400; after the job ends no container, network or volume labelled with that environment remains (DETER's containment plan calls for the same removal of live malware before nodes are reused [S45]) |
| T-WL-03 | Run `ai_scan` with `probe_set: quick` on `stub-vulnerable`, then on `stub-guarded`, with networking to the internet absent | Job `done`; failures greater than zero on the vulnerable stub and strictly fewer on the guarded stub; each probe row carries an OWASP LLM risk ID; `report_sha256` matches the stored report |
| T-E2E-01 | Browser: log in as `analyst.alpha`, create an environment, wait for `running`, run a command, see output | Completes without page reload |
| T-E2E-02 | Browser as `admin`: create a user and a team, change a quota, use the kill switch | State visible in the console and in the ledger |
| T-E2E-03 | Browser as `auditor`: open audit, filter, export, press Verify | Result OK and the last checkpoint shown |
| T-E2E-04 | Browser as `auditor` while a tamper drill runs | Red banner appears within 30 s without reload |

## 9. Judges that are not us

| ID | Outside judge | What it decides | Evidence file |
| --- | --- | --- | --- |
| X-01 | Docker Bench for Security (checks based on the CIS Docker Benchmark v1.6.0 [S35]; automated checking of runtime configuration is what NIST SP 800-190 recommends [S36]) | Host and container runtime configuration. Expected warning to document: the runner mounts the Docker socket, which is part of the trusted computing base | `evidence/scans/docker-bench.txt` |
| X-02 | Trivy | Known vulnerabilities and secrets in our images and repository; misconfiguration scan must be enabled explicitly because it is off by default [S37] | `evidence/scans/trivy-*.json` |
| X-03 | Semgrep with a public Python and TypeScript security ruleset | Injection, unsafe deserialisation, weak crypto in our code | `evidence/scans/semgrep.json` |
| X-04 | gitleaks | Secrets in git history | `evidence/scans/gitleaks.json` |
| X-05 | OWASP ZAP baseline scan of the console | Missing headers, cookie flags, obvious web flaws | `evidence/scans/zap.html` |
| X-06 | Schemathesis (T-API-01), which generates property-based tests from the OpenAPI schema [S38] | The API never answers 5xx and never violates its schema on generated input | `evidence/tests/schemathesis.xml` |
| X-07 | The witness file, and for S3 an external anchor | That a checkpoint existed before a dispute | `evidence/witness/` |
| X-08 | A person outside the team with an `analyst.bravo` account and 30 minutes | Five flags: name any alpha environment; make the API return 5xx; change an audit row without detection; read `flag_env`; read `flag_host`. The last two follow Google kCTF's practice of planting flags that can be read only by breaking out of the sandbox or breaking the isolation between workloads [S46] | `evidence/break-it.md` with what they tried |
| X-09 | The jury | Picks the audit row to corrupt and runs the verifier on a machine the team does not control | live |

Triage rule for scanners: every HIGH or CRITICAL finding is fixed, or listed in `evidence/scans/ACCEPTED.md`
with a reason a security reviewer would accept. A scanner that was not run is reported as not run.
