# ABHEDYA instruction pack, version 2 (25 November 2026)

Team TM005136 · SFIC 2026 · PS0001: Design and Development of a Secure, Isolated and Auditable Cybersecurity
Testing Platform. This folder is the four-person instruction baseline for the GitHub repository.

```
README.md                 this map
CLAUDE.md                 loaded by every agent: short rules, roles, machines
.claude/                  enforced deny rules, stop hook, read-only reviewer
.gitignore                keeps CLAUDE.local.md and secrets out of git
contracts/                frozen machine-readable contracts (unchanged from version 1)
docs/                     shared truth, one copy; edits use agreed change requests
  00_START_HERE.md          first two hours, step by step
  01_DEEPER_BRIEF.md        what a top professional would add; the rewritten prompt
  02_MASTER_PLAN.md         architecture, who does what on which machine, gates, clock, tripwires, cuts
  03_CONTEXT.md             problem text, threat model, decisions D1 to D12, compatibility, limits L1 to L10
  04_CONTRACTS.md           schema, authorization matrix, ledger format, API, sandbox profile
  05_OBJECTIVES.md          nine mandatory objectives, definition of done, budgets, stretch S1 to S8
  06_VERIFICATION.md        every test with its pass condition; nine outside judges
  07_ANTI_HALLUCINATION.md  twelve failure modes, ten hard rules, seven ready prompts
  08_TECHNICAL_IMPLEMENTATION.md  how to build each part with the least code
  09_BUG_JOURNAL.md         freeze sign-off, risks R-01 to R-27, change requests
  13_DEMO_AND_EVIDENCE.md   jury script, questions, evidence pack, criteria map, precedent slide
  14_PRIOR_ART.md           proven systems, what we copied from each, what we did not
  15_CHANGELOG_V2.md        everything that changed from version 1 and why
  SOURCES.md                numbered sources S1 to S60; what was and was not verified
team/                     one folder per person
  README.md                 four-person ownership and folder map
  manas/                    role D, maintainer, integration/release, primary host
  parth/                    role B, isolation engine and workloads
  henil/                    role A, identity, API, quota and audit
  bhavya/                   role C, console, verifier and test suites
docs/specs/                 detailed ABHEDYA PRD, TRD, backend and architecture specs
docs/TEAM_OWNERSHIP_AND_BRANCHING.md  file boundaries, hardware assignments, branch and merge rules
```

Order: all four read `docs/00_START_HERE.md` and `docs/TEAM_OWNERSHIP_AND_BRANCHING.md` together, then each person
opens `team/<name>/00_START_HERE.md`. Manas is the sole merger into `integration` and `main`.
Numbers 10 to 12 are missing from `docs/` on purpose: personal setup and task instructions live under `team/`.
