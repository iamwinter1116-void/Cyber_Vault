# 04 · Canonical contracts

These are the interfaces between the four implementation owners. They are **frozen at gate G0**.
Machine-readable parts live in `contracts/` and win over this prose if the two ever disagree:

| File | Fixes | Validated how |
| --- | --- | --- |
| `contracts/schema.sql` | Tables, constraints, triggers, roles, grants | Applied cleanly on PostgreSQL 19 (PGlite build) during pack preparation; constraint, trigger and grant behaviour exercised. Re-validate on your server at G0. |
| `contracts/rbac_matrix.yaml` | 31 API rules, roles, scopes, status codes | Parsed as YAML. Tests are generated from it. |
| `contracts/audit_vectors.json` | Known-answer vectors for the ledger: 5 records, 6 Merkle roots, 2 signed checkpoints, 10 tamper cases | Generated in Python, re-verified by an independent JavaScript implementation |
| `contracts/openapi.yaml` | Exact request and response schemas | Generated from the API code by `make openapi` at G0, then committed; CI fails if regeneration differs |

**Change request (CR) rule.** Nobody, human or agent, edits a contract after G0. To change one: add a CR entry
in `09_BUG_JOURNAL.md` (what, why, who is affected), get a yes from all four members, change the contract
and every affected test in one commit titled `CR-<n>`.

## 1. Repository layout and ownership

```
abhedya/
  CLAUDE.md                     shared, frozen
  .claude/settings.json         shared, frozen (deny rules, stop hook)
  .claude/agents/reviewer.md    shared
  Makefile                      D/Manas owns; target names fixed in section 11
  compose.yaml                  D/Manas owns; A and B provide service requirements for integration
  contracts/                    frozen
  docs/                         this pack; only 09_BUG_JOURNAL.md is edited during the build (by humans)
  team/<name>/                  one folder per person: start file, device setup, prompts, objective slice (frozen)
  team/<name>/work/             that person's JOURNAL.md and HANDOFFS.md (the only editable part of team/)
  core/abh_core/                A/Henil   shared Python package: settings, db, audit, authz types
  services/api/                 A/Henil   FastAPI application
  services/notary/              A/Henil   checkpoint signer and continuous verifier
  services/runner/              B/Parth   reconciler, sandbox launcher, collectors, job executor
  sandbox/templates/            B/Parth   Dockerfiles and template.yaml for each template
  host/                         B/Parth   preflight.sh, setup_host.sh, daemon.json
  web/                          C/Bhavya  React console
  tools/verify_audit.py         C/Bhavya  independent verifier; imports nothing from core/ or services/
  tests/unit/                   each feature owner, mirrored by component
  tests/contract/               C/Bhavya  vectors, RBAC matrix, OpenAPI conformance
  tests/security/               C/Bhavya writes; B/Parth supplies sandbox probes
  tests/e2e/                    C/Bhavya
  .github/, db/init/             D/Manas  CI and schema initialization
  evidence/                     generated outputs only
```

A member's agent writes only inside that member's directories. Reading everything is allowed.
Roles: A = Henil, B = Parth, C = Bhavya, D = Manas (`02_MASTER_PLAN.md` section 3). D is not an API role.

## 2. API conventions (prefix `/api/v1`)

- JSON only, UTF-8. Timestamps are RFC 3339 UTC strings. IDs are UUID strings.
- Session: cookie `abh_session` = 32 random bytes from the OS CSPRNG, URL-safe base64. Attributes
  `HttpOnly; Secure; SameSite=Strict; Path=/`. The server stores only SHA-256 of the token.
  Idle timeout 30 minutes, absolute lifetime 8 hours. Logout, disable and role change delete the session rows.
- CSRF: login returns `csrf_token`. Every POST, PATCH, DELETE except login must send it as `X-CSRF-Token`;
  a missing or wrong value is 403 with code `CSRF_FAILED`.
- Lockout: 5 failed logins for one account within 15 minutes lock it for 15 minutes (`ACCOUNT_LOCKED`, 403).
  Responses for unknown email and wrong password are identical in body and timing class.
