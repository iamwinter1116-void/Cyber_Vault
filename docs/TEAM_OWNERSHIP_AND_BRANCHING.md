# ABHEDYA team ownership and branch workflow

Version: 1.0 · Applies to the four-person build team · Maintainer: Manas

This is the current operating agreement for task ownership, file boundaries, reviews, and branch movement.
It supersedes the older three-person assignment tables in the v2 instruction pack where they conflict.
The machine-readable contracts remain frozen and authoritative; this document does not change them.

## 1. Current repository state

The folder began as an instruction pack, contracts, and project documentation. The `core/`, `services/`, `web/`,
`host/`, `sandbox/`, `tests/`, and deployment implementation described in those documents are not present yet.
The four new specification documents under `docs/specs/` are completed planning artifacts, not executable code.
Create implementation files only after the initial shared repository commit and branch setup described below.

The shared remote is `https://github.com/iamwinter1116-void/Cyber_Vault`. It was inspected as a private empty repository;
the connected GitHub account has write permission but not admin permission. Branches can be created and pushed, but
remote branch-protection rules may require the repository owner/admin. Do not call the Manas-only merge rule enforced
until the `main` and `integration` rules are visible in GitHub settings.

## 2. Team, role, and primary responsibility

| Person | Project role | Primary ownership | Owns outcome slice | Machine use |
| --- | --- | --- | --- | --- |
| Manas | D · maintainer, integration and release owner | `Makefile`, `compose.yaml`, `.github/`, `db/init/`, `team/manas/`, merge queue | G0–G4 coordination, cross-service integration, release readiness and demo-host operation | Primary Ubuntu VM on the 32 GB laptop; 6 vCPU, 12 GB guest RAM, 80 GB disk unless preflight evidence justifies an agreed change |
| Parth | B · isolation engine and workload runtime | `host/`, `services/runner/`, `sandbox/`, runner unit tests | O1, O5, O9; runtime side of O3 and collection side of O4 | Develop on his laptop; all `runsc` checks on Manas's primary VM. Keep a prepared 4-vCPU/8-GB backup VM if practical |
| Henil | A · identity, API, quota and audit services | `core/abh_core/`, `services/api/`, `services/notary/`, their unit tests | O2, O6, O7 ledger side; API/quota sides of O3, O4, O5 and O8 | WSL 2 on the 16 GB Lenovo for code and unit tests; full stack checks on Manas's primary VM |
| Bhavya | C · console, independent verifier and test author | `web/`, `tools/verify_audit.py`, `tests/contract/`, `tests/security/`, `tests/e2e/`, `evidence/` | O8, O7 verifier side, display side of O4, contract/security/e2e proof | WSL 2 on the 16 GB Ryzen 7 laptop for editing and light checks; stack-dependent tests on Manas's primary VM |

The GPU is not needed for any mandatory objective. The AI workload uses the offline stub target and the agreed
probe set. Do not add a model download, GPU service, network exception, or GPU-dependent mandatory test.
Any real model/GPU experiment belongs to stretch S8 after G4, behind its flag, with its isolation effects tested.

## 3. Exact directory ownership

The owner listed below is the only person who directly edits implementation files in that area. Other people
may review, comment, file issues, and propose patches on their own branch; the owner applies requested edits.
Manas is the only person who merges any contributor branch into `integration` or promotes `integration` to `main`.

| Path | Direct editor | Reviewer / integration boundary |
| --- | --- | --- |
| `core/abh_core/`, `services/api/`, `services/notary/` | Henil | Parth reviews shared audit/API interface; Bhavya reviews contract behavior; Manas merges |
| `services/runner/`, `host/`, `sandbox/` | Parth | Henil reviews DB-row/audit interface; Bhavya reviews probe/test interface; Manas merges |
| `web/`, `tools/verify_audit.py`, `tests/contract/`, `tests/security/`, `tests/e2e/`, `evidence/` | Bhavya | Henil reviews API shapes; Parth reviews runtime assumptions; Manas merges |
| `Makefile`, `compose.yaml`, `.github/`, `db/init/` | Manas | Each service owner reviews their service wiring; Manas merges and owns final integration |
| `contracts/` | Frozen; no direct editor | Any proposed change is a CR in `docs/09_BUG_JOURNAL.md`, approved by all four people, then implemented by Manas in one coordinated change |
| `docs/` outside the four new specifications | Frozen/shared truth | Change only through a documented CR or explicit team decision recorded in the bug journal |
| `docs/specs/` | Frozen shared specifications | A subject-matter owner raises a CR with evidence; all four approve; Manas applies the agreed edit under the shared-document change process |
| `team/<person>/work/` | That person only | Journals and handoffs are append-only per person; do not edit another person's work notes |
| `team/<person>/` setup/prompts/objective files | Frozen role instructions | Manas may update assignment text after agreement; contributors do not self-edit role boundaries |

### File boundary rules

