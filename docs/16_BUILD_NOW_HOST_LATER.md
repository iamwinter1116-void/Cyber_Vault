# Current execution order · build now, Linux proof later

Decision recorded 26 November 2026 by Manas for the four-person team. This changes the **work order**, not the
frozen interfaces, objective pass conditions, or test verdicts in `contracts/`, `04_CONTRACTS.md`, `05_OBJECTIVES.md`,
and `06_VERIFICATION.md`. Where an older schedule or role prompt requires the Ubuntu VM before any coding, this page
is the current instruction. Historical T0 dates and tripwires are not live deadlines.

## The two evidence levels

1. **Local implementation evidence:** real code, real local dependencies, unit/known-answer tests, static checks,
   command/output/exit code and commit. A component may be merged with this evidence if its PR clearly lists the
   Linux-dependent checks still pending. It is not an objective or gate pass.
2. **Host acceptance evidence:** only tests run on a real Linux host with Docker Engine, `runsc`, PostgreSQL and the
   integrated stack count for sandbox isolation, resource limits, workload containment, security and end-to-end gates.
   `make preflight` and the applicable tests must actually pass; WSL/Docker Desktop results do not substitute.

Never present a local pass as host acceptance. No task is described as fully complete while a required acceptance
check is pending. An owner may move to an **independent local slice** while a host-only check remains blocked; the
pending item stays open in the handoff and gate board. No G0–G4 gate or O1–O9 objective is marked green early.

## No fabricated behavior

- No mock, simulated container, 501 route stub, fake health response, placeholder success target, canned test output,
  or UI state pretending an environment ran. Unavailable features must refuse clearly and be reported as unavailable.
- The older `STUB-G0` route exception is suspended by this decision. Henil implements real core/auth/audit behavior
  and adds routes only as their real behavior is implemented. Generate OpenAPI only from implemented routes; record
  the missing matrix rules until all 31 are real. The frozen route contract itself is not altered.
- The original O9 design names an offline *model stub*. Manas's no-stub instruction conflicts with that design.
  Do not implement or claim the AI workload until all four approve a change request defining a real offline target,
  its dependencies, limits and deciding tests. Work on independent runtime pieces may continue.
- No fake test pass. Run available real checks aggressively; list each required check that could not run and why.

## Parallel work that can start now

| Owner | Immediate real local slice | Linux-host dependent acceptance held open |
| --- | --- | --- |
| Manas | Exact Makefile interface for real owner commands, repository CI and branch hygiene, Compose/DB init from reviewed owner interfaces | Primary host setup, full stack health, preflight, G0–G4 gate calls |
| Henil | Core canonicalization/hash/audit against real PostgreSQL; real authentication/session/RBAC and implemented API routes; notary code | Full-stack API, stream, quota, notary and tamper verification on demo host |
| Parth | Review/fix B0 scripts; implement typed runner reconciliation, launch policy, template parsing and unit tests against documented interfaces; do not claim sandbox behavior | B0 preflight and all Docker/`runsc`/cgroup/network/storage/workload tests |
| Bhavya | Contract cases derived from frozen vectors/matrix, independent verifier, UI against implemented API shapes, local type/unit checks | Real-stack contract/security/e2e tests, scans and demo evidence |

Each owner works in `work/<name>` and their owned paths, pushes coherent real slices, and opens PRs to `integration`.
Manas reviews path ownership, actual local evidence and the explicit pending host checks before merging. A PR can be
integrated as an incomplete slice; its title/body and handoff must say so. Only Manas promotes tested integration
to `main` under the agreed workflow. Do not merge a local-only slice to `main` as a finished release.

## Immediate dependency exchange

Before Manas wires a service in Compose or a Make target, the service owner supplies the actual build context/image,
start command, readiness command, variables, DB role, mounts, test command and output path in their handoff. Manas
may implement a target for an existing script such as Parth's `host/preflight.sh`; a missing target must fail
clearly rather than report success. Service owners continue independent real code while an interface is pending.

When a Linux host is available, Manas coordinates one active stack and test window. Parth fixes B0 issues and runs
preflight there; Bhavya runs the integrated test suites; Henil and Parth fix their owned failures. The host-dependent
backlog closes only from recorded commands, outputs, host identity and tested commit.
