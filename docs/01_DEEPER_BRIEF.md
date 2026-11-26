# 01 · Deeper brief: what you asked, what a top professional would do, and the rewritten prompt

You asked for a master plan, prompts and files for three teammates and their Claude agents.
This file answers your four questions first, then rewrites your request so it asks for the deeper version.
Reading of one phrase: you wrote "quantity over quality" right after saying you do not want thousands of lines
of rubbish code. The whole pack assumes you meant **quality over quantity**.

## 1. What a top professional would do here that you did not ask for

1. **Write the threat model before any code.** Name who attacks (a malicious tenant inside a sandbox, a curious
   user from another team, an insider with database access, an anonymous network caller), what they want, and
   which boundary stops each one. Every feature is then judged by which attacker it stops.
2. **Treat the platform as the target.** A security platform is judged by attacks on itself. The professional
   plans the escape attempts, cross-tenant requests, resource bombs and log tampering first, as executable
   tests, and builds until those tests pass.
3. **Freeze interfaces before splitting work.** Three people with three AI agents drift apart within an hour
   unless the database schema, the authorization matrix, the audit record format and the API are fixed as
   machine-readable files that tests enforce.
4. **Separate prevention, detection and proof for the audit log.** Blocking edits (database permissions) is
   prevention. A hash chain is detection. Signed checkpoints held outside the database are proof that survives
   an attacker who rewrites the whole chain. Most student projects stop at the hash chain, which an insider
   who knows the algorithm can recompute.
5. **State the limits in public.** What the sandbox does not stop (hardware side channels, Windows malware,
   a compromised orchestrator) is written down and shown to the jury. Unstated limits read as ignorance,
   stated limits read as competence.
6. **Refuse silent degradation.** If the strong sandbox runtime is missing, the platform says so on screen and
   in the audit log. It never quietly falls back to ordinary containers.
7. **Plan the demo as an experiment the jury runs.** The jury chooses the audit row to corrupt and runs the
   verifier on a machine the team does not control.
8. **Budget scope against the clock.** With the finale on the official schedule two days away, a professional
   ranks features by proof value per hour and fixes the order in which things get cut.

## 2. The rawest material they would start from

| Instead of digested material | Start from |
| --- | --- |
| The problem statement summary | The exact portal text (copied verbatim in `03_CONTEXT.md`), the official schedule page and the synopsis you already submitted |
| Blog posts on container security | Docker Engine reference pages, gVisor architecture and user guides, the runc security advisories of November 2025 |
| Tutorials on "blockchain logging" | RFC 6962 (Merkle tree hash definition), the Crosby and Wallach 2009 paper on tamper-evident logging, NIST SP 800-53 controls AU-9, AU-9(3), AU-10 |
| "Best practice" lists for login | OWASP Password Storage and Session Management cheat sheets, OWASP ASVS 5.0 chapters V7 and V8 |
| Claims that a tool works | The output of the tool on your own host: `docker info`, `docker inspect`, `/sys/fs/cgroup`, `runsc --version`, `<tool> --help` |
| AI answers about package names and flags | The package registry page and the installed tool's own help text |
| Opinions on AI red teaming | The OWASP Top 10 for LLM Applications 2025 text and the garak reference documentation |
| Indian compliance hearsay | The CERT-In Directions of 28 April 2022 (log retention and clock synchronisation clauses) |

## 3. The specific methods and tools they would use

| Area | Method | Tools |
| --- | --- | --- |
| Isolation | Application-kernel sandbox per environment, one internal network per environment, all capabilities dropped, read-only root filesystem | gVisor `runsc` under Docker Engine, internal bridge networks with isolated gateway mode |
| Resources | Kernel control groups per environment plus admission control against team quotas | Docker `--cpus`, `--memory`, `--pids-limit`, size-capped volumes |
| Identity | Memory-hard password hashing, opaque server-side sessions, CSRF token, lockout | Argon2id, HttpOnly Secure SameSite=Strict cookies |
| Authorization | One declarative matrix, deny by default, tests generated from the matrix | `contracts/rbac_matrix.yaml`, pytest parametrisation |
| Audit | Append-only table, hash chain, RFC 6962 Merkle root, Ed25519-signed checkpoints, external witness copy | PostgreSQL roles and triggers, SHA-256, Ed25519 |
| Monitoring | Event stream and resource statistics read from the container engine, pushed to browsers | Docker events and stats API, PostgreSQL LISTEN/NOTIFY, Server-Sent Events |
| File testing | Static triage, then detonation with no network and a time limit | YARA-X, hash and type identification, gVisor sandbox with `network none` |
| AI testing | Automated probe sets mapped to a public risk taxonomy | garak, OWASP Top 10 for LLM Applications 2025 |
| Verification | Known-answer vectors, property-based tests, schema-driven API fuzzing, adversarial drills | pytest, Hypothesis, Schemathesis |
| Agent control | Short project memory file, enforced deny rules, fresh-context reviewer, evidence with every claim | `CLAUDE.md`, `.claude/settings.json`, a read-only reviewer subagent |