- Errors: `{"error": {"code": "<CODE>", "message": "<human text>", "request_id": "<id>"}}`.
- Every response carries `X-Request-ID`. The same value is the audit record's `request_id`.
- Lists: `?limit=` (1 to 200, default 50) and `?cursor=`; response `{"items": [...], "next_cursor": string|null}`.
- Security headers on every response: `Content-Security-Policy: default-src 'self'`, `X-Content-Type-Options: nosniff`,
  `Referrer-Policy: no-referrer`, `Cache-Control: no-store` on API responses.

Error codes (closed list): `UNAUTHENTICATED` 401 · `FORBIDDEN` 403 · `CSRF_FAILED` 403 · `ACCOUNT_LOCKED` 403 ·
`NOT_FOUND` 404 · `QUOTA_EXCEEDED` 409 · `ENV_NOT_RUNNING` 409 · `LAST_ADMIN` 409 · `SELF_ROLE_CHANGE` 409 ·
`CONFLICT` 409 · `VALIDATION` 422 · `PAYLOAD_TOO_LARGE` 413 · `RATE_LIMITED` 429 · `INTERNAL` 500.

## 3. Endpoints (authorization per rule ID is in `contracts/rbac_matrix.yaml`)

| Rule | Method and path | Request body | Success |
| --- | --- | --- | --- |
| R01 | POST /auth/login | `{email, password}` | 200 `{user: User, csrf_token}` and sets cookie |
| R02 | POST /auth/logout | none | 204 |
| R03 | GET /auth/me | | 200 `{user: User, csrf_token}` |
| R04 | GET /users | | 200 list of User |
| R05 | POST /users | `{email, password, role, team_id|null}` | 201 User |
| R06 | PATCH /users/{user_id} | any of `{role, team_id, disabled, password}` | 200 User |
| R07 | GET /teams | | 200 list of Team |
| R08 | POST /teams | `{name}` plus optional quota fields | 201 Team |
| R09 | PATCH /teams/{team_id} | any of the four quota fields | 200 Team |
| R10 | GET /templates | | 200 list of Template |
| R11 | GET /envs | filters `team_id`, `state` | 200 list of Env |
| R12 | POST /envs | `{name, template, size, ttl_minutes?}` (`template` must be `app-target`; the other two are created through R20 and R21) | 201 Env with `observed_state: "requested"` |
| R13 | GET /envs/{env_id} | | 200 Env |
| R14 | POST /envs/{env_id}/stop | none | 202 Env |
| R15 | DELETE /envs/{env_id} | none | 202 Env |
| R16 | GET /envs/{env_id}/metrics | `?minutes=` 1 to 60 | 200 `{items: [MetricSample]}` |
| R17 | POST /envs/{env_id}/exec | `{command}` 1 to 4096 chars, optional `{container: "toolbox"|"target"}` default toolbox | 202 Job |
| R18 | GET /jobs | filters `kind`, `env_id` | 200 list of Job |
| R19 | GET /jobs/{job_id} | | 200 Job |
| R20 | POST /files | multipart: `file` (max 10 MiB), `detonate` true or false | 202 Job (kind `file_analysis`) |
| R21 | POST /ai-scans | `{target: "stub-vulnerable"|"stub-guarded", probe_set: "quick"|"full"}` | 202 Job (kind `ai_scan`) |
| R22 | GET /stream | Server-Sent Events, section 6 | 200 `text/event-stream` |
| R23 | GET /events | filters `severity`, `env_id`, `after_id` | 200 list of ActivityEvent |
| R24 | GET /audit | filters `action`, `actor_id`, `outcome`, `from_seq`, `to_seq` | 200 list of AuditRecord |
| R25 | GET /audit/export | `?kind=records|checkpoints` | 200 `application/x-ndjson`, section 7.7 |
| R26 | GET /audit/checkpoints | | 200 list of Checkpoint |
| R27 | GET /audit/pubkey | | 200 `{public_key_hex, log_id, algorithm: "ed25519"}` |
| R28 | POST /audit/verify | none | 200 VerifyResult |
| R29 | GET /admin/overview | | 200 Overview |
| R30 | POST /admin/kill-switch | `{team_id: uuid|null}` (null means every team) | 202 `{affected: int}` sets `desired_state` to `stopped` |
| R31 | GET /healthz | | 200 `{status: "ok", db: bool}` |

## 4. Resource shapes (fields are exhaustive; no others may be returned)

