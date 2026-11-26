# Parth · start here

**Your role:** B, the isolation engine and workload runtime. You own the sandbox launcher, host setup, networks,
resource limits and job execution. Manas owns the primary demo host; your laptop is the cold backup host.
**Your code is the only code that holds the Docker socket.** Small and boring is the goal.
Current order: read `docs/16_BUILD_NOW_HOST_LATER.md`. Continue real runner and template implementation locally;
record B0 and all sandbox checks as pending until a real Linux host is available. No simulation proves isolation.

## Your folder
| File | What it is | When |
| --- | --- | --- |
| `00_START_HERE.md` | This page | now |
| `01_DEVICE_SETUP.md` | Runtime development, backup VM and how to run checks on Manas's primary host | before B0 |
| `02_PROMPTS.md` | Your nine agent tasks B0 to B8, in order, each ending in commands that prove it | one fresh session per task |
| `03_MY_OBJECTIVES_AND_TESTS.md` | The objectives you lead and the exact tests that decide them | before B1 |
| `CLAUDE.local.md` | Tells your agent who it works for and which machine it is on | copy to the repository root once |
| `work/JOURNAL.md` | Your bug journal | every failure longer than 20 minutes |
| `work/HANDOFFS.md` | Hand-off notes, appended by your agent at the end of every session | every session |

Shared files you must read once (about 50 minutes, with the other two): `docs/00_START_HERE.md`,
`docs/02_MASTER_PLAN.md`, `docs/03_CONTEXT.md`, then `docs/04_CONTRACTS.md` sections 1, 4, 5, 6, 8, 9, 10 and
`docs/09_BUG_JOURNAL.md` part 2.

## One-time agent setup
1. Clone the repository on your development environment. Keep the source tree on a Linux filesystem when using Linux tools.
2. `cp team/parth/CLAUDE.local.md ./CLAUDE.local.md` (it is git-ignored).
3. Guard-rail test: ask the agent to add a comment to `contracts/schema.sql` and to `team/parth/02_PROMPTS.md`.
   Both must be refused. Ask it to append a line to `team/parth/work/JOURNAL.md`. That must work.

## Your host boundary
Develop and review runner code on your machine, but execute gVisor, Docker, cgroup and network-isolation checks only
on Manas's primary Ubuntu VM over SSH. If a backup-host drill is needed, Manas must first announce that the primary
stack is stopped and explicitly hand over the active host. Never run a second stack concurrently.

## Work sequence
1. Confirm `work/parth` and your exact path boundary. Review and fix the pushed B0 scripts.
2. Prepare real runner code and locally testable units while B0 host preflight awaits a Linux test window.
3. Deliver the single runner launch path, network isolation, resource limits, cleanup, collectors and three workloads in dependency order.
4. Supply Bhavya with probe names, command interfaces and expected safe outputs before security tests are finalized.
5. Fix only failures tied to test IDs; report code/evidence to Manas for gate calls.
6. Do not start a backup VM stack unless Manas announces a host handoff and confirms the primary stack is stopped.

If G1 has not passed at 09:00 on 26 November, the tripwires in `docs/02_MASTER_PLAN.md` section 4 apply. For you that
means: `ai_scan` keeps only the `quick` probe set, and if tripwire 2 fires, B6 keeps static triage only.

## What only you must never forget
1. Every container you launch goes through the one `launch()` function with the whole profile of
   `docs/04_CONTRACTS.md` section 8. After every task, run `docker inspect` on a live sandbox and read it yourself.
2. If `runsc` is missing or broken, the platform says so on screen. It never quietly uses `runc`.
3. One stack on the VM at a time, and Manas starts it. A second runner on the same Docker daemon deletes the first
   one's sandboxes (risk R-23).
4. Nothing you learn about sandboxes in WSL or Docker Desktop counts. Only the VM counts.
5. Snapshot the VM after B0 passes. If an install goes wrong later, roll back instead of debugging the host.

## Ritual for every task
new session → paste **P-GROUND** → paste the task from `02_PROMPTS.md` → read the plan → let it work →
**P-CLAIMS** → **P-REDTEAM** → **P-REVIEW** → **P-HANDOFF** → the two-minute human checks of
`docs/07_ANTI_HALLUCINATION.md` section 4 → PR from `work/parth` to `integration`; Manas merges after review.
