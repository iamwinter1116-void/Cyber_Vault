# 09 · Bug journal, risk register, change requests

This is the only file in `docs/` that changes during the build. Humans edit it (agents propose text in their
hand-off notes; a human pastes it). It has four parts: the freeze sign-off, risks found during research,
the bug journal, and change requests.

## Part 1 · Contract freeze (gate G0)
We have read `03_CONTEXT.md` and `04_CONTRACTS.md`, applied `contracts/schema.sql` on our PostgreSQL, and
accept the contracts as frozen.

| Member | Name | Date and time | Preflight evidence read |
| --- | --- | --- | --- |
| A | Henil | | |
| B | Parth | | |
| C | Bhavya | | |
| D | Manas | | |

Decisions taken at G0 (fill in from `evidence/preflight.md`):
hypervisor = VMware / VirtualBox · VM size = __ vCPU / __ GB · VM reached from the other laptops by = bridged /
forwarded ports · host = ______ · Docker Engine version = ______ · runsc version = ______ · platform = systrap / kvm ·
network mode = isolated gateway / internal + firewall · storage method = V1 / V2 / V3 · PostgreSQL version = ______

## Part 2 · Risks found during research (read before your first prompt)

| ID | Risk | Why it is real | What to do | Caught by |
| --- | --- | --- | --- | --- |
| R-01 | Building on Windows with WSL or Docker Desktop | A gVisor maintainer calls WSL "very much unsupported" [S9]; Docker Desktop hides the daemon in its own VM | Use a real Linux VM or machine from the first hour | preflight 1 to 4 |
| R-02 | Sandbox reaches the platform's own database or API through the bridge gateway | An internal network's bridge still has a host address unless gateway mode is `isolated` [S18] | Isolated gateway mode, or firewall fallback; nothing in the control plane listens on `0.0.0.0` except the proxy | T-ISO-04 |
| R-03 | Process limit behaves differently under gVisor | Processes inside a sandbox do not appear as host processes [S13], so the host process counter sees sandbox threads, not tenant processes | Do not assume. Run the fork bomb spike and record which limit contains it | preflight 7, T-RES-02 |
| R-04 | Memory graphs read near zero | Under gVisor application memory is accounted as shared memory, not anonymous [S13] | Use the cgroup total | T-MON-02, T-RES-01 |
| R-05 | Storage "limit" that does not limit | On the `overlay2` storage driver, `--storage-opt size=` needs an xfs backing filesystem mounted with `pquota` [S12]; RAM-backed volumes may count against memory | Storage ladder of `08` section 4 | T-RES-03 |
| R-06 | Agent proposes Falco for runtime monitoring | Falco removed its gVisor engine in version 0.44.0 [S20] | Our decision: Docker events and stats [S19]; gVisor trace points only as stretch S5 | review |
| R-07 | AI scan works at home and fails at the venue | garak option names differ between documentation pages [S28], and probes may need resources that are downloaded on first use | Fix the probe list, bake dependencies into the image, test with the network cable out | T-WL-03 |
| R-08 | Hashes differ from the vectors | Python's default JSON output escapes non-ASCII; floats, `None`, unsorted keys, or values changed by a database round trip break canonical bytes | Use the exact call in `04` section 7.1; forbid floats and null; run the vectors first | T-KAT-01, 02 |
| R-09 | Timestamps differ between writer and verifier | `+00:00` instead of `Z`, missing microseconds, application clock instead of database clock | Format in SQL from `clock_timestamp()`; the schema's check constraint rejects other shapes | schema check, T-KAT |
| R-10 | Ledger stalls or forks under load | The advisory lock serialises appends; a transaction that holds it while calling Docker or doing slow work blocks every other audit write | Runner does Docker work first, then one short transaction for state plus audit. API transactions contain only SQL | T-AUD-06 |
| R-11 | Live stream arrives in bursts or not at all | Reverse proxies buffer or compress event streams by default in some configurations | Disable buffering and compression for the stream route; test through the proxy, not directly | T-MON-01 |
| R-12 | Login "works" but no cookie is stored | `Secure` cookies need HTTPS; a self-signed certificate on a LAN address triggers warnings on the jury's machine | Decide the demo URL and certificate on day one; rehearse from a second laptop | T-AUTH-02, T-E2E |
| R-13 | Docker socket leaks beyond the runner | Docker's documentation says only trusted users should control the daemon, which runs as root [S7] | Socket only in `runner`; static check | T-STATIC-01 |
| R-14 | Command injection through `exec` | A user command concatenated into a host shell command | Pass the command as one argument to a shell inside the sandbox only | P-REDTEAM, review |
| R-15 | Images or rule files missing offline | No internet assumed at the venue | Digest-pinned images present locally; preflight check 10 | preflight 10 |
| R-16 | Notification payload too large | PostgreSQL NOTIFY payloads are small | Send row IDs for activity and audit; keep metric JSON short | T-MON |
| R-17 | Wrong key format for Ed25519 | Libraries differ on 32-byte seed versus 64-byte expanded key | 32-byte seed; the test key in the vectors must reproduce the vector signatures | T-KAT-03 |
| R-18 | Control-plane containers still run on the default runtime | Three runc breakout CVEs were disclosed in November 2025 [S8] | Keep Docker and runc at current patched releases; record versions | preflight 2 |
| R-19 | Two finale dates in official material | Schedule page says 27 November, manual says 2 December [S1][S2] | Plan for the earlier date; confirm by phone or email today | humans |
| R-20 | Laptops cannot reach the demo VM at the venue | Planning assumption, not a sourced fact: shared Wi-Fi often blocks device-to-device traffic, and a VM behind NAT is unreachable without forwarded ports | Bring your own small router or use a phone hotspot; choose bridged or forwarded ports at G0; rehearse the two-laptop demo on that exact network | G4 rehearsal |
| R-21 | The VM is slow because Windows' own hypervisor is active | VirtualBox shows a green turtle when a native hypervisor such as Hyper-V runs on the host, and users report degraded speed in that mode [S58] | Prefer VMware Workstation Pro on the Omen, or turn off the Windows features that enable the hypervisor and reboot; re-run the T-RES tests after any change | preflight 7, T-RES-04 |
| R-22 | Slow tools on Henil's and Bhavya's laptops | Microsoft recommends keeping project files in the WSL file system when using Linux tools, not under `/mnt/c` [S59] | Clone into `~/abhedya` inside WSL | first `make check-fast` |
| R-23 | Two runners on one Docker daemon destroy each other's sandboxes | Design consequence of `08` section 3: the reaper removes labelled objects whose environment row is missing from its own database | One stack per Docker daemon. Only Parth runs `make up` on the demo VM | symptom: environments vanish within 30 s |
| R-24 | The backup host was never tested | An imported VM copy can differ in CPU count, memory and network adapter | Export at G1 and at G4; on Parth's laptop run `make preflight` and the demo once, coordinated by Manas | G4 checklist |
| R-25 | A scanner score is presented as fact | garak's verdicts varied with the evaluator in 22 of 25 categories in a 2026 preprint [S53] | Say "scanner-flagged"; show the vulnerable versus guarded difference, never an absolute score | T-WL-03, demo script |
| R-26 | A `clean` file verdict is read as "safe" | Limit L8; an NDSS 2021 study recommends two minutes of execution for a behavioural report [S54], and our sandbox runs Linux programs only | 120 s deadline; the report page states the limit | C6 page text |
| R-27 | The team is not on the finalist list, or the finale format differs from the plan | The portal says the result has been declared; finalists were due on 24 November [S1] | Check the list and the reporting time today | humans |