- **User** `{id, email, role, team_id, disabled, created_at}`. Never `password_hash`, `totp_secret`, counters.
- **Team** `{id, name, quota_envs, quota_cpu_millis, quota_mem_mb, quota_storage_mb, usage: {envs, cpu_millis, mem_mb, storage_mb}}`
- **Template** `{name, title, description, containers: [string], sizes: ["S","M","L"]}`
- **Env** `{id, team_id, owner_id, name, template, size, cpu_millis, mem_mb, storage_mb, pids_limit, desired_state, observed_state, isolation_tier, failure_reason, expires_at, created_at}`
- **MetricSample** `{ts, cpu_pct, mem_mb, storage_mb, pids, net_rx_bytes, net_tx_bytes}`
- **Job** `{id, kind, env_id, team_id, requested_by, input, status, result, created_at, started_at, finished_at}`
- **ActivityEvent** `{id, ts, team_id, env_id, severity, kind, message, data}`
- **AuditRecord** the 15 body fields of section 7.2 plus `hash`
- **Checkpoint** `{v, log_id, tree_size, root_hash, head_hash, ts, signature}`
- **VerifyResult** `{ok, verdict, at, records, checkpoints, unanchored_tail, checked_at}` where `at` is the
  sequence number or tree size named by the verdict, or null
- **Overview** `{users, teams, envs_by_state: {..}, host: {cpu_millis_total, cpu_millis_allocated, mem_mb_total, mem_mb_allocated, storage_mb_allocated}, alerts_last_hour, ledger: {records, last_checkpoint: Checkpoint|null, last_verify: VerifyResult|null}, isolation: {runtime, degraded: bool}}`

**Sizes** (the API copies these into the env row; users cannot send raw limits):

| Size | cpu_millis | mem_mb | storage_mb | pids_limit |
| --- | --- | --- | --- | --- |
| S | 500 | 256 | 128 | 128 |
| M | 1000 | 512 | 256 | 256 |
| L | 2000 | 1024 | 512 | 512 |

**Admission control (same transaction as the insert, with `SELECT ... FOR UPDATE` on the team row):**
the sum over the team's environments whose `observed_state` is not `destroyed` or `failed`, plus the request,
must not exceed any team quota; and the sum over all teams plus the request must not exceed host capacity minus
`ABH_HOST_RESERVED_CPU_MILLIS` and `ABH_HOST_RESERVED_MEM_MB`. Otherwise 409 `QUOTA_EXCEEDED`, audited.
Default TTL 60 minutes, maximum 240. File and AI environments get TTL 10 minutes and size S (file) or M (AI).

## 5. Job shapes

| kind | input | result when done |
| --- | --- | --- |
| `exec` | `{command, container}` | `{exit_code, output, truncated, duration_ms}`; `output` is combined stdout and stderr, at most 65536 bytes; timeout 60 s gives status `timeout` |
| `file_analysis` | `{sha256, filename, size_bytes, detonate}` | `{sha256, file_type, yara_matches: [string], detonation: null or {exit_code, duration_ms, output_tail, timed_out}, verdict}` with verdict in `clean`, `suspicious`, `malicious`, `unknown` |
| `ai_scan` | `{target, probe_set}` | `{probes: [{probe, attempts, failures, owasp_llm}], attempts, failures, report_sha256}` |

Verdict rule (deterministic, no judgement): any YARA match tagged `malicious` gives `malicious`; any other
match or a detonation that timed out gives `suspicious`; no match gives `clean`; a pipeline error gives `unknown`.
Uploaded bytes are stored as `$ABH_QUARANTINE_DIR/<sha256>` with mode 0400, never under the original
filename, and are never executed outside a sandbox.

## 6. Real-time stream

Transport: Server-Sent Events on R22. Events are filtered by the caller's scope on the server.
`id:` is set for `activity` events (the row id) so `Last-Event-ID` resumes without loss.

| SSE event | data | Source |
| --- | --- | --- |
| `activity` | ActivityEvent | NOTIFY `abh_activity` (payload: row id) |
| `audit` | AuditRecord (admin, auditor: all; team_lead: own team; analyst: none) | NOTIFY `abh_audit` (payload: seq) |
| `metric` | `{env_id, ...MetricSample}` | NOTIFY `abh_metric` (payload: JSON, sent by the runner) |
| `heartbeat` | `{ts}` every 15 s | API |

