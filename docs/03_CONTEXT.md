# 03 · Context: problem, threat model, decisions, compatibility, limits

Project codename: **ABHEDYA** (rename freely; the prefix `abh` in identifiers stays).
Sources for every external fact are listed by number in `SOURCES.md`, cited here as [S#].

## 1. Problem statement (verbatim from the SFIC portal, PS0001, Track 2: Open Innovation)

**Title:** Design and Development of a Secure, Isolated and Auditable Cybersecurity Testing Platform

**Exact problem specification:** To develop a secure and isolated cybersecurity testing platform that allows
multiple users or teams to test applications, suspicious files, and AI systems without affecting production
systems or exposing confidential data. The platform should provide proper access control, prevent interference
between testing environments, monitor activities in real time, manage system resources, and detect unauthorized
modifications to audit logs.

**Expected outcomes and deliverables (the eight the jury will tick):**
1. A functional cybersecurity testing platform with isolated testing environments.
2. Secure user login and role-based access control.
3. Separate environments for different users or teams.
4. Real-time monitoring of user and system activities.
5. Resource management for CPU, RAM, and storage.
6. Centralized audit logs to record security activities.
7. Tamper detection to identify unauthorized changes in audit records.
8. An admin dashboard to manage users, environments, and security activities.

**Stakeholders:** cybersecurity teams, ethical hackers, security researchers, IT administrators.

**Team:** TM005136, MBIT. Mentor: Prof. Sunit Parmar. Three builders, each with a Claude coding agent:
Parth (role B, isolation engine, demo host), Henil (role A, identity, API, ledger) and Bhavya (role C,
console, verifier, proof). Machines and the reason for each assignment: `02_MASTER_PLAN.md` section 3.

## 2. Dates (verify with the organisers today)

- The official schedule page lists the finale, described as intensive prototype building and jury
  demonstrations at Mahatma Mandir, Gandhinagar, on **27 November 2026**, and finalist declaration on 24 November [S1].
- The portal's student manual PDF lists the grand finale on **2 December 2026** instead [S2].
- The plan in `02_MASTER_PLAN.md` assumes 27 November, the earlier date. If the later date is confirmed,
  keep the same gates and spend the extra days on stretch objectives S1 to S8, in that order.
- Read again on 25 November: the schedule page still shows the finale on 27.11.2026, described as "Intensive
  Prototype Building & Jury Demonstrations", and the home page says the result for SFIC Gujarat has been
  declared [S1]. Check that TM005136 is on the finalist list and ask for the reporting time.
- Scoring: the Gujarat portal pages read publish no rubric. The national Seva First Innovation Challenge site
  lists six common criteria: problem clarity, originality, demonstrated feasibility, cost, beneficiary impact,
  scalability [S57]. `13_DEMO_AND_EVIDENCE.md` section 6 prepares one answer for each.

## 3. Threat model

### 3.1 Assets
A1 host and control plane · A2 each team's sandbox contents, job output and uploaded files ·
A3 user credentials and sessions · A4 the audit ledger and its signing key · A5 shared CPU, memory, storage.

### 3.2 Attackers and the boundary that stops each

| ID | Attacker | Goal | Stopping boundary | Proof |
| --- | --- | --- | --- | --- |
| TA1 | Code running inside a sandbox (malware sample, exploited target app, hostile user) | Reach the host kernel, the control plane, the internet or another sandbox | gVisor application kernel, per-environment internal network with no gateway address, dropped capabilities, read-only root | T-ISO-01 to T-ISO-07 |
| TA2 | Authenticated user of team X | Read or control team Y's environments, jobs, events | Team scope check on every object route, scoped event stream | T-RBAC matrix, T-ISO-05, T-MON-03 |
| TA3 | Any tenant | Starve others of CPU, memory, processes, storage | cgroup limits per environment, quota admission, TTL reaper | T-RES-01 to T-RES-06 |
| TA4 | Anonymous network caller | Guess passwords, hijack sessions, forge requests | Argon2id, lockout, opaque sessions, cookie flags, CSRF token | T-AUTH-01 to T-AUTH-05 |
| TA5 | Insider with database write access, including the platform admin | Edit, delete, reorder or truncate audit records unnoticed, even by recomputing hashes | Append-only grants and triggers (prevention), hash chain (detection), Ed25519-signed Merkle checkpoints with a witness copy outside the database (proof) | T-AUD-03 to T-AUD-05 |
| TA6 | Platform admin | Read a team's confidential test data | Admin and auditor have no exec and no job-output permission (rules R17 to R21) | T-RBAC matrix |

### 3.3 Trusted computing base (say this to the jury)
The host kernel, Docker Engine, the runner service (it holds the Docker socket; Docker's documentation says the daemon runs as root and only trusted users should control it [S7]),
the notary's private key, and the physical machine. Compromise of any of these is out of scope for detection
inside the platform, except that audit tampering is still caught by anyone holding an older witness copy.

### 3.4 Stated limits (do not hide these)
L1. gVisor does not protect against hardware side channels [S4].
L2. gVisor runs Linux ELF binaries only [S5], so Windows malware cannot be detonated. File analysis covers
    static triage of any file and dynamic runs of Linux executables and scripts.
L3. An attacker holding a runtime database role can append false records. The ledger detects modification,
    deletion, reordering and truncation of existing records. It cannot stop junk being logged, a limit the
    tamper-evident logging literature states too [S16].
L4. Records newer than the last signed checkpoint can be truncated without cryptographic proof. The window is
    at most 30 seconds or 20 records.
L5. Verification recomputes the whole tree, which is linear in log size. Consistency proofs [S15] are the
    scaling path and are not built.
L6. One host, no high availability. The reconciler design allows more runners later.
L7. Workspace storage and uploaded samples are not encrypted at rest in the prototype.
L8. A `clean` verdict is not a statement that a file is safe. Detonation lasts at most 120 seconds, runs Linux
    programs only, and a sample can stay dormant or behave differently when it detects a sandbox. The two-minute
    window follows a published recommendation for behavioural reports [S54]; it does not remove the limit.
L9. AI scan results are scanner-flagged, not ground truth. A 2026 preprint found that garak's verdicts changed
    with the evaluator in 22 of 25 attack categories, and that reported success rates varied by up to 33 % [S53].
    We therefore claim only the difference between the vulnerable and the guarded target (T-WL-03).
L10. The witness copy of the checkpoints is kept by the same operator as the log. In transparency-log practice
    witnesses are independent parties that cosign a checkpoint only after checking consistency [S52]. Someone
    who controls the database, the witness volume and the signing key can rewrite history. Stretch S3
    (external anchor) is the fix.

## 4. Architecture decisions with the facts they rest on

**D1. Sandbox runtime: gVisor `runsc` under Docker Engine. Mandatory.**
Three runc container-breakout CVEs (CVE-2025-31133, CVE-2025-52565, CVE-2025-52881) were disclosed in
November 2025 [S8], and gVisor's own documentation says plainly that containers sharing the host kernel are
not a sandbox for untrusted code [S6]. gVisor intercepts every application system call in a user-space
kernel and passes none through directly to the host [S4]. It installs as a Docker runtime with
`runsc install` and runs with `docker run --runtime=runsc` [S3]. Firecracker or Kata microVMs were rejected
for the prototype because they need KVM, which a rented or nested VM may not expose.
Precedent: gVisor runs millions of sandboxes a day under Google's GKE Sandbox, Cloud Run and App Engine [S47],
and the UK AI Security Institute uses gVisor for most of its agentic AI evaluations [S49]. A precedent
justifies the choice; only our own T-ISO tests say anything about our build.

**D2. Host: native Linux or a Linux virtual machine, x86_64. Never WSL, never Docker Desktop.**
gVisor requires Linux and supports x86_64 and ARM64 [S5]. A gVisor maintainer describes running it inside WSL 1
or 2 as "very much unsupported" and recommends a standalone VM on Windows hosts [S9]. The default `systrap`
platform is the documented choice inside a VM or on machines without virtualization support, and KVM is
fastest on bare metal [S10]. Current team assignment: Ubuntu Server LTS in a VMware Workstation or VirtualBox
virtual machine on Manas's Ryzen 9/32 GB laptop, with `systrap`; Parth's 24 GB laptop may host a cold backup VM.
Only one stack is active at a time. Henil and Bhavya may use WSL 2 for their own code, because nothing they run
there starts a sandbox; no `runsc` result obtained in WSL counts.
Steps per machine are in `team/<name>/01_DEVICE_SETUP.md`.

**D3. Resource limits live on the host cgroup, one sandbox per container.**
gVisor relies on host cgroups against resource exhaustion and cannot enforce limits between processes inside
one sandbox [S4][S11]. Docker sets them with `--cpus`, `--memory`, `--pids-limit` [S12]. Consequence: never put
two tenants in one sandbox, and read memory from the cgroup total, because gVisor application memory is
accounted as shared memory, not anonymous memory [S13]. Firecracker's authors give the same reason for
enforcing limits from outside: they do not trust the guest to implement its own limits [S48].

**D4. Storage quota: a size-capped volume per environment, proven by a write-until-full test.**
Docker's `--storage-opt size=` is available only for the `btrfs`, `overlay2`, `windowsfilter` and `zfs` storage
drivers, and on `overlay2` only when the backing filesystem is xfs mounted with `pquota` [S12]. We do not assume
the demo host meets that condition (preflight records the storage driver and backing filesystem), so choosing a
capped volume instead is our design decision, not something the Docker page prescribes. The local volume driver accepts mount-style options, for
example a tmpfs volume with `o=size=100m` [S14]. Decision ladder in `08_TECHNICAL_IMPLEMENTATION.md` section 4.

**D5. Network: one internal bridge network per environment with gateway mode `isolated`.**
Containers on different bridge networks cannot talk to each other except through published ports [S17].
An `--internal` network has no default route out [S41], but by default its bridge still has an address, so containers can
reach host services listening on that address or on `0.0.0.0`. Gateway mode `isolated` removes the bridge
address and is only allowed together with `--internal` [S18]. Without this, a sandbox could reach the
platform's own database or API through the gateway address.

**D6. Monitoring reads the container engine, not an in-sandbox agent.**
Docker exposes a live event stream (`GET /events`, filterable by label and type) and per-container resource
statistics (`GET /containers/{id}/stats`) [S19]. Falco's gVisor engine was removed in Falco 0.44.0 (26 May 2026)
[S20]. That source states only the removal; leaving Falco out and reading Docker events and statistics instead is
our design decision. gVisor's own runtime monitoring, which streams trace points for system calls to
an external process [S21], is stretch objective S5. KYPO's designers drew the same line: monitoring whose
consumer is outside the exercise must be protected from manipulation by participants [S44].

**D7. Audit ledger: hash chain plus RFC 6962 Merkle root plus Ed25519-signed checkpoints plus witness copy.**
RFC 6962 defines the leaf hash as SHA-256(0x00 || entry) and node hash as SHA-256(0x01 || left || right); the
different prefixes give second-preimage resistance [S15]. RFC 6962 also has the log sign its tree root (the
Signed Tree Head, section 3.5) [S15], which is the model for our signed checkpoint. RFC 6962 is cited only for
the Merkle tree hash and that signing pattern; the per-record hash chain (`prev_hash`), the Ed25519 signature
and the witness file are this project's design choices. NIST SP 800-53 AU-9 requires protecting audit
information from unauthorized modification and deletion, AU-9(3) asks for cryptographic integrity mechanisms and
names signed hashes with asymmetric keys, and AU-10 is non-repudiation [S22]. Crosby and Wallach frame the goal:
the logger must prove that events are still present and that the log now is consistent with how it was seen
before [S16]. Canonical bytes use sorted-key compact JSON restricted to strings, integers, booleans, objects and
arrays; RFC 8785 is the general standard for that problem [S23].
Production precedents for the pattern: AWS CloudTrail hashes every log file, signs an hourly digest, chains each
digest to the previous one, keeps digests apart from the logs and ships a command-line validator [S51];
Certificate Transparency logs built on Trillian, and Sigstore's Rekor, sign Merkle tree heads, which Rekor
calls checkpoints [S52]. Our witness differs from theirs in one important way (limit L10).

**D8. Identity: Argon2id, opaque server-side sessions in cookies, CSRF token.**
OWASP's minimum Argon2id setting is m=19456 KiB, t=2, p=1 [S24]. Session cookies must be HttpOnly and set
SameSite=Strict (preferred) or Lax, and SameSite is defense in depth, not a replacement for a CSRF token [S25].
ASVS 5.0 requires reference session tokens from a CSPRNG with at least 128 bits of entropy (7.2.3) and
function-level access restricted to explicit permissions (8.2.1) [S26]. JWTs were rejected: revocation on
logout or disable needs server state anyway.

**D9. Control plane split by privilege.** API (no Docker access) · runner (Docker socket, no inbound network) ·
notary (read-only ledger access plus the signing key) · PostgreSQL · reverse proxy. API and runner communicate
only through database rows (desired state and observed state), so there is no network API to attack between them.

**D10. File triage with YARA-X, AI probing with garak.**
YARA-X scans a file with rule files through `yr scan <RULES_PATH> <TARGET_PATH>` [S27]. garak runs probes
against a target through generators, including a generic REST generator, and ships offline test generators
(`test.Blank`, `test.Repeat`) for smoke runs; it writes a `report.jsonl` [S28]. Findings map to the OWASP Top 10
for LLM Applications 2025, where LLM01 is prompt injection [S29]. garak option names have changed between
releases (documentation shows both `--model_name` and `--target_name` forms), so the agent must read
`garak --help` of the installed version.
Two research findings limit what we may claim. A 2026 preprint found garak's verdicts unstable across
evaluators [S53] (limit L9), so reports say "scanner-flagged". An NDSS 2021 study of sandbox run times
recommends two minutes when the goal is a behavioural report [S54], so the detonation deadline is 120 seconds
(limit L8). Malware sandboxes such as CAPE default to no network routing for an analysis [S50], as we do.

**D11. Indian compliance hook.** CERT-In's Directions of 28 April 2022 require enabling logs of all ICT
systems, keeping them securely for a rolling 180 days within Indian jurisdiction, and synchronising clocks
with NIC or NPL NTP servers or servers traceable to them [S30]. The ledger's retention setting defaults to
180 days and the host runs an NTP client. Whether the Directions bind a given deployment is a legal question
this document does not answer.

**D12. Every template carries an isolation profile in the UK AI Security Institute's notation.**
The institute classifies a sandbox on three independent axes: tooling (T0 is unrestricted execution inside the
sandbox), host (H1 is an ordinary container sharing the host kernel, H2 is a shared host with stronger
container isolation such as gVisor, H3 is a full virtual machine) and network (N2 is no external network at
all) [S49]. All three of our templates run at `T0.H2.N2`; degraded mode is `T0.H1.N2`. The profile is written
at the start of each template's `description` text, so no contract field changes, and is shown in the
environment badge tooltip. Placing Docker with gVisor in tier H2 is our reading of their definition, not a
certification by them.

## 5. Compatibility matrix (checked by `make preflight`, see `08` section 1)

| Factor | Requirement | Why | If it fails |
| --- | --- | --- | --- |
| Host OS | Linux x86_64, native or full VM | D2 | Stop. Build a VM. |
| Docker | Docker Engine from Docker's own repository, not Docker Desktop, not snap | runtime registration, gateway modes | Reinstall |
| runsc | `docker run --rm --runtime=runsc hello-world` exits 0 | D1 | Fix before any feature work |
| cgroups | v2 unified hierarchy (`docker info` shows Cgroup Version: 2) | D3 | Record and test limits explicitly |
| Network | `docker network create --internal -o com.docker.network.bridge.gateway_mode_ipv4=isolated` accepted | D5 | Use `--internal` plus host firewall rule, T-ISO-04 must still pass |
| CPU / RAM of the demo VM | Minimum 4 cores and 8 GB. On Parth's Omen: 6 virtual CPUs and 12 GB, which by the admission rule of `04` section 4 admits 10 size-S environments at once ((6000 - 1000) / 500). The 4-core, 8 GB backup on Henil's Legion admits 6 ((4000 - 1000) / 500). Memory is not the binding limit in either case | calculation from contract numbers, confirm with T-RES | Reduce default quotas |
| Hypervisor on Windows | VMware Workstation Pro, free for commercial, educational and personal use [S58], or VirtualBox. A green turtle icon in VirtualBox means a native hypervisor such as Hyper-V is running on the host, and users report degraded speed in that mode [S58] | D2 | Use the other hypervisor, or accept the speed and re-run the T-RES tests |
| Guest OS | Ubuntu Server 24.04 LTS, 64-bit; Docker Engine lists 24.04 and 26.04 LTS as supported [S58] | Docker and gVisor install paths | Use 26.04 LTS and record it |
| Developer machines of A and C | Windows 11 with WSL 2, which is available on Home editions [S59]; repository inside the Linux file system, not under `/mnt/c` [S59]; the agent needs 4 GB of RAM or more [S60] | fast file access, `make` available | Work over SSH inside the demo VM |
| GPU | Not required by any mandatory objective | scope | none |
| Venue | No internet assumed | on-site demo | All images pre-pulled, all rule files and packages baked into images |
| Browser | Current Chrome or Firefox | EventSource, WebCrypto | none |

## 6. Dependency allowlist (a lead, not a fact: verify each on its registry before installing)

Backend: `fastapi`, `uvicorn`, `psycopg` (with `binary` and `pool` extras), `pydantic`, `pydantic-settings`,
`argon2-cffi`, `cryptography`, `python-multipart`, `pyyaml`. Runner adds `docker`. Tests: `pytest`,
`hypothesis`, `schemathesis`, `httpx`. Lint and types: `ruff`, `mypy`.
Frontend: `react`, `react-dom`, `react-router-dom`, `@tanstack/react-query`, one chart library, `tailwindcss`,
`vite`, `typescript`, `vitest`, `openapi-typescript`, `@playwright/test`. Stretch S2 adds `@xterm/xterm`.
Sandbox images: `yara-x`, `garak`.
Anything else needs a change request. No ORM, no task queue, no message broker, no Kubernetes.

## 7. Glossary
**Environment (env):** one team's isolated set of containers on its own network. **Sandbox:** one container
run by `runsc`. **Template:** an allowlisted recipe of images for an environment. **Job:** a command, file
analysis or AI scan executed inside an environment. **Ledger:** the audit log. **Checkpoint:** a signed
statement of the ledger's size and Merkle root. **Witness:** a copy of checkpoints kept outside the database.
**Notary:** the service that signs checkpoints. **Runner:** the service that turns desired state into containers.
