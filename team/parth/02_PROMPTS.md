# Parth · role B · isolation engine · agent tasks B0 to B8

**You own:** `host/`, `services/runner/`, `sandbox/templates/`, `sandbox/probes/`, and their unit tests.
**You lead:** O1 (isolated environments), O5 (CPU, RAM, storage), O9 (three workload types); you supply the
runtime half of O3 and the collection half of O4.
**You never touch:** `contracts/`, `docs/`, `core/`, `services/api/`, `services/notary/`, `web/`, `tools/`, `tests/contract`, `tests/security`, other people's folders under `team/`.
**Where you run:** edit/unit-test on your development environment; run Docker, `runsc`, and isolation tasks on Manas's primary Ubuntu VM over SSH, in an announced window (`01_DEVICE_SETUP.md`). A is Henil, C is Bhavya, and D is Manas.
**Current sequence:** read `docs/16_BUILD_NOW_HOST_LATER.md`. The B0 scripts may be reviewed and repaired locally,
then independent real runner code may proceed. B0 and B1 isolation acceptance stay open until actual Linux tests.
**You are the only member whose code holds the Docker socket.** Everything you write is part of the trusted
computing base. Small and boring is the goal.

## What others need from you, and when

| By | Deliver | Who waits |
| --- | --- | --- |
| G0 | `evidence/preflight.md` with every check and the three spike results; the demo host ready | everyone |
| G1 | Runner that takes an `app-target` row from `requested` to `running` under `runsc`, with labels | A, C |
| T0 + 12 h | `sandbox/probes/` scripts (connect, memory hog, fork bomb, disk fill, CPU burn, environment dump) | C (security tests call them) |
| G2 | Limits, storage, expiry, reaper, collectors, alerts, exec, file and AI jobs | everyone |

## How to run each prompt
Same ritual as the other members: new session → **P-GROUND** → task prompt → **P-CLAIMS** → **P-REDTEAM**
(every task of yours is security-relevant) → **P-REVIEW** → **P-HANDOFF** → two-minute human checks → PR to
`integration`; Manas alone merges after review.
One extra human check for you after every task: run `docker inspect` on a live sandbox and read it against
`04_CONTRACTS.md` section 8 yourself.

---

### B0 · Host preflight and spikes (gate G0, about 90 minutes, on Manas's primary VM after arranging access)
```
Task B0. You are inside an Ubuntu Server virtual machine on a Windows laptop; confirm it and stop if
/proc/version mentions Microsoft. Read docs/03_CONTEXT.md sections 4 (D1 to D6) and 5, docs/08_TECHNICAL_IMPLEMENTATION.md sections 1
and 4, and risks R-01 to R-05, R-15, R-18 in docs/09_BUG_JOURNAL.md.
Write host/preflight.sh and host/setup_host.sh (together at most 150 lines, POSIX shell, set -eu). preflight
runs the ten checks of docs/08 section 1 in order, prints one PASS or FAIL line per check with the observed
value, writes everything to evidence/preflight.md, and exits non-zero on the first FAIL of checks 1 to 5.
For the three SPIKE checks (network isolation, limits under runsc, storage ladder) run the real experiment
with throwaway containers under --runtime=runsc, clean up after, and record the exact commands and outputs.
Rules: install Docker Engine and runsc only by following their official installation pages, which you must
open and quote the commands from; do not recall installation commands from memory. This is a virtual
machine, so keep gVisor's default systrap platform; do not configure the KVM platform. Record the hypervisor
name, the VM's CPU count and memory in evidence/preflight.md. Do not change kernel
parameters or Docker daemon options other than registering the runsc runtime, unless a check requires it and
you tell me first.
If check 4 (runsc hello-world) fails, stop and report; do not continue to later checks and do not suggest
running without runsc.
Done when: `make preflight` exits 0 on the demo host and evidence/preflight.md states: versions, cgroup
version, chosen network mode, which limit contained the fork bomb, chosen storage method, each with the
command output that shows it.
```