Activity kinds (closed list). Severity in brackets.
`env.state_changed` [info] · `env.failed` [warn] · `env.expired` [info] · `job.finished` [info] ·
`alert.oom_killed` [critical] · `alert.mem_high` [warn] (above 90 % of limit for 3 samples) ·
`alert.cpu_saturated` [warn] (above 95 % of limit for 5 samples) · `alert.storage_high` [warn] (above 90 %) ·
`alert.authz_denied_burst` [warn] (5 denials by one user in 60 s) · `alert.login_bruteforce` [warn] (lockout) ·
`alert.isolation_degraded` [critical] · `alert.tamper_detected` [critical] · `authn.anonymous_rejected` [info].

Latency targets tested in T-MON: state change visible within 3 s, metric sample at least every 5 s per
running environment, tamper alert within 30 s of the change.

## 7. Audit ledger specification `abhedya-audit-v1`

### 7.1 Canonical bytes
`canonical(x)` = JSON text of `x` with object keys sorted by code point, no insignificant whitespace,
non-ASCII characters written literally, encoded as UTF-8. Allowed value types: string, integer with absolute
value below 2^53, boolean, object, array. **Forbidden:** floats, null, NUL characters, keys outside `[a-z0-9_]`.
Python: `json.dumps(x, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")`.
JavaScript: recursive sorted-key serialiser using `JSON.stringify` for scalars. Both reproduce the vectors.

### 7.2 Record body (exactly these 15 keys)
`v` (always 1) · `seq` (1, 2, 3, ... no gaps) · `ts` (`YYYY-MM-DDTHH:MM:SS.ffffffZ`, taken from the database
clock) · `actor_type` (`user`, `service`, `system`) · `actor_id` · `actor_role` · `team_id` · `action` ·
`target_type` · `target_id` · `outcome` (`success`, `denied`, `error`) · `ip` · `request_id` · `detail` (object,
canonical size at most 2048 bytes) · `prev_hash`.
Absent values are the empty string, never null. Secrets, passwords, session tokens, file contents and command
output never appear in `detail`. For `env.exec`, `detail` holds the command's SHA-256 and its first 200 characters.

### 7.3 Hashes
`hash = hex(SHA-256(0x00 || canonical(body)))`. For `seq` 1, `prev_hash` is 64 zeros; otherwise it is the
previous record's `hash`. This is the RFC 6962 leaf hash, so the same value serves the chain and the tree.
Merkle tree hash over the first n record hashes, per RFC 6962 section 2.1: MTH of zero leaves is SHA-256 of
the empty string; of one leaf is that leaf hash; of n > 1 leaves is `SHA-256(0x01 || MTH(first k) || MTH(rest))`
with k the largest power of two smaller than n.

### 7.4 Append protocol (the only write path; `abh_core.audit.append`)
Inside the caller's database transaction: take `pg_advisory_xact_lock(4242001)`; read the last `seq` and
`hash`; read `ts` from `clock_timestamp()`; compute the hash; insert. The state change and its audit record
commit together or not at all. A refusal is recorded in its own transaction.

### 7.5 Checkpoints and witness
Checkpoint body: `{v: 1, log_id, tree_size, root_hash, head_hash, ts}`; `log_id` = first 16 hex characters of
SHA-256 of the raw 32-byte public key; `signature` = hex of Ed25519 over `canonical(body)`.
The notary issues a checkpoint when 20 new records exist or 30 seconds have passed with at least one new record.
Before signing checkpoint n it recomputes the root for every earlier checkpoint in its **witness file** and
refuses to sign if any differs (verdict `ROOT_MISMATCH`), raising `alert.tamper_detected` instead.
Each checkpoint is written to (1) table `audit_checkpoint`, (2) the witness file `$ABH_WITNESS_PATH`
(NDJSON, append, fsync) on a volume mounted only in the notary container. Stretch S3 adds an external anchor.
The private key is a 32-byte Ed25519 seed in a file readable only by the notary container.

