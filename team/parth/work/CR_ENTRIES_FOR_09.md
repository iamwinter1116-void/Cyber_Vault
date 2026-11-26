# Two change-request entries for docs/09_BUG_JOURNAL.md Part 4 (ready to paste by a human)

docs/09 is edited by humans only, so these are written here for one member to paste. The numbers `<n>` are
assigned at paste time as the next free CR numbers (Part 4 had no entries on integration 9c8675b).
The template's "Agreed by" line lists A, B and C only; the rule (CLAUDE.md rule 8, docs/04 header, Manas
2026-11-26) is all four members, so a D slot is added. Nothing is approved until all four slots are filled.

```
### CR-<n> · docs/03_CONTEXT.md section 6 (dependency allowlist: sandbox/service base image, packages)   2026-11-26 22:30 IST · raised by B
Problem: section 6 allowlists sandbox images `yara-x` and `garak` only and says "Anything else needs a change
  request". No base image, OS package or transitive Python package is allowlisted, so no sandbox image (G1
  needs an S app-target env running on gVisor) and no runner service image can be built. Evidence and the full
  reasoning: team/parth/work/CR_PROPOSAL_sandbox_images.md (registry digest read 2026-11-26T16:26Z; PyPI
  requires_dist of every locked runner package).
Proposed change: in docs/03_CONTEXT.md line 222, after "Sandbox images: `yara-x`, `garak`." add:
  "Base image for sandbox images and the runner image: Docker Official Image `python:3.13-slim-trixie`,
  referenced only by digest (index sha256:7249d5587b78209a006dc4a3b5340678f84ea729239193aa559962cd8c1fce50 as
  read 2026-11-26). Debian package `curl` in the `toolbox` image only. Probes and the `target` application use
  the Python standard library only. Python packages installed as dependencies of an allowlisted package are
  allowed when each is recorded with exact version and sha256 in evidence/VERSIONS.lock and installed with
  `pip install --require-hashes`."
Affected: B (images, probes, target app, runner image), C (security/workload tests call the probes and curl),
  D (builds on the Linux host, lock and evidence), A (same base/transitive rule applies to api/notary images
  if adopted). Tests: T-ISO-01..07, T-RES-01..06, T-WL-01..02, T-E2E-01, T-MON-02.
Agreed by: A __  B yes (Parth, 2026-11-26 22:57 IST)  C __  D __
Applied in commit: <id>
```

```
### CR-<n> · docs/05_OBJECTIVES.md "Code budget" (services/runner)   2026-11-26 22:30 IST · raised by B
Problem: `make budget-report` on integration 9c8675b prints `services/runner: 850/800 OVER` after a reduction
  pass (857 -> 850). The remaining lines are required behaviour of docs/04 sections 5, 6, 8 and docs/08
  sections 3-6 (list: team/parth/work/CR_PROPOSAL_runner_budget.md). B6 (file analysis) cannot start under 800.
Proposed change: in docs/05_OBJECTIVES.md line 33, change "| `services/runner` | 800 |" to
  "| `services/runner` | 1000 |". The 150 lines above the current count are an estimate for B6, measured and
  reported at the B6 commit. B7 (ai_scan) is excluded and needs its own budget in the O9 change request.
  Alternative: none that fits 800. The runner is already at 850 before any B6 line, and O9 (mandatory,
  docs/05) requires file-analysis static triage; docs/02 section 5 cut 5 removes only detonation ("keep static
  triage"). Cutting detonation would lower the B6 estimate, not bring the total under 800.
Affected: B (runner, B6), D (`make budget-report` reads its limits from this docs/05 table since PR #24,
  so it follows the change without a code edit).
  Tests: T-WL-02 (B6).
Agreed by: A __  B yes (Parth, 2026-11-26 22:57 IST)  C __  D __
Applied in commit: <id>
```