### B1 · Runner skeleton and the single launch function (about 2.5 hours) · tests T-ISO-01, T-ISO-02
```
Task B1. Read docs/04_CONTRACTS.md sections 8, 9, 10, the env table in contracts/schema.sql, docs/08 section 3,
and evidence/preflight.md. Member A provides abh_core (settings, db, audit.append); import it, do not copy it.
If it is not merged yet, code against the signatures in docs/04 section 10 and tell me what you assumed.
Build services/runner: the reconcile loop (select rows needing work with FOR UPDATE SKIP LOCKED; requested ->
provisioning -> running; desired stopped; desired destroyed), one launch() function that applies the complete
sandbox profile and is the only caller of the Docker SDK's container creation, per-environment network
creation using the mode chosen in preflight, template loading from sandbox/templates/<name>/template.yaml,
and state changes written together with the env.* audit record and the env.state_changed activity event in
one short transaction that is opened only after the Docker work has finished (risk R-10).
Build the app-target template: an in-repo deliberately vulnerable web application of at most 60 lines for the
target container, and a toolbox image with a shell, curl and a TCP-connect port scanner. Both images run as
UID 1000 with a read-only root filesystem. Record image digests in template.yaml. Start the template's
description with the isolation profile [T0.H2.N2] (decision D12 in docs/03_CONTEXT.md).
Confirm each Docker SDK argument you use against the installed SDK (help() or its source), not memory.
If runsc is unavailable: refuse to provision unless ABH_ALLOW_DEGRADED=true, and in that case set
isolation_tier, append isolation.degraded and raise alert.isolation_degraded. Never fall back silently.
Budget for this task: 350 lines of Python.
Done when: inserting a requested app-target row by SQL leads to observed_state running within 20 seconds;
`docker inspect` of both containers, pasted, shows every row of the section 8 table; killing and restarting the
runner mid-provision converges to exactly one set of objects; unit tests for the state machine pass.
```

### B2 · Network isolation and probe scripts (about 90 minutes) · tests T-ISO-03, 04, 06, 07
```
Task B2. Read docs/06_VERIFICATION.md section 4 and risk R-02.
Create sandbox/probes/: small scripts baked into the toolbox image and callable through exec, each printing
one JSON line: probe_connect (host, port, timeout -> reachable true/false), probe_env (environment variable
names, mounts, uid, capability sets from /proc/self/status, kernel release), probe_write (path -> ok or error
text), mem_hog (megabytes), fork_bomb, disk_fill (path), cpu_burn (seconds). At most 120 lines in total.
Then prove isolation yourself before C's tests do: from an alpha sandbox try every address of a bravo
sandbox, the bridge gateway address, the host's LAN address on 443, 5432 and 8000, and a public address on 53
and 443. All must fail. If any succeeds, fix the network configuration; do not weaken the probe.
Done when: a table of each attempted connection with its result is pasted, all refused or timed out;
probe_env output shows uid 1000, empty effective capabilities, no ABH_ variables, only the allowed mounts, and
a kernel release different from the host's.
```

### B3 · Limits, storage, expiry, reaper (about 2 hours) · tests T-RES-01 to 04, T-RES-06
```
Task B3. Read docs/04_CONTRACTS.md sections 4 (sizes) and 8, docs/08 sections 3 and 4, risks R-03 and R-05,
and the storage and limit results in evidence/preflight.md.
Implement storage.py with the method chosen at preflight behind one function pair (create_volume, remove_volume)
and the storage usage reading described in docs/08 section 4. Split CPU and memory across the containers of a
template so the sums equal the environment's limits. Implement expiry (expires_at passed -> destroyed, audited
as env.expired) and the 30-second reaper for labelled objects without a live row.
Run the four abuse probes inside an S environment while a second environment runs a heartbeat loop, and
record: what killed or contained each, the neighbour's worst heartbeat gap, the API health latency.
Done when: the outputs show the pass conditions of T-RES-01 to T-RES-04 and T-RES-06 exactly as written in
docs/06_VERIFICATION.md section 5; `docker ps -a`, `docker network ls`, `docker volume ls` filtered by the
abh.managed label are empty after destroying everything.
```

### B4 · Collectors and alerts (about 2 hours) · tests T-MON-02, alert part of T-RES-01
```
Task B4. Read docs/04_CONTRACTS.md section 6, docs/08 section 5, risks R-03, R-04, R-16, and the metric_sample
and activity_event tables.
Implement collect.py: one Docker events subscription filtered by the abh.managed label; a stats sampler every
ABH_METRIC_INTERVAL_SEC that inserts one metric_sample per running environment and sends the abh_metric
notification with a compact JSON payload; threshold alerts exactly as defined in section 6 with one alert
per environment per kind per five minutes; deletion of samples older than one hour. Reconnect the events
subscription after a Docker restart without losing the loop.
Check your memory figure against the cgroup's own total for a sandbox that allocated a known amount, and
paste both numbers.
Done when: T-MON-02 passes; an induced out-of-memory kill produces alert.oom_killed on the stream within 5
seconds and one env.oom_killed audit record, shown with timestamps.
```