### 7.6 Actions (closed list)
From API rules: `auth.login`, `auth.logout`, `user.create`, `user.update`, `team.create`, `team.quota_update`,
`env.create`, `env.stop`, `env.destroy`, `env.exec`, `file.submit`, `ai.scan_start`, `audit.export`,
`audit.verify`, `admin.kill_switch`, `authz.denied`.
From services: `audit.genesis` (notary, first record), `audit.tamper_detected` (notary), `auth.lockout` (API),
`env.provisioned`, `env.stopped`, `env.destroyed`, `env.expired`, `env.failed`, `env.oom_killed`,
`job.finished`, `isolation.degraded` (runner).

### 7.7 Export format (R25 and the verifier's input)
Records: NDJSON, one object per line, the 15 body keys plus `hash`, ascending `seq`.
Checkpoints: NDJSON, one object per line, the 6 body keys plus `signature`, ascending `tree_size`.

### 7.8 Verification algorithm and verdicts (first failure wins, in this order)
1. For position i = 1..n: `seq` must equal i, else **SEQ_GAP** at i.
2. `prev_hash` must equal the previous record's `hash` (zeros at i = 1), else **CHAIN_BREAK** at i.
3. The recomputed hash must equal `hash`, else **HASH_MISMATCH** at i.
4. For each checkpoint in ascending `tree_size`: signature must verify, else **BAD_SIGNATURE** at tree_size;
   `tree_size` must not exceed n, else **TRUNCATED** at tree_size; recomputed root and `head_hash` must match,
   else **ROOT_MISMATCH** at tree_size.
5. If a witness file is given: every witness checkpoint must appear unchanged among the checkpoints, else
   **CHECKPOINT_REGRESSION** at the smallest missing tree_size.
6. Otherwise **OK**. `unanchored_tail` = n minus the largest tree_size (a number to report, not a failure).

`tools/verify_audit.py --records FILE --checkpoints FILE --pubkey HEX [--witness FILE]` prints one VerifyResult
JSON line. Exit code 0 for OK, 2 for any tamper verdict, 3 for usage or input errors.
The ten cases in `audit_vectors.json` → `tamper_cases` fix the expected verdict for each kind of attack.

## 8. Sandbox profile (every container the runner starts; asserted by T-ISO-02 through `docker inspect`)

| Setting | Value |
| --- | --- |
| Runtime | `runsc`. If preflight found it missing and `ABH_ALLOW_DEGRADED=true`: `runc`, and the runner sets `isolation_tier = runc-hardened`, appends `isolation.degraded`, raises `alert.isolation_degraded`. Default is to refuse to start environments. |
| Image | From the template allowlist only, referenced by digest, already present locally (pull policy never) |
| User | Non-root UID:GID `1000:1000` |
| Capabilities | Drop `ALL`, add none |
| Security options | `no-new-privileges` |
| Privileged | false. No devices. No host PID, IPC, UTS or network namespace |
| Root filesystem | Read-only. `/tmp` tmpfs `rw,noexec,nosuid,size=64m`. `/workspace` = the environment's quota volume |
| Mounts | Only the two above, plus for `file-analysis` the single sample file read-only. Never the Docker socket, never a host directory |
| Limits | `nano_cpus = cpu_millis * 1e6`, `mem_limit = mem_mb`, swap equal to memory (no swap), `pids_limit` |
| Network | `abh-env-<env_id>`: bridge, internal, gateway mode isolated, created per environment. Detonation containers use network `none`. No published ports |
| Environment variables | Only template-defined, non-secret values. Nothing starting with `ABH_`, no database or key material |
| Labels | `abh.managed=true`, `abh.env_id`, `abh.team_id`, `abh.template` |
| Lifetime | Removed with network and volume on destroy or expiry. The reaper removes any labelled object whose env row is `destroyed` or missing |

Templates: `app-target` = containers `target` (a deliberately vulnerable web application) and `toolbox`
(shell, curl, nmap-class tools). `file-analysis` = container `analyzer`, then `detonator` (network none) when
requested. `ai-redteam` = containers `llm-target` (the in-repo stub with a hidden instruction and a planted
secret, in a vulnerable and a guarded mode) and `scanner` (garak).

## 9. Processes, networks, volumes, variables

