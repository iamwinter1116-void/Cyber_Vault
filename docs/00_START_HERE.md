# 00 · Start here

This pack directs four people and their coding agents to build PS0001, "Design and Development of a
Secure, Isolated and Auditable Cybersecurity Testing Platform", as a small, tested codebase.
This pack is being installed as the initial commit in the shared `Cyber_Vault` repository before anyone opens an agent session.

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
3. Manas's 32 GB laptop is the primary host for the Ubuntu VM (initially 6 vCPU, 12 GB). Sandbox security does not
   count as verified in WSL or Docker Desktop (`03_CONTEXT.md` D2).
4. Parth's 24 GB laptop is a cold backup host; never run its Docker stack concurrently with Manas's.
5. Henil and Bhavya use WSL 2 for code and light checks; full-stack tests run on Manas's primary VM.
6. GPU hardware is not needed for mandatory objectives; the AI target is the offline stub.
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
| 2 | `docs/02_MASTER_PLAN.md` and `docs/TEAM_OWNERSHIP_AND_BRANCHING.md` | Architecture, four owners, hardware, file boundaries, branch route and merge authority | 15 min |
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

## First two and a half hours (gate G0), step by step
0. **Before T0:** Manas initializes the repository/branch set and creates the primary Ubuntu VM (`team/manas/01_DEVICE_SETUP.md`).
1. All four: read the shared files and ownership agreement together. Confirm exact owned paths before coding.
2. Manas creates `main`, `integration`, and `work/{manas,parth,henil,bhavya}` from the reviewed baseline.
3. Each person copies `team/<name>/CLAUDE.local.md` to the repository root on the machine where their agent runs.
4. Test the guard rails: each of you asks the agent to add a comment to `contracts/schema.sql` and to your own
   `team/<name>/02_PROMPTS.md`. Both must be refused. Then ask it to append a line to your
   `team/<name>/work/JOURNAL.md`. That must work. If not, fix `.claude/settings.json` before going on.
5. **Manas** starts M0/M1 first (branch setup and Makefile/Compose/CI scaffold).
6. **Bhavya** starts C0 (contract-test harness); **Parth** starts B0 on the primary VM.
7. **Henil** reads `04_CONTRACTS.md` fully, then starts A0 once Manas's scaffold is merged to `integration`.
8. Apply `contracts/schema.sql` on the real PostgreSQL in the stack. If it fails, that is change request 1.
9. All four sign the freeze table in `09_BUG_JOURNAL.md` and fill in the G0 decisions line.
10. From here each member works through their own prompt list in order, one fresh session per prompt.

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