## Part 3 · Bug journal

Write an entry when something costs more than 20 minutes, when a test that passed starts failing, or when an
agent was confidently wrong. Entries are evidence of engineering maturity for the jury; keep them factual.

```
### BUG-<n> · <short title>                      <date time> · owner <A|B|C>
Objective / test: <O# / T-...>
Symptom: <exact command and the exact output or screenshot path>
Expected: <what the contract or test says>
Investigation: <what was tried, in order, with results>
Root cause: <one or two sentences; "unknown" if unknown>
Was an AI agent wrong? <no | yes: what it claimed, how it was caught, which rule H# applies>
Fix: <commit id and one line>
Regression test: <test id or file that now fails if this returns>
Lesson for the other two members: <one line, or "none">
```

Entries are written in each person's own file, `team/<name>/work/JOURNAL.md`, in the format above, so four
people never edit the same lines. `make evidence` copies all four next to a copy of this file.

## Part 4 · Change requests

```
### CR-<n> · <contract file and section>         <date time> · raised by <A|B|C>
Problem: <why the contract cannot be implemented or is wrong, with evidence>
Proposed change: <exact new text or diff>
Affected: <which members, which tests, which code>
Agreed by: A __  B __  C __
Applied in commit: <id>
```

(entries go here)

---
<!-- team/bhavya/work/JOURNAL.md -->
# Bug journal · Bhavya (role C)

