# 02 · Master plan

## 1. Mission in one sentence
Ship a small platform where the jury can watch a hostile tenant fail to escape, fail to reach another team,
fail to starve the host, and fail to alter the audit log unnoticed, and where each of the eight listed
deliverables is backed by a test that somebody outside the team can run.

## 2. Architecture

```
 Browser (console, EventSource)
        | HTTPS 443
   +----v----+        edge network
   |  proxy  |  TLS, static files
   +----+----+
        |                      control network (internal)
   +----v----+   rows    +-----------+   rows    +----------+
   |   api   +---------->| PostgreSQL|<----------+  runner  +--- Docker socket
   | (A)     |<--NOTIFY--+  ledger,  +--NOTIFY-->|  (B)     |
   +---------+           |  state    |           +----+-----+
                         +-----^-----+                |  creates, limits, watches, destroys
   +---------+   read          |                      v
   | notary  +-----------------+        +-------------------------------+
   | (A)     |  signs checkpoints       | per-environment internal net  |
   +----+----+                          |  [runsc sandbox] [runsc ...]  |  one per env, no gateway
        | witness file (outside DB)     +-------------------------------+
        v
   tools/verify_audit.py (C)  independent, runs anywhere, also on the jury's laptop
```

Design rules that keep the code small:
1. **Reconciler, not RPC.** The API writes `desired_state`; the runner makes reality match and writes
   `observed_state`. No service calls another over HTTP.
2. **One write path for audit**, `abh_core.audit.append`, inside the caller's transaction.
3. **One authorization source**, `rbac_matrix.yaml`, loaded by a single dependency in the API.
4. **One sandbox primitive.** Applications, file analysis and AI scans are templates over the same hardened
   container launch function.
5. **No feature without its test ID** in `06_VERIFICATION.md`.

## 3. Ownership

| Member | Owns | Directories | Objectives led |
| --- | --- | --- | --- |
| **A · Henil · Identity, API, quota and ledger** | Login, sessions, RBAC engine, API routes, quota admission, audit append, notary | `core/`, `services/api/`, `services/notary/`, their unit tests | O2, O6, O7 ledger side; API/data sides of O3/O4/O5/O8 |
| **B · Parth · Isolation engine and workloads** | Host scripts, runner, sandbox profile, networks, limits, storage, collectors and three templates | `host/`, `services/runner/`, `sandbox/`, runner unit tests | O1, O3 runtime, O4 collection, O5 limits, O9 |
| **C · Bhavya · Console, independent verifier and tests** | Console, independent verifier, contract/security/e2e suites, scanners and evidence | `web/`, `tools/verify_audit.py`, `tests/contract/`, `tests/security/`, `tests/e2e/`, `evidence/` | O8, O7 verifier side, O4 display, independent proof |
| **D · Manas · Maintainer, integration and release owner** | Branch setup, build wiring, CI, primary host, gate coordination, PR review and release | `Makefile`, `compose.yaml`, `.github/`, `db/init/`, `team/manas/`, integration/release docs | Cross-objective integration and G0–G4; sole promotion to `main` |

Role letters A/B/C already appear in frozen contracts and tests and remain unchanged. Manas is role D for the new
maintainer/integration responsibility, not a new API role. Exact file boundaries and review duties are in
`docs/TEAM_OWNERSHIP_AND_BRANCHING.md`.

**Hardware assignment.** Manas's Ryzen 9 9955HX / RTX 5070 Ti 12 GB / 32 GB laptop hosts the primary Ubuntu VM,
initially preserving the documented 6-vCPU/12-GB baseline. Parth's i7 HX / RTX 5050 8 GB / 24 GB laptop is the
cold backup host and runtime development system. Henil's Ryzen 7 260 / RTX 5050 8 GB / 16 GB and Bhavya's Ryzen 7 /
RTX 3050 / 16 GB laptops are WSL development machines. Stack-dependent checks run on Manas's primary VM. GPU
hardware is not required for mandatory objectives.

## 4. Gates (a gate passes only when every listed command exits 0 on the demo host)

| Gate | Target time after start (T0) | Exit criteria |
| --- | --- | --- |
| **G0 Contracts and host** | T0 + 2 h | `make preflight` passes (runsc hello-world, isolated network, storage method chosen). `contracts/schema.sql` applied on the real PostgreSQL. `make check-fast` runs. `contracts/openapi.yaml` generated from route stubs and committed. All four have read `03` and `04` and signed the freeze line in `09`. |
| **G1 Walking skeleton** | T0 + 8 h | Through the browser: log in, create an S `app-target` environment, see it reach `running` with tier `gvisor`, see one metric sample, see the audit records. `tools/verify_audit.py` returns OK on a live export. T-KAT-01 to T-KAT-04, T-ISO-01 green. |
| **G2 All deliverables** | T0 + 18 h | O1 to O9 work on the happy path. `make test-contract` green. |
| **G3 Proof** | T0 + 26 h | `make test-security` green. `make scan` run and triaged. Ten tamper cases detected with the expected verdicts. Outsider break-it session held and logged. |
| **G4 Demo freeze** | T0 + 32 h | Tag `demo-v1`. `make demo-reset` then the script in `13_DEMO_AND_EVIDENCE.md` rehearsed twice with networking off. Backup screen recording made. `make evidence` output committed. |

After G4 only two kinds of change are allowed: a fix that starts with a failing test, and a stretch objective
behind a flag that defaults to off.

### Historical schedule assumption (written 25 November 2026; verify before using)

