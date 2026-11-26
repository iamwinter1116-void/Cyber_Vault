# Manas · integration objectives and gate evidence

Manas is accountable for the integrity of the integrated build and release path, not for taking over another owner's
feature code or test suite.

| Objective area | Integration responsibility | Acceptance evidence |
| --- | --- | --- |
| O1–O9 across the platform | Ensure the currently owned branches combine without changing contract semantics | Objective/test mapping in `docs/05_OBJECTIVES.md` and passing outputs on current integration commit |
| Build and deployment | Keep the Makefile/Compose/CI wiring aligned with owner interfaces | Clean start, health checks, target output, only proxy exposed |
| Branch governance | Keep all work flowing through `integration`; promote only tested integration to `main` | `git branch -vv`, PR review trail, merge commit IDs, remote branch rules once available |
| Host operations | Keep one active primary stack and announce reset windows | Host identity, VM snapshot, preflight results, reset/rehearsal log |
| Evidence and release | Make sure evidence describes the tested commit and honest limits | `evidence/INDEX.md`, test reports, scan triage, outsider/jury notes |

## Gate calls

Manas coordinates the gates. Bhavya supplies test reports. Parth supplies isolation/runtime evidence. Henil supplies
identity/API/ledger evidence. The gate is green only when every required command has actually completed successfully on
the required machine; an owner statement or generated document is not a substitute for output.

| Gate | Manas's integration check | Required owner evidence |
| --- | --- | --- |
| G0 | Branches, host preflight coordination, schema/contract review, scaffold and CI | Parth preflight; Henil schema/API baseline; Bhavya contract harness |
| G1 | Browser-to-runner happy path and clean audit verification | Henil auth/API/notary; Parth running `runsc`; Bhavya verifier/UI; Manas service wiring |
| G2 | All mandatory objective happy paths | Every feature owner plus Bhavya tests |
| G3 | Security suite, tamper drills, scanners, outsider session | Bhavya test/evidence; Parth sandbox; Henil ledger; Manas gate record |
| G4 | Freeze, offline rehearsal, backup readiness and release tag | All owners sign their evidence; Manas alone promotes `main` |

## Hard constraints

- Never merge a PR whose base is `main` from a contributor branch.
- Never allow a direct change to `integration` or `main` by another contributor.
- Never merge code that violates ownership without the path owner applying/reviewing the actual change.
- Never mark a test green because it was skipped, mocked, manually bypassed, or run against the wrong host.
- Never change frozen contracts without a signed CR from all four team members.
- Never run a second active runner/stack on the primary Docker daemon.
- Never commit `.env`, demo passwords, signing seed, witness secrets, flags, private TLS keys or customer data.
