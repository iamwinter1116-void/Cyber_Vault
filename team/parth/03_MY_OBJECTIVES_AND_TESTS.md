# Parth · objectives you lead and the tests that decide them

This is a slice of `docs/05_OBJECTIVES.md` and `docs/06_VERIFICATION.md`. Those two files are the authority; if
this page and they ever differ, they win. Bhavya writes the tests in `tests/security`; you make them pass and
you never edit them.

## Mandatory objectives

| ID | What must be true | Your tasks | Tests that decide it |
| --- | --- | --- | --- |
| **O1** Isolated testing environments | A user creates an environment from the console; it runs under `runsc` with the full sandbox profile; code inside cannot reach the host, the control plane, the internet or another environment | B0, B1, B2 | T-ISO-01, 02, 04, 06, 07; T-E2E-01 |
| **O3** Separate environments per team (runtime half) | One network and one volume per environment; no route between teams | B1, B2 | T-ISO-03 (Henil's API supplies T-ISO-05) |
| **O4** Real-time monitoring (collection half) | State changes, resource samples and alerts are produced within the latency targets | B4 | T-MON-02; the alert part of T-RES-01 |
| **O5** CPU, RAM and storage management (limits half) | Hard limits per environment for CPU, memory, processes and storage; expiry and clean-up; a hostile environment cannot degrade a neighbour beyond the stated bound | B3 | T-RES-01, 02, 03, 04, 06 (Henil supplies T-RES-05) |
| **O9** Three workload types | `app-target`, `file-analysis`, `ai-redteam` each work end to end | B1, B5, B6, B7 | T-WL-01, 02, 03 |

## What changed for you in version 2 of the pack
| Change | Where | Why |
| --- | --- | --- |
| Detonation deadline is 120 seconds, not 30 | B6, `docs/08` section 6 | A peer-reviewed study of sandbox run times recommends two minutes for a behavioural report [S54] |
| After a file job, nothing labelled with that environment may remain | T-WL-02 | DETER's containment plan requires removing live malware before nodes are reused [S45] |
| Each `template.yaml` description starts with `[T0.H2.N2]` | B1, decision D12 | The UK AI Security Institute's notation for tooling, host and network isolation [S49] |
| AI results are worded "scanner-flagged" | B7, limit L9 | A 2026 preprint found garak's verdicts unstable across evaluators [S53] |
| `flag_host` exists on the VM at `/var/lib/abhedya/flag_host` | `docs/08` section 12 | Planted flags for the break-it session, after Google kCTF [S46]. No sandbox may ever see this path |

## Code budget (non-test lines; `make check-fast` prints the count)
`services/runner` 800 · `sandbox/` 450 · `host/` scripts 150.
Going over needs one line in `work/JOURNAL.md` saying why the extra lines cannot be removed.

## Evidence you personally produce
`evidence/preflight.md` (B0) · the pasted `docker inspect` of both `app-target` containers (B1) · the connection
table of B2 · the abuse-probe record of B3 · both numbers of the memory cross-check in B4 ·
`evidence/scans/docker-bench.txt` and your part of `evidence/scans/ACCEPTED.md` (B8).

## Definition of done for any of your tasks
All seven points of `docs/05_OBJECTIVES.md`, plus one that is yours alone: you ran `docker inspect` on a live
sandbox after the task and read it against `docs/04_CONTRACTS.md` section 8 with your own eyes.