| Service | Network(s) | Published | Mounts | DB role |
| --- | --- | --- | --- | --- |
| `proxy` (TLS, static console files) | edge, control | 443 on the demo interface | console build, TLS data | none |
| `api` | control | none | quarantine (rw) | `abh_api` |
| `runner` | control | none | Docker socket, quarantine (ro), volume directory | `abh_runner` |
| `notary` | control | none | key (ro), witness (rw) | `abh_notary` |
| `db` | control | none (use `docker compose exec db psql` for drills) | data | owner at init only |

`control` is itself an internal network. Sandboxes are never attached to `control` or `edge`.

Variables (names fixed): `ABH_DB_DSN` (per service) · `ABH_SESSION_IDLE_MIN=30` · `ABH_SESSION_ABS_HOURS=8` ·
`ABH_ENV_TTL_MIN=60` · `ABH_SANDBOX_RUNTIME=runsc` · `ABH_ALLOW_DEGRADED=false` ·
`ABH_HOST_RESERVED_CPU_MILLIS=1000` · `ABH_HOST_RESERVED_MEM_MB=2048` · `ABH_QUARANTINE_DIR=/quarantine` ·
`ABH_VOLUME_DIR=/var/lib/abhedya/vol` · `ABH_NOTARY_KEY_PATH=/run/secrets/notary_ed25519` · `ABH_NOTARY_PUBKEY_PATH=/run/secrets/notary_ed25519.pub` (public, mounted read-only into `api`) ·
`ABH_WITNESS_PATH=/witness/checkpoints.ndjson` · `ABH_CHECKPOINT_EVERY_N=20` · `ABH_CHECKPOINT_EVERY_SEC=30` ·
`ABH_AUDIT_RETENTION_DAYS=180` · `ABH_METRIC_INTERVAL_SEC=2`.
Secrets come from files under `./secrets/` (git-ignored, denied to agents), never from committed files.

## 10. Shared library `abh_core` (A delivers the audit part first; B and the notary import it)

```python
# abh_core/audit.py
Outcome = Literal["success", "denied", "error"]
@dataclass(frozen=True)
class Actor: type: Literal["user", "service", "system"]; id: str; role: str = ""; team_id: str = ""

def canonical(obj: Mapping[str, object]) -> bytes: ...
def record_hash(body: Mapping[str, object]) -> str: ...              # section 7.3
def merkle_root(leaf_hashes: Sequence[bytes]) -> bytes: ...          # section 7.3
def append(conn: psycopg.Connection, *, actor: Actor, action: str, target_type: str, target_id: str,
           outcome: Outcome, ip: str = "", request_id: str = "", detail: Mapping[str, object] | None = None) -> int: ...
           # returns seq; raises ValueError on unknown action or forbidden value type; section 7.4

# abh_core/settings.py   typed settings object reading the variables of section 9
# abh_core/db.py         connection pool factory; no ORM; SQL lives next to the code that uses it
```

## 11. Makefile targets (names fixed so every agent and CI call the same thing)

| Target | Does | Must finish in |
| --- | --- | --- |
| `make preflight` | Runs `host/preflight.sh`, writes `evidence/preflight.md` | 1 min |
| `make secrets` | Generates database role passwords, the 32-byte notary seed and its public key file under `./secrets/` | |
| `make up` / `make down` | Starts or stops the stack | |
| `make check-fast` | ruff, mypy strict, TypeScript `tsc --noEmit`, unit tests, placeholder scan | 90 s |
| `make test-contract` | Vectors on core and on verifier, RBAC matrix, OpenAPI drift, Schemathesis | 5 min |
| `make test-security` | Isolation, resource, audit tamper, monitoring scope tests against the running stack | 10 min |
| `make test-e2e` | Browser journey of the demo script | 5 min |
| `make scan` | Docker Bench, Trivy, Semgrep, gitleaks, ZAP baseline into `evidence/scans/` | 15 min |
| `make openapi` | Regenerates `contracts/openapi.yaml` from the API | |
| `make evidence` | Collects reports, versions and standards mapping into `evidence/` | |
| `make demo-reset` | Clean database, seed two teams and seven users, pre-pull check | 2 min |
| `make tamper-drill CASE=<name>` | Applies one tamper case to the live database as superuser; refuses unless `ABH_ALLOW_TAMPER_DRILL=1` | |