The schedule below is retained as source planning context, not as a current commitment. Its T0 and dated tripwires
have passed or may not match the confirmed event date. Manas must publish a fresh team schedule after verifying the
event date, available working hours, and machine/network readiness. Gate exit criteria remain useful until superseded
by an approved change request.

Start (T0) is 25 November 19:00. That leaves about 28 clock hours and 23 working hours before the demo freeze,
against a gate plan first written for 32. The gate targets in the table above therefore give way to the clock
times below, and the plan only fits if the tripwires are obeyed.

| When (IST) | Block |
| --- | --- |
| 25 Nov 18:00 to 19:00 | Before T0. Parth starts the Ubuntu download and VM creation (`team/parth/01_DEVICE_SETUP.md`), the longest single wait. Henil and Bhavya set up WSL 2 and their tools. One person confirms the finale date and that TM005136 is on the finalist list (risk R-27). |
| 25 Nov 19:00 to 21:30 | G0. Read `03` and `04` together for 30 minutes. Parth: B0 on the VM. Bhavya: C0. Henil: A0 once the scaffold is pushed. |
| 25 Nov 21:30 to 26 Nov 02:00 | Toward G1. Henil: A1, A2. Parth: B1, B2. Bhavya: C1, then C2. |
| 26 Nov 02:00 to 07:30 | Sleep. Tired people accept wrong agent output. |
| 26 Nov 07:30 to 09:00 | G1 check on the demo VM. **Tripwire 1.** |
| 26 Nov 09:00 to 16:00 | G2. Henil: A3 to A6. Parth: B3 to B7. Bhavya: C3 to C6. **Tripwire 2 at 13:00.** |
| 26 Nov 16:00 to 20:30 | G3. Bhavya leads C7. Henil and Parth fix only what tests expose. Break-it session with the mentor or another team at 18:00. |
| 26 Nov 20:30 to 23:30 | G4. Rehearse twice offline, record the backup video, export the VM to Henil's laptop, pack hardware. **Tripwire 3.** |
| 27 Nov | On site. Stretch items only if G4 passed. Otherwise finish the highest unmet objective. |

**Tripwires (decide by the clock, not by hope).**
1. 26 Nov 09:00 and G1 has not passed: apply cuts 1, 2 and 4 of section 5 at once, and Bhavya stops console
   polish to help whoever is blocking G1.
2. 26 Nov 13:00 and fewer than six of O1 to O9 work on the happy path: apply cuts 3, 5 and 6.
3. 26 Nov 20:30 and G3 has not passed: freeze features anyway. A smaller system that passes its tests in front
   of the jury beats a larger one that fails.

If the finale is confirmed for 2 December instead, keep the same order, sleep properly, and use the extra days
for a second break-it session and stretch objectives S1 to S8 in that order.

## 5. Order of cuts when a gate slips (cut from the top; never from the bottom list)
Cut first: 1. S1 to S8 stretch objectives · 2. `ai_scan` probe set `full` (keep `quick`) · 3. `stub-guarded`
target (keep `stub-vulnerable`) · 4. console charts (keep numbers) · 5. file detonation (keep static triage)
· 6. `alert.cpu_saturated` and `alert.storage_high`.

**Never cut:** runsc isolation with T-ISO tests · the RBAC matrix tests · memory, process and storage limit
tests · signed checkpoints, the independent verifier and the tamper drills · the live event stream ·
the admin console pages for users, environments and audit.

## 6. Working agreements
- **Branches:** use `work/manas`, `work/parth`, `work/henil`, `work/bhavya`; every PR targets `integration`.
  Manas alone merges contributor PRs into `integration` and alone promotes `integration` into `main`. No direct
  commits or merges to shared branches. Configure remote branch protection when a remote exists.
- **Commits:** `<objective or test id>: <what changed>`, for example `O5/T-RES-03: cap workspace volume`.
- **One agent session per prompt.** Start a fresh session for each prompt in your member file. Long sessions
  that mix tasks carry stale assumptions and cost more.
- **Evidence rule:** a task is done when its "done when" commands were run and their output pasted in the
  hand-off note. "Should work" is not a state.
- **Stuck rule:** 20 minutes without progress means stop, write a bug journal entry, ask a teammate.
- **Contract rule:** disagreement with a contract is a change request, never a local workaround.
- **Sync:** ten minutes at each gate. Each owner states: owned objectives green/red, evidence location, blocker, and exact handoff needed.

## 7. How the files are used

| File | Who reads it | When |
| --- | --- | --- |
| `CLAUDE.md` | every agent, automatically | every session |
| `03_CONTEXT.md`, `04_CONTRACTS.md` | every agent | first prompt, and whenever a prompt names a section |
| `05_OBJECTIVES.md`, `06_VERIFICATION.md` | every agent | to find acceptance tests for the task in hand |
| `07_ANTI_HALLUCINATION.md` | every human once; agents get its rules through `CLAUDE.md` and the prompts | start |
| `08_TECHNICAL_IMPLEMENTATION.md` | the owner of the section | per task |
| `team/<name>/` | that member | start with `00_START_HERE.md`; paste prompts from `02_PROMPTS.md` in order; write only in `work/` |
| `14_PRIOR_ART.md` | every human once; agents when a prompt cites a precedent | before G0 |
| `09_BUG_JOURNAL.md` | humans, for the freeze sign-off, new risks and change requests | at G0 and on every change request |
| `team/<name>/work/JOURNAL.md` | that member and their agent | on every failure longer than 20 minutes |
| `13_DEMO_AND_EVIDENCE.md` | C leads, all rehearse | G3 onward |