1. A branch change should stay inside its owner's paths plus its own `team/<person>/work/` notes.
2. If one feature genuinely requires another owner's path, open a small integration request naming the exact files and why.
3. The owner of each path makes the code edit. If work must be paired, name one driver; the other person reviews.
4. No shared contract, security test, RBAC rule, schema, or audit vector is changed as a local workaround.
5. A change request lists affected objectives, tests, owners, migration/compatibility effects, and sign-offs.
6. `Makefile`, `compose.yaml`, and CI changes are Manas-owned; feature owners provide a patch proposal or exact service requirements.
7. Bhavya owns independent tests and verifier code. Henil and Parth must not weaken, delete, skip, or mock those tests.
8. Manas owns integration, but does not silently rewrite another person's feature implementation. Feedback goes to its owner.
9. Secrets, private keys, generated password files, local `.env` files, and live user data never enter branches or PRs.
10. Shared interface conflict is resolved by reading `contracts/` first; the contract wins unless all four approve a CR.

## 4. Objective ownership and handoffs

| Objective | Accountable lead | Contributors | Required handoff / proof |
| --- | --- | --- | --- |
| O1 isolated testing environments | Parth | Manas provides host/compose integration; Bhavya provides isolation tests; Henil provides environment API rows | `runsc` profile inspection, isolation probes, environment create-to-running browser flow |
| O2 secure login and RBAC | Henil | Bhavya authors generated role/scope tests; Manas wires services; Parth consumes runner identity fields only | Argon2id/session/CSRF/lockout evidence; every R01–R31 role case follows matrix |
| O3 team separation | Henil for API/data scope; Parth for network and volume boundary | Bhavya tests cross-team API and streams; Manas checks deployment networks | Cross-team lookups are 404 where specified; separate networks, volumes and event filtering |
| O4 live monitoring | Parth produces metrics/events; Henil implements scoped stream; Bhavya renders it | Manas wires the proxy and end-to-end stack | State, metrics, alerts and allowed audit stream meet exact latency and resume criteria |
| O5 resource management | Parth enforces sandbox limits and cleanup; Henil enforces team/host admission | Bhavya writes hostile resource tests; Manas supplies host capacity configuration | CPU, memory, pids, storage, quota, TTL, reaper, and neighbor tests pass |
| O6 centralized audit | Henil | Parth emits runner actions through shared append path; Bhavya verifies expected event coverage; Manas wires notary volumes | State change plus audit is atomic where contract requires; exactly one record for each applicable action |
| O7 tamper detection | Henil owns append/checkpoint/notary; Bhavya owns independent verifier and tamper tests | Manas wires witness persistence and demo export | Known-answer vectors, ten tamper cases, witness-backed verification, alert within 30 seconds |
| O8 admin dashboard | Bhavya | Henil provides endpoints; Manas provides compose/proxy/build integration | Overview, users/teams/quotas, environment usage/kill switch, activity, audit filter/export/verify |
| O9 three workload types | Parth | Henil provides job submission/API; Bhavya verifies UI and outcome rendering; Manas wires images/config | `app-target`, `file-analysis`, and offline `ai-redteam` run with the defined shapes and limits |

### Work order and gates

1. Manas initializes the repository, `integration`, owner branches, `Makefile`, `compose.yaml`, and CI skeleton.
2. Bhavya creates the contract-test harness and independent audit-vector test plan from frozen contracts.
3. Parth checks the Ubuntu `runsc` host preflight and reports the exact evidence before runtime implementation.
4. Henil implements the shared core audit and database interface first; Parth and the notary use that interface.
5. The four owners work in parallel only after each interface is named in a PR or contract comment approved by Manas.
6. At each gate Manas reports green/red objectives and names one blocking owner; other owners continue independent tasks.
7. Bhavya reports test evidence; feature owners report implementation evidence; Manas decides integration readiness from both.
8. After G4, only a fix tied to a failing test or an explicitly flagged stretch feature may enter the release branch.

## 5. Hardware and environment assignments

### Manas — primary host and maintainer

- Laptop: Ryzen 9 9955HX, RTX 5070 Ti 12 GB VRAM, 32 GB RAM.
- Prepare an Ubuntu Server 24.04 LTS VM for the only active demo stack. Preserve the existing reference size of
  6 virtual CPUs and 12 GB RAM until the team has measured the host and agreed to a change; leave resources for Windows.
- Own the VM snapshot, offline images/dependencies, TLS setup, `compose.yaml`, and primary demo stack lifecycle.
- Verify CPU, virtualization, free disk, host OS, hypervisor, networking, `runsc`, and available memory rather than
  assuming the model number guarantees a configuration.
- Do not use the RTX GPU for a mandatory workload. The required AI target remains the in-repository offline stub.
- Only Manas runs `make up`, `make down`, and `make demo-reset` on the primary Docker daemon.

### Parth — runtime engineer and backup host