## 4. What, other than you or me, would show the result is right

1. **Known-answer vectors.** `contracts/audit_vectors.json` holds hashes, Merkle roots and signatures that were
   computed in Python and re-verified by an independent JavaScript implementation with a different Merkle
   algorithm. Any implementation that reproduces them follows the specification.
2. **Two independent implementations.** Member A writes the ledger. Member C writes the verifier from the
   specification alone, importing nothing from A. Agreement between them is evidence neither agent invented
   its own format.
3. **Adversarial drills with a known correct answer.** Ten tampering cases each have one expected verdict.
   Escape, cross-tenant and resource-bomb tests each have one expected outcome.
4. **Third-party scanners.** Docker Bench for Security (CIS Docker Benchmark), Trivy, Semgrep, gitleaks,
   OWASP ZAP baseline and Schemathesis judge the system without knowing what the team intended.
5. **An external witness.** Signed checkpoints are copied outside the database. Optional anchoring to a public
   timestamp service proves when a checkpoint existed.
6. **People outside the team.** The faculty mentor or another team gets an analyst account and thirty minutes
   to break it. The jury picks the audit row to corrupt.
7. **Published standards.** Each control maps to a clause in NIST SP 800-53, OWASP ASVS 5.0, the CIS Docker
   Benchmark or the CERT-In Directions, so a reviewer can check the claim against the clause.

## 5. Your prompt, rewritten to ask for exactly that

> We are a team of three students building PS0001 for the Seva First Innovation Challenge: a secure, isolated
> and auditable cybersecurity testing platform. Each of us works with a Claude coding agent. Produce the
> complete instruction pack that all three agents will be fed, optimised for a small, correct codebase
> rather than a large one.
>
> Work the way a senior security engineer would. Before designing, write the threat model: attackers, assets,
> trust boundaries, and the limits we will state openly. Start from primary material only: the verbatim
> problem statement, official engine and sandbox documentation for the versions we will run, the relevant
> RFCs, NIST, OWASP, CIS and CERT-In texts, and commands executed on our own host. Treat anything recalled
> from memory, including package names, flags and versions, as unverified until checked.
>
> Deliver: (a) one architecture that satisfies all eight listed deliverables and the three workload types
> (applications, suspicious files, AI systems); (b) machine-readable canonical contracts (database schema,
> authorization matrix, audit record format with known-answer test vectors, API surface) that are frozen
> before work is split; (c) a master plan with ownership for three members, integration gates, a schedule
> tied to the real finale date, and a fixed order of cuts; (d) mandatory objectives, each with acceptance
> tests whose pass or fail does not depend on our opinion; (e) a verification plan that attacks the platform
> itself: sandbox escape attempts, cross-tenant access, resource exhaustion, and audit tampering including an
> attacker who recomputes the hash chain; (f) an anti-hallucination protocol with enforced rules and ready
> prompts; (g) per-member files with ordered, self-contained prompts for their agent, each ending in commands
> that prove completion; (h) a bug journal pre-filled with the risks you found during research; (i) the
> jury demonstration designed so the jury, not the team, performs the decisive checks.
>
> For every design choice, name the specific method and tool, the version-sensitive facts it depends on with
> their sources, the compatibility constraints across operating system, runtime and hardware, and the
> evidence, other than our own judgement, that will show it works. State what the system does not protect
> against. Enforce code budgets, a dependency allowlist, and a rule that no claim of completion is accepted
> without the command and its output.
