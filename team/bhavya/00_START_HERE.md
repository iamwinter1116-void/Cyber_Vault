# Bhavya · start here

**Your role:** C: the web console, independent audit verifier, contract/security/e2e tests, scanners, and evidence.
You are the team's independent test owner. Manas is the maintainer and integration/release owner; you do not own
the Makefile, Compose file, CI, or merge queue.
Current order: read `docs/16_BUILD_NOW_HOST_LATER.md`. Start vector/matrix tests and the independent verifier now;
record real-stack tests as pending until a Linux host exists. Do not simulate API or sandbox success.

## Your folder
| File | What it is | When |
| --- | --- | --- |
| `00_START_HERE.md` | This page | now |
| `01_DEVICE_SETUP.md` | WSL setup for your Ryzen 7 / RTX 3050 / 16 GB system and the shared VM boundary | before C0 |
| `02_PROMPTS.md` | Your nine agent tasks C0 to C8, in order | one fresh session per task |
| `03_MY_OBJECTIVES_AND_TESTS.md` | The objectives you lead and the tests you own | before C1 |
| `CLAUDE.local.md` | Tells your agent its role and file boundary | copy to the repository root on your WSL checkout |
| `work/JOURNAL.md`, `work/HANDOFFS.md` | Your bug journal and hand-off notes | every session |

Shared files you must read once (about 60 minutes, with the other three): `docs/00_START_HERE.md`,
`docs/02_MASTER_PLAN.md`, `docs/03_CONTEXT.md`, `docs/04_CONTRACTS.md`, all of `docs/06_VERIFICATION.md`
(you write those tests), `docs/13_DEMO_AND_EVIDENCE.md`, and `docs/09_BUG_JOURNAL.md` part 2.

## One-time agent setup
1. Inside WSL: clone into `~/abhedya`, then `cp team/bhavya/CLAUDE.local.md ./CLAUDE.local.md`.
2. For later full-stack tests, SSH into Manas's primary Linux host as `bhavya` when Manas opens a test window;
   no host-dependent test is claimed now.
3. Guard-rail test: ask the agent to add a comment to `contracts/schema.sql` and to
   `team/bhavya/02_PROMPTS.md`. Both must be refused. Appending to `team/bhavya/work/JOURNAL.md` must work.

## Work sequence
1. Confirm `work/bhavya` and your exact path boundary. Start independent contract work without a VM or scaffold.
2. Complete C0 contract tests and C1 verifier; send vector results to Henil and Manas.
3. Complete C2 contract/security suites; report failing test IDs to the owning implementation engineer.
4. Build C3–C6 UI pages after the corresponding API shapes are available; do not edit API or runner code.
5. Complete C7 scanners/evidence and C8 demo rehearsal only in coordination with Manas.
6. Manas calls gates and controls the shared host. You provide exact commands, exit codes and evidence paths.

## What only you must never forget
1. Your tests come from the contracts, never from Henil's or Parth's code. When a test and their code disagree,
   the contract decides. You do not loosen a test to make a gate pass.
2. Your verifier imports nothing from `core/` or `services/`, and for C1 and C2 your agent does not open those
   directories at all.
3. A gate passes only when every listed command exits 0 **on Manas's primary VM**. Not on your laptop, not "almost".
4. A scanner that was not run is reported as not run. An evidence file is generated, never typed.
5. Your laptop is the lightest. Edit there, run heavy things on the VM, and say early if it slows you down:
   moving your whole session onto the VM is a planned fallback, not a failure.

## Ritual for every task
new session → **P-GROUND** → the task from `02_PROMPTS.md` → read the plan → let it work → **P-CLAIMS** →
**P-REVIEW** → **P-HANDOFF** → two-minute human checks → PR from `work/bhavya` to `integration`; Manas merges.
