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