Write an entry when something costs more than 20 minutes, when a test that passed starts failing, or when the
agent was confidently wrong. Format: `docs/09_BUG_JOURNAL.md` part 3. Newest at the bottom. Keep it factual;
`make evidence` copies this file into the evidence pack the jury may read.

---
<!-- team/henil/work/JOURNAL.md -->
# Bug journal · Henil (role A)

Write an entry when something costs more than 20 minutes, when a test that passed starts failing, or when the
agent was confidently wrong. Format: `docs/09_BUG_JOURNAL.md` part 3. Newest at the bottom. Keep it factual;
`make evidence` copies this file into the evidence pack the jury may read.

### Budget note · `services/api` line count (2026-11-26 · owner A)
`services/api` is ~2058 non-comment lines (budget 1100 in `docs/05_OBJECTIVES.md`). All 31 contract routes (`R01`–`R31`), strict Pydantic input/output models for 11 shapes, Argon2id/CSPRNG/lockout auth, RBAC matrix loader, quota admission, quarantine upload streaming, SSE `LISTEN/NOTIFY` hub, live overview SQL, and `R28` ledger verification are implemented with `mypy --strict` typing and zero placeholders; further compression below 1100 lines would require dropping explicit field typing or merging unrelated route modules.

---
<!-- team/manas/work/JOURNAL.md -->
# Bug journal · Manas (role D)

## 2026-11-26 · G0 host handoff review

Parth pushed B0 at `55e7d96`. Static review of `host/preflight.sh` found the `res` helper compares its second
argument numerically with `-gt 5`, while checks 7a, 7b, and 7c call it with alphanumeric IDs. A failure in one
of those checks can therefore exit at the numeric comparison instead of continuing through checks 8–10 as the
script header promises. This is a review finding, not a claim from an executed Ubuntu preflight. Parth owns the fix.

Local host inspection: `Get-CimInstance Win32_ComputerSystem` reported MSI Vector A18 HX A9WHG, 32 logical CPUs,
33,438,138,368 bytes RAM, and a present hypervisor. VMware Workstation's `vmrun.exe` is installed; `vmrun list`
reported zero running VMs. No VMX or Ubuntu ISO was found in the inspected Documents, Downloads, or `N:\virtual-lab`
paths. An Ubuntu VM may exist elsewhere; no VM or runtime security claim follows from this inspection.

The owned instruction-template repair is in PR #1, `work/manas` → `integration`; it remains open for review.

---
<!-- team/parth/work/JOURNAL.md -->
# Bug journal · Parth (role B)

Write an entry when something costs more than 20 minutes, when a test that passed starts failing, or when the
agent was confidently wrong. Format: `docs/09_BUG_JOURNAL.md` part 3. Newest at the bottom. Keep it factual;
`make evidence` copies this file into the evidence pack the jury may read.


### BUG-1 · preflight aborted on alphanumeric check IDs                2026-11-26 · owner B
Objective / test: O1 / G0, B0 `make preflight`
Symptom: `res FAIL 7a ...` under `set -eu` printed `[: 7a: integer expression expected` and exited 1 (reproduced
  with the 55e7d96 `res` line in a scratch harness; never run on the Linux host).
Expected: the script header and B0: a FAIL in checks 6-10 is reported and the script continues to check 10.
Investigation: static review by Manas (team/manas/work/JOURNAL.md); reproduced with the original line for id 7a
  (exit 1) and confirmed the fixed line continues for 7a, 7b, 7c, 6, 10 and still exits for 5 and 1.
  Same review pass found `RV=$(runsc --version 2>&1 | head -1)` takes head's exit status, so a missing runsc
  was not reported there (old line exit 0 with "runsc: command not found"; new line calls res FAIL 3).
Root cause: `[ "$2" -gt 5 ]` compares the check ID numerically; IDs 7a-7c are not integers.
Was an AI agent wrong? yes: the agent wrote the helper and the header claim "a FAIL in 6-10 is reported" without
  exercising an alphanumeric ID; caught by Manas's review; rule H1 (no claim without an executed check).
Fix: 28cf689 compares "${2%%[a-z]*}"; runsc version captured before trimming.
Regression test: none automated (host/ has no test harness); the scratch harness commands are in HANDOFFS.md.
Lesson for the other members: exercise every distinct argument shape of a shell helper under `set -eu` before
  claiming its control flow.