### B5 · Exec jobs (about 75 minutes) · supports T-E2E-01, T-RBAC-12
```
Task B5. Read docs/04_CONTRACTS.md section 5 (exec), docs/08 section 6, and risk R-14.
Implement the job claim query and the exec executor: run the command inside the named container as UID 1000
through a shell inside the sandbox, 60-second deadline, combined output capped at 65536 bytes with the
truncated flag, status done, timeout or error, one job.finished audit record and activity event.
The command string is hostile input. It must never reach a shell on the host or be formatted into another
command. Write a test that submits a command containing quotes, semicolons, backticks and $(...) and shows it
executed only inside the sandbox.
Done when: that test passes; a 70-second sleep ends as timeout; a command printing 200000 bytes is truncated.
```

### B6 · File analysis (about 2 hours) · test T-WL-02
```
Task B6. Read docs/04_CONTRACTS.md section 5 (file_analysis and the verdict rule), section 8 (file-analysis
row), docs/08 section 6, limit L2 in docs/03_CONTEXT.md.
Build the file-analysis template: an analyzer image containing the YARA-X command line tool and an in-repo
rule directory (one rule for the standard antivirus test file tagged malicious; a few behaviour-string rules
tagged suspicious), and a detonator image with common script interpreters. Both run with network none.
Implement the pipeline: hash, type identification, rule scan, optional detonation with a 120-second deadline
(docs/08 section 6 gives the reason), verdict by the deterministic rule, result in the contract shape,
environment destroyed afterwards, and a check that no container, network or volume with that environment's
label remains.
Read the scanner's actual command syntax from its own help output. Obtain the antivirus test string from its
official publisher's page and verify the scanner flags it; do not type it from memory.
The sample is mounted read-only as a single file; it is never written to the host outside the quarantine
directory and never executed outside the detonator.
Done when: T-WL-02's three cases produce the stated verdicts, shown as job results; the detonation of a
script that tries a network connection reports failure to connect; a script that sleeps 130 seconds ends with
timed_out true and verdict suspicious; `docker ps -a`, `docker network ls` and `docker volume ls` filtered by
that environment's label are empty afterwards.
```

### B7 · AI red-team scans (about 2.5 hours) · test T-WL-03
```
Task B7. Read docs/04_CONTRACTS.md section 5 (ai_scan), section 8 (ai-redteam row), docs/08 section 6,
decision D10, risk R-07.
Build llm-target: an HTTP stub of at most 60 lines with a hidden system instruction and a planted secret, in
modes vulnerable (obeys instructions inside the user message, can be made to reveal the secret) and guarded
(refuses messages matching a small deny list). No model download, no GPU.
Build scanner: an image with garak installed and every resource its chosen probes need baked in.
First run `garak --help` and the probe listing of the installed version and paste them. Choose a quick probe
list (finishes in under 3 minutes on the stub) and a full list, using only probes that run with no internet.
Drive the stub through garak's REST generator. Parse the JSONL report into the contract result shape; map
probe families to OWASP LLM 2025 risk IDs with a small table in the template and cite the OWASP page title for
each ID you use in a comment.
Prove offline operation: run the scan inside the environment's internal network with the host's internet
access disabled, and show it completes.
Never describe a result as proof that a model is safe or unsafe: results are scanner-flagged (limit L9).
Done when: T-WL-03 passes: failures above zero on vulnerable, strictly fewer on guarded, every probe row has
an OWASP ID, report_sha256 matches the stored report.
```

### B8 · Degraded mode, benchmark triage, reduction (remaining time before G3)
```
Task B8. First: test the degraded path on purpose (set ABH_SANDBOX_RUNTIME to a name that does not exist):
with ABH_ALLOW_DEGRADED=false provisioning must fail visibly; with true the tier, audit record and alert must
appear. Second: run Docker Bench for Security from its official repository, read every WARN that concerns
containers labelled abh.managed, fix those that the sandbox profile should already satisfy, and write the
rest with reasons to evidence/scans/ACCEPTED.md (the runner's socket mount is an expected, documented
warning). Third: delete unused code and report the line count against the budget.
Done when: both degraded-mode behaviours are shown; the benchmark output is saved; the count is within budget.
```
