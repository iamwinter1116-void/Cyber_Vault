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