- Laptop: i7 HX class CPU, RTX 5050 8 GB VRAM, 24 GB RAM.
- Own runner, gVisor launch path, host setup scripts, network isolation, limits, storage, lifecycle and all workload images.
- Develop on his normal Linux/WSL-compatible code environment, but every claim about gVisor, Docker, cgroups,
  network isolation, and container cleanup must be measured on Manas's real Ubuntu VM or an explicitly promoted backup VM.
- If backup-host readiness is required, prepare an Ubuntu VM no larger than 4 vCPU and 8 GB initially; do not run a
  second stack concurrently with Manas's primary stack. Manas explicitly announces a host handoff first.
- Keep GPU use out of the workload path; no device passthrough to a sandbox.

### Henil — API and ledger engineer

- Laptop: Ryzen 7 260 octa-core, RTX 5050 8 GB VRAM, 16 GB RAM.
- Use WSL 2 for Python, unit tests, schema inspection and code review; keep the clone in the Linux filesystem.
- Do not operate the primary Docker stack, the notary witness backup, or the demo host.
- Send any full-stack or runner-dependent verification command to Manas with exact expected output.

### Bhavya — UI, independent proof and test engineer

- Laptop: Ryzen 7, RTX 3050, 16 GB RAM.
- Use WSL 2 for frontend, verifier, contract tests, local type/lint checks and source review; keep the clone in the Linux filesystem.
- Do not operate Docker or edit backend/runner implementation directories.
- Run contract/security/e2e suites on the primary host under Manas's coordination; do not restart or reset the shared stack.

## 6. Branch model and merge authority

### Branches

| Branch | Purpose | Who writes directly | Who merges into it |
| --- | --- | --- | --- |
| `main` | Demoable, reviewed baseline and release tags | Nobody directly | Manas only, from `integration` |
| `integration` | Shared integration branch where all accepted work is assembled | Nobody directly | Manas only, from contributor branches |
| `work/manas` | Integration scaffolding, CI, compose, developer workflow and release preparation | Manas | Manas may merge it to `integration` after review checklist |
| `work/parth` | Runtime/isolation/workload implementation | Parth | Manas merges after Parth evidence and independent review |
| `work/henil` | Identity/API/quota/audit/notary implementation | Henil | Manas merges after Henil evidence and independent review |
| `work/bhavya` | UI/verifier/contract/security/e2e tests and evidence | Bhavya | Manas merges after Bhavya evidence and independent review |

The required route is `work/<owner>` → pull request → `integration` → pull request/release review → `main`.
No contributor pushes commits directly to `integration` or `main`. Do not merge another person's branch yourself.
Manas is the sole merger into `integration` and the sole person allowed to promote `integration` into `main`.

### Pull request checklist

Every PR states: owner, objective IDs, test IDs, exact paths changed, commands actually run, exit codes, concise output,
security/contract impact, and known limitations. A PR with a changed contract requires an approved CR linked in the body.
Before merging to `integration`, Manas confirms the PR is limited to the owner's paths, has an independent review,
does not weaken tests, does not include secrets, and has the required owner evidence. `make check-fast` must be green
when the scaffold exists. Runtime/security tests must be run on the primary VM and their output attached or linked.

Before promoting `integration` to `main`, Manas confirms all applicable gate commands are green on the primary VM,
the evidence pack is current, the branch contains no unreviewed direct commits, and the demo reset/rehearsal is complete.
Release tags are created from `main`, never a contributor branch.

### Conflict and emergency fix

If two owners need the same file, stop and assign one editor in a short issue/PR comment before editing. The second owner
supplies a patch suggestion or test. For a release blocker, Manas can ask the owner to make a narrowly scoped fix on that
owner's branch; Manas still performs the merge. Do not solve a conflict by copying someone else's unreviewed code into
your branch. Record the chosen resolution in the owning person's handoff and the PR.

## 7. Remote branch protection requirement

After Manas or the repository owner confirms the branch rules can be managed:

1. Set `origin` to the shared repository and push `main`, `integration`, and all four `work/*` branches.
2. Protect `main`: require pull requests, require Manas as the only person with merge permission, require CI, disallow force-push and deletion.
3. Protect `integration`: require pull requests and CI, and grant merge permission only to Manas.
4. Add Manas's GitHub account as the required code owner for `main`, `integration`, `.github/`, `compose.yaml`, and `Makefile`.
5. Keep contributors as branch writers without merge permission to the protected branches.
6. Confirm branch rules in repository settings; a local policy or local branch name alone cannot enforce permissions on a remote.

The connected account is `choksi2212`; confirm that this is Manas's GitHub identity before treating CODEOWNERS or
branch restriction lists as proof of personal authority. Repository owner/admin access remains required for settings.

## 8. Known state and next action

The instruction pack, frozen contracts, and planning documents exist. The product implementation is not present in this folder.
Do not describe the application as partly implemented until code and test evidence are visible on the shared branches.
The immediate sequence is: Manas initializes Git and the four-person branch structure; Manas creates the primary VM;
Parth runs host preflight; Bhavya and Henil prepare their owned test/API slices; then the four owners build through PRs.