### Budget accounting · services/runner (docs/05: 800 non-test lines)   2026-11-26 · owner B
Counting rule is not yet fixed: the Makefile on integration (26a71e0) has no check-fast target. Two counts:
  physical lines (wc -l) and code lines (no blanks, comments, docstrings; Python tokenizer + ast).
Measured at the commit after dc3dc2b (net.py folded into launch.py; it was a single-call-site wrapper, which
  docs/05 style limits forbid):
  launch 174/118 · reconcile 174/134 · templates 114/86 · objects 108/85 · storage 78/46 · state 58/38 ·
  main 49/35 · total 756 physical / 542 code. Remaining: 44 physical / 258 code.
ESTIMATES (not measured; sized from the B4-B7 prompts), code lines:
  B4 collect.py (events + OOM mapping, stats sampler + insert + pg_notify, threshold alerts with 5-min dedup,
     1-hour deletion, reconnect) ~130 · B5 exec job (claim, exec_run deadline, 64 KiB cap, job.finished) ~60 ·
  B6 file_analysis (analyzer, yr scan parse, detonation, verdict rule, destroy + label check) ~100 ·
  B7 ai_scan ~70, BLOCKED: no target may be built until the four-person CR on the O9 AI target.
  Projection: 542 + 290 = ~832 code lines without B7, ~900 with B7; physical counts would be far over 800.
Status: NOT over budget yet. No overage line is claimed now. If a merged slice crosses 800 under the rule
  make check-fast adopts, the one-line docs/05 note will be added here at that commit with the reason the
  lines are not removable. Before then: (1) Manas to fix the counting rule in check-fast; (2) reduce first:
  candidates are verbose validation messages in templates.py and launch.py, and docstrings that repeat the
  handoff (only if the rule counts docstrings).

### Budget accounting update · after B4 local slice   2026-11-26 · owner B
Measured (same two counts as above) with collect.py + metrics.py added and the failed-env reaper rule:
  reconcile 176/135 · launch 175/119 · collect 165/124 · templates 114/86 · objects 107/85 · metrics 80/50 ·
  storage 78/46 · state 58/38 · main 55/40 · total 1009 physical / 723 code.
Under a physical-line rule the runner is now OVER 800 (by 209). Under a code-line rule it is at 723 (77 left).
  Why not removed now: the counting rule is still undecided (Manas: check-fast); the excess under a physical
  rule is mostly docstrings recording contract basis and unverified Docker behaviour, which the anti-
  hallucination rules ask to keep next to the code. If the rule is physical lines, that is the first cut.
Next: B5 (~60 code) fits a code-line rule; B6 local (~40) would reach ~823 code lines, so B6 starts only after
  the rule is fixed or a reduction pass (verbose validation messages in templates.py/launch.py) is done.

### BUDGET OVERAGE · services/runner 857 code lines of 800 after B5 local slice   2026-11-26 · owner B
docs/05 line: services/runner is over its 800-line budget (857 non-test code lines; 1191 physical) because
  B5 adds the exec path (jobs.py 98, exec_policy.py 28) on top of B1-B4; the lines are contract checks
  (sandbox profile, template allowlist, job input), required state/audit writes, and the bounded-output and
  deadline guards of R-14. They are not removed now because each one is exercised by a test or a section-8 /
  section-5 rule, and cutting defensive branches before the Linux run shows which are needed would trade
  safety for a count.
Was an AI agent wrong? yes: the agent estimated B5 at ~60 code lines (entry above); it measured 133. Rule H1.
Measured: reconcile 135 · collect 125 · launch 119 · jobs 98 · templates 86 · objects 85 · metrics 50 ·
  main 47 · storage 46 · state 38 · exec_policy 28 (counting rule: no blanks, comments, docstrings).
Consequence: B6 (file analysis) cannot fit without either a reduction pass or a team decision on the budget
  (a budget change needs a four-person change request, CLAUDE.md rule 8). Raised with Manas in HANDOFFS.md.
Reduction candidates for a later pass, after Linux results: merge the duplicated env-row lookups in collect.py
  and jobs.py; shorter error-message branches in templates.py/launch.py; one shared "service actor" helper.

### Budget reduction pass · services/runner 857 -> 850 code lines   2026-11-26 · owner B
Manas asked for a reduction pass before any budget CR. Done: removed the one-implementation DockerWork Protocol
and three never-read Template fields; no unused module-level names found. The rest is required behaviour
(listed in team/parth/work/CR_PROPOSAL_runner_budget.md). Still over: 850/800 code, 1185 physical. The
over-budget line is now backed by that proposal (request 1000, B6 included as an estimate, B7 excluded).
