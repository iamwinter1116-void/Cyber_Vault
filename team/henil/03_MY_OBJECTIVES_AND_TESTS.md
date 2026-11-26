# Henil · objectives you lead and the tests that decide them

This is a slice of `docs/05_OBJECTIVES.md` and `docs/06_VERIFICATION.md`. Those two files are the authority.
Bhavya writes the tests in `tests/contract` and `tests/security`; you make them pass and never edit them.

## Mandatory objectives

| ID | What must be true | Your tasks | Tests that decide it |
| --- | --- | --- | --- |
| **O2** Secure login and role-based access control | Argon2id hashes, opaque sessions with the cookie flags of `04` section 2, CSRF token, lockout; every rule of `rbac_matrix.yaml` enforced, deny by default | A2, A3 | T-AUTH-01 to 05; T-RBAC-01 to 12; T-API-01 |
| **O3** Separate environments per team (API half) | Another team's object is indistinguishable from a missing one (404); event streams are scoped; platform roles cannot read a team's job output | A3, A4, A5 | T-ISO-05; T-MON-03; T-RBAC-01, 02, 07 |
| **O4** Real-time monitoring (stream half) | One Server-Sent Events stream with server-side scope filtering and resume | A5 | T-MON-01, 03, 04 |
| **O5** Resource management (quota half) | Team quotas with admission control in the same transaction as the insert | A4 | T-RES-05 |
| **O6** Centralized audit logs | Every state-changing call, every refusal and every service action writes exactly one record through the single append path, atomically with the change | A1, A2 to A6 | T-AUD-01, 02, 06, 07 |
| **O7** Tamper detection (ledger side) | Append-only grants and triggers; hash chain; Merkle root; signed checkpoints; witness file; alert within 30 s | A1, A6 | T-KAT-01 to 03 (core side); T-AUD-03, 08 |
| **O8** Admin dashboard (API half) | Users, teams, quotas, overview, kill switch | A3, A5 | T-E2E-02 through Bhavya's console |

## What changed for you in version 2 of the pack
| Change | Where | Why |
| --- | --- | --- |
| No contract changed: schema, matrix, vectors and the 31 routes are exactly as in version 1 | `contracts/` | The precedents confirmed the design; none required a format change |
| New stated limit L10: the witness is kept by the same operator as the log | `docs/03_CONTEXT.md` section 3.4 | In transparency logs, witnesses are independent parties [S52]. Say this to the jury before they ask |
| New stretch S7: an inclusion proof for one record | `docs/05_OBJECTIVES.md` | Sigstore's Rekor pairs an inclusion proof with a signed checkpoint [S52]. Only after G4 |
| Full-stack "done when" lines run on the demo VM | A5, A6, A7 | Your laptop has no runner by design |

## Code budget (non-test lines; `make check-fast` prints the count)
`core/abh_core` 300 · `services/api` 1100 · `services/notary` 150.

## The precedent to quote when you explain the ledger
AWS CloudTrail does the same three things at cloud scale: hashes every log file, signs a periodic digest, and
keeps the digests apart from the logs so that a standalone tool can validate the chain [S51]. Our records are
chained one by one and our checkpoints carry an RFC 6962 Merkle root; the pattern is the same. Say "the same
technique as", never "as secure as".

## Definition of done for any of your tasks
All seven points of `docs/05_OBJECTIVES.md`. Every refusing path (401, 403, 404 by scope, 409) has a test that
takes it, and every refusal that the matrix says is audited has its record.
