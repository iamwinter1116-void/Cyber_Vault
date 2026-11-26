# 07 · Anti-hallucination protocol

Why this file exists: a coding agent stops when the work looks done. Without something to run that returns
pass or fail, "looks done" is all it has [S31]. In a security product, code that looks done and is not is the
worst outcome, because it produces confidence without protection.

## 1. The failure modes we are defending against

| # | Failure | Example in this project | Defence |
| --- | --- | --- | --- |
| F1 | Invented package | A plausible name that does not exist on the registry. A USENIX Security 2025 study found that 19.7 % of 2.23 million packages recommended by code-generating models did not exist [S34]. An attacker can register such a name | Rule H3 |
| F2 | Invented or outdated flag, option or API | A `garak` option renamed between releases; a Docker network option the installed engine lacks | Rule H2 |
| F3 | Stale ecosystem knowledge | Wiring Falco to gVisor, although Falco removed that engine in 2026 [S20] | Rule H2, `03_CONTEXT.md` decisions |
| F4 | Claimed but not run | "All tests pass" with no output | Rule H1 |
| F5 | Test weakened to pass | Assertion loosened, `skip` added, real Docker replaced by a mock | Rule H5 |
| F6 | Silent substitution | `runc` used because `runsc` failed, nobody told | Rule H6 |
| F7 | Placeholder shipped | `return True  # TODO verify signature` | Rule H7 |
| F8 | Contract drift | Agent adds a field or renames a route because it seemed nicer | Rule H4 |
| F9 | Security theatre | "Isolated" asserted from configuration, never attacked | `06_VERIFICATION.md` |
| F10 | Volume as progress | Five hundred lines of abstraction around a twenty-line job | Rule H8 |
| F11 | Right command, wrong machine | Sandbox work run in WSL or Docker Desktop on a teammate's laptop, where `runsc` is unsupported [S9], giving results that do not transfer to the demo VM | `CLAUDE.local.md` names the machine; P-GROUND item 5 |
| F12 | Precedent used as proof | "Google uses gVisor, so our sandbox is safe" | `14_PRIOR_ART.md` justifies choices; only our own tests prove our build |

## 2. Hard rules (H1 to H10)

**H1 Evidence or it did not happen.** Every statement that something works is followed by the command, its
exit code and the relevant output lines. No output, no claim.

**H2 Three places to look, in this order, before using anything external:** (1) the installed tool itself:
`--help`, `--version`, `inspect`, the library's source in the environment; (2) official documentation for
that version; (3) the upstream repository. Memory is a lead for where to look, never the answer. If none of
the three confirms it, write `UNVERIFIED:` and the open question, and stop or run a ten-minute spike.

**H3 Dependency gate.** Only names in the allowlist (`03_CONTEXT.md` section 6). Before any install, confirm
on the registry that the exact name exists, who publishes it and its latest version (open
`https://pypi.org/pypi/<name>/json` or run `npm view <name> name version maintainers`), and append the line to `evidence/VERSIONS.lock`. The allowlist
in this pack was written from memory, so it goes through the same gate. A new name needs a change request.

**H4 Contracts are read-only.** `contracts/`, `docs/`, `CLAUDE.md` and the files directly inside each
`team/<name>/` folder are denied to the edit tool in `.claude/settings.json`. Only `team/<name>/work/` is writable.
If a contract looks wrong, stop and write a CR. Never work around it locally.

**H5 Tests are not negotiable.** Never weaken, skip, delete or mock away a test in `tests/contract`,
`tests/security` or `tests/e2e`. If a test seems wrong, say why and stop.

**H6 No silent fallback.** Any degraded path (runtime, network mode, storage method, missing scanner) must be
visible in three places: the console, the ledger or activity stream, and the hand-off note.

**H7 No placeholders.** No `TODO`, stub, fake success, hard-coded credential or commented-out check in
non-test code. If the real thing cannot be built in the time, leave the feature out and say so.

**H8 Smallest correct code.** Stay inside the budget of `05_OBJECTIVES.md`. Before adding a file, class or
helper, name its two call sites. Delete what the diff makes unused.

**H9 Permission to not know.** "I don't know" and "I could not verify this" are correct answers and are
preferred to a guess. Explicit permission to admit uncertainty reduces false statements [S33].

**H10 Stop and ask a human when:** a contract needs to change · a security test would need to change · a
sandbox would need a capability, a privileged flag, a host mount or the Docker socket · a new dependency is
needed · the budget would be exceeded · the same error has come back three times.

Rules H4 and part of H1 are enforced by configuration, not by request: deny rules (syntax in [S42]) hold in every permission
mode, and a stop hook that exits with code 2 sends the failing output back to the agent [S31]. Instructions
in `CLAUDE.md` are followed most of the time, not every time, which is why the rules that cannot have
exceptions live in `.claude/settings.json`. Keep `CLAUDE.md` under 200 lines, since longer files reduce
adherence [S32].

