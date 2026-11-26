# 00 · Start here

This pack directs four people and their coding agents to build PS0001, "Design and Development of a
Secure, Isolated and Auditable Cybersecurity Testing Platform", as a small, tested codebase.
This pack is being installed as the initial commit in the shared `Cyber_Vault` repository before anyone opens an agent session.

**Current work order:** read `16_BUILD_NOW_HOST_LATER.md`. All four owners build real local slices now; Ubuntu
host setup and Linux-only acceptance follow later. No mock, simulation, 501 route stub or fake pass is allowed.

## Who, on what
| Person | Role | Machine | Folder |
| --- | --- | --- | --- |
| Manas | D · maintainer, integration/release owner · primary host | Ryzen 9 9955HX, RTX 5070 Ti 12 GB, 32 GB RAM | `team/manas/` |
| Parth | B · isolation engine and workload runtime · backup host | i7 HX class, RTX 5050 8 GB, 24 GB RAM | `team/parth/` |
| Henil | A · identity, API, quota and audit | Ryzen 7 260, RTX 5050 8 GB, 16 GB RAM | `team/henil/` |
| Bhavya | C · console, independent verifier and test suites | Ryzen 7, RTX 3050, 16 GB RAM | `team/bhavya/` |

## Assumptions made for you (change them in the first ten minutes if wrong)
1. You meant **quality over quantity**.
2. The source planning pack contains conflicting finale dates (27 November and 2 December 2026). These are historical
   planning assumptions; Manas must confirm the current event date and eligibility before setting a live schedule
   (`03_CONTEXT.md` section 2, risk R-27).
3. When provisioned, Manas's 32 GB laptop is the primary host for the Ubuntu VM (initially 6 vCPU, 12 GB). Sandbox security does not
   count as verified in WSL or Docker Desktop (`03_CONTEXT.md` D2).
4. Parth's 24 GB laptop is a cold backup host; never run its Docker stack concurrently with Manas's.
5. Henil and Bhavya use WSL 2 for code and light checks; full-stack tests run on Manas's primary VM.
6. GPU hardware is not needed for the local-first slices. The original AI workload specifies an offline model stub;
   this conflicts with the current no-stub instruction, so O9's AI target is pending a four-person change request.
7. Each person uses a coding agent that reads `CLAUDE.md`, `CLAUDE.local.md` and
   `.claude/settings.json`.
8. The original plan assumed the team would share a network from 26 November and have no usable venue internet.
   Confirm current venue/network conditions before relying on this assumption.
9. Role letters A, B, C remain in frozen contracts/tests; Manas is role D for maintainer/integration work. Current
   owners and file boundaries are in `02_MASTER_PLAN.md` and `TEAM_OWNERSHIP_AND_BRANCHING.md`.

## The shared files, in reading order

| # | File | What it is | Time to read |
| --- | --- | --- | --- |
| 1 | `docs/01_DEEPER_BRIEF.md` | What a top professional would add, raw material, methods, outside proof, and your prompt rewritten | 8 min |
| 2 | `docs/02_MASTER_PLAN.md`, `docs/TEAM_OWNERSHIP_AND_BRANCHING.md`, `docs/16_BUILD_NOW_HOST_LATER.md` | Architecture, owners, current work order, file boundaries and branch route | 15 min |
| 3 | `docs/03_CONTEXT.md` | Verbatim problem, threat model, twelve decisions with sources, compatibility matrix, ten limits | 15 min |
| 4 | `docs/14_PRIOR_ART.md` | Proven systems that already do parts of this, and what we took from each | 8 min |
| 5 | `docs/04_CONTRACTS.md` + `contracts/` | The frozen interfaces: schema, authorization matrix, ledger format with test vectors, API, sandbox profile | 25 min |
| 6 | `docs/05_OBJECTIVES.md` | Nine mandatory objectives with deciding tests, definition of done, code budgets, stretch list | 5 min |
| 7 | `docs/06_VERIFICATION.md` | Every test with its pass condition, and nine outside judges | 15 min |
| 8 | `docs/07_ANTI_HALLUCINATION.md` | Twelve failure modes, ten hard rules, seven ready prompts, hand-off format | 10 min |
| 9 | `docs/08_TECHNICAL_IMPLEMENTATION.md` | How to build each part with the least code; the spikes | your sections |
| 10 | `docs/09_BUG_JOURNAL.md` | Freeze sign-off, twenty-seven pre-found risks, change-request template | 5 min |
| 11 | `docs/13_DEMO_AND_EVIDENCE.md` | Seven-minute jury script, expected questions, evidence pack, criteria map, precedent slide, venue checklist | 10 min |
| 12 | `docs/15_CHANGELOG_V2.md`, `docs/SOURCES.md` | What changed from version 1 and why; numbered sources | 5 min |
| | `CLAUDE.md`, `.claude/settings.json`, `.claude/agents/reviewer.md` | Loaded by the agents: short rules, enforced deny rules and stop hook, read-only reviewer | |

Then each person opens their own folder: `team/<name>/00_START_HERE.md`.

## Start now · G0 remains pending until real host evidence exists
1. All four: read the shared contracts, ownership and current work-order decision. Confirm owned paths before coding.
2. The six branches already exist. Work only on `work/<name>`; copy `team/<name>/CLAUDE.local.md` to the root locally.
3. Test the guard rails: each of you asks the agent to add a comment to `contracts/schema.sql` and to your own
   `team/<name>/02_PROMPTS.md`. Both must be refused. Then ask it to append a line to your
   `team/<name>/work/JOURNAL.md`. That must work. If not, fix `.claude/settings.json` before going on.
4. **Manas** wires only actual owner commands and prepares CI; Compose and DB init follow reviewed interfaces.
5. **Henil** starts A1 real core/audit work against real PostgreSQL; add API routes only with real behavior.
6. **Bhavya** starts C0 vector/matrix contract cases and C1 independent verifier without waiting for the VM.
7. **Parth** fixes/reviews B0 scripts, then builds locally verifiable runner slices; real `runsc` claims wait for Linux.
8. Record local commands and pending host checks in each handoff. Apply `contracts/schema.sql` on real PostgreSQL
   when available. G0 freeze signatures and preflight pass wait for the host and actual evidence.

## The session ritual (identical for everyone, every prompt)
new session → paste **P-GROUND** → paste the task prompt → read the plan before any code is written →
let it work → paste **P-CLAIMS** → for security work paste **P-REDTEAM** → paste **P-REVIEW** → paste
**P-HANDOFF** → do the two-minute human checks → open a PR to `integration`; Manas alone merges after review.

## If you only remember six things
1. The contracts are law. Disagreement is a change request.
2. Nothing is done without the command and its output.
3. The sandbox runtime is never silently replaced, and nothing about it is ever tested in WSL.
4. Tests in `tests/contract` and `tests/security` are never weakened.
5. When a tripwire in `02_MASTER_PLAN.md` section 4 fires, cut from the list in section 5, and never from the
   "never cut" list.
6. A precedent explains a choice. Only our own tests prove our build.
