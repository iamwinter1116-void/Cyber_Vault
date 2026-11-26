# Bhavya · objectives you lead and tests you own

This is a slice of `docs/05_OBJECTIVES.md` and `docs/06_VERIFICATION.md`. Those two files are the authority.

## Mandatory objectives you lead

| ID | What must be true | Your tasks | Tests that decide it |
| --- | --- | --- | --- |
| **O8** Admin dashboard | Console pages: overview, users and teams with quotas, environments with live usage and kill switch, live activity and alerts, audit with filter, export and verify | C3, C4, C5, C6 | T-E2E-01 to 04 |
| **O7** Tamper detection (verifier side) | An independent verifier gives the specified verdict for edits, deletions, reordering, truncation and full hash recomputation | C1, C2 | T-KAT-01 to 04 (verifier side); T-AUD-04, 05 |
| **O4** Real-time monitoring (display half) | The console shows state changes, metrics, alerts and audit records live, without reload | C3, C4 | T-E2E-01, T-E2E-04 |

## Tests you write for the others (they build until these are green)
| Suite | IDs | Written in | Runs on |
| --- | --- | --- | --- |
| Known-answer vectors | T-KAT-01 to 04 | C0, C1 | anywhere |
| Authentication, authorization, API fuzzing | T-AUTH-01 to 05, T-RBAC-01 to 12, T-API-01 | C0, later tasks | stack on Manas's primary VM |
| Isolation, static checks | T-ISO-01 to 07, T-STATIC-01 | C2 | Manas's primary VM only |
| Resources | T-RES-01 to 06 | C2 | Manas's primary VM only |
| Audit ledger | T-AUD-01 to 08 | C1, C2 | Manas's primary VM only |
| Monitoring | T-MON-01 to 04 | C2 | Manas's primary VM only |
| Workloads and end to end | T-WL-01 to 03, T-E2E-01 to 04 | C2, C8 | Manas's primary VM only |

## Gate responsibility
Manas calls G0–G4 and controls the primary VM. You provide the exact test commands, exit codes, output files, and
failing test IDs. Do not announce a gate as passed on your own; report results to Manas, who checks all owner evidence.
Your test PRs target `integration`; Manas alone merges and promotes to `main`.

## What changed for you in version 2 of the pack
| Change | Where | Why |
| --- | --- | --- |
| `make demo-reset` plants `flag_env` and `flag_host` | C8, `docs/06` fixtures, `docs/08` section 12 | Google kCTF plants flags that can only be read by escaping [S46] |
| The break-it session has five flags, not three | X-08 | Same source |
| T-WL-02 also asserts that nothing labelled with the environment remains | C2 | DETER's containment plan removes live malware before reuse [S45] |
| File page says "clean does not mean safe"; AI page says "scanner-flagged" | C6 | Limits L8 and L9 [S54][S53] |
| Environment badge tooltip shows the isolation profile `T0.H2.N2` | C3, C6 | Notation of the UK AI Security Institute [S49] |
| Evidence pack includes all four journals and the prior-art file | C7 | Journals now live in `team/<name>/work/` |
| Two new slides: scoring criteria and precedents | `docs/13` sections 6 and 7 | The national challenge site lists six criteria [S57] |

## Code budget (non-test lines; `make check-fast` prints the count)
`web/src` 1800 · `tools/verify_audit.py` 180.

## Outside judges you organise (X-01 to X-09)
Docker Bench, Trivy, Semgrep, gitleaks, ZAP baseline, Schemathesis, the witness file, one person outside the
team with 30 minutes and five flags, and the jury. Triage rule: every HIGH or CRITICAL finding is fixed or
listed in `evidence/scans/ACCEPTED.md` with a reason a security reviewer would accept.