## 3. Ready prompts

**P-GROUND (paste at the start of every session, before the task prompt)**
```
Read CLAUDE.md and CLAUDE.local.md, then docs/03_CONTEXT.md sections 3 to 6 and the sections of
docs/04_CONTRACTS.md named in my task. Do not write code yet. Reply with:
1. The task in your own words, in at most five lines.
2. The contract sections and test IDs that decide whether it is done.
3. Every external fact you would rely on (tool flags, library calls, package names, version behaviour),
   each marked VERIFIED (say where you checked just now) or UNVERIFIED.
4. Your plan as at most eight steps, with the files you will create or change and the expected line count.
5. The machine you are on (run `uname -a`; if my task touches containers also run `docker info` and report the
   Runtimes line) and whether it is the machine CLAUDE.local.md says this task must run on. If not, stop.
If anything in the contracts looks wrong or contradictory, say so now instead of working around it.
```

**P-CLAIMS (paste when the agent says it is finished)**
```
Before I accept this: list every factual claim in your last message about behaviour you did not observe in
this session. For each one, either run the command that proves it and show the output, or retract it.
Then run the "done when" commands from the task again, from a clean state, and paste the full output.
If any command fails, do not explain it away. Fix the code, not the test.
```

**P-DEP (paste whenever a new import or package appears in a diff)**
```
You added or used the package <name>. Show me, by running commands now: that this exact name exists on the
registry, who maintains it, its latest version and release date, and that it is on the allowlist in
docs/03_CONTEXT.md section 6. Append the result to evidence/VERSIONS.lock. If it is not on the allowlist,
remove it and solve the task with the standard library or an allowlisted package, or stop and tell me why
that is impossible.
```

**P-REDTEAM (paste after each security-relevant task)**
```
Act as an attacker who has read this diff. Using docs/03_CONTEXT.md section 3 as the attacker list, name the
three most likely ways this change fails to stop TA1 to TA6. For each: the exact request or command, what you
expect to happen, and which test in docs/06_VERIFICATION.md would catch it. Then run those tests. If no
existing test would catch a way you found, write the failing test first and tell me; do not fix it silently.
```

**P-REVIEW (paste to get a fresh pair of eyes that cannot edit)**
```
Use the reviewer subagent to compare the changes on this branch against docs/04_CONTRACTS.md and the test
IDs of my task. Report only gaps that affect correctness or security: a contract field or status code that
differs, a refusing path with no test, a secret in a log or response, a missing audit record, a place where
a sandbox setting of section 8 is not applied. Skip style.
```

**P-UNSTICK (paste when the same failure appears a third time)**
```
Stop changing code. Append a bug journal entry to team/<my name>/work/JOURNAL.md in the format of
docs/09_BUG_JOURNAL.md part 3: symptom with exact output,
what you tried, what you now believe the cause is and how sure you are, and the smallest experiment that
would prove or disprove it. Run only that experiment. If it disproves your belief, say so plainly.
```

**P-HANDOFF (paste at the end of every session)**
```
Append the hand-off note to team/<my name>/work/HANDOFFS.md in the format of docs/07_ANTI_HALLUCINATION.md
section 5, newest at the bottom. Include only what you ran and saw in this session.
```

## 4. Human checks that take under two minutes each
1. Open the diff. Is any file outside your directories changed? Reject.
2. Search the diff for `skip`, `xfail`, `mock`, `TODO`, `privileged`, `cap_add`, `docker.sock`, `verify=False`,
   `# type: ignore`, `any`. Each hit needs a reason you accept.
3. Pick one claimed test at random and run it yourself.
4. For anything touching the sandbox, run `docker inspect` on a live container and read it against
   `04_CONTRACTS.md` section 8 with your own eyes.
5. Compare the line count with the budget.

## 5. Hand-off note format (the agent's last message of every session, also appended to `team/<name>/work/HANDOFFS.md`)
```
TASK: <prompt id and title>
STATUS: done | partial | blocked
CHANGED: <files, with line counts added/removed>
COMMANDS RUN (with exit codes):
  $ <command>   -> <exit code>
  <the lines of output that matter>
TESTS: <test ids> passed | failed (list)
VERIFIED FACTS: <external fact> -- <where it was checked>
UNVERIFIED / ASSUMED: <anything not checked; "none" only if true>
DEGRADED PATHS: <any fallback taken, and where it is visible; "none" only if true>
NEW DEPENDENCIES: <name, version, registry check; "none" only if true>
OPEN RISKS / QUESTIONS FOR HUMANS: <list>
NEXT: <the next prompt id>
```
