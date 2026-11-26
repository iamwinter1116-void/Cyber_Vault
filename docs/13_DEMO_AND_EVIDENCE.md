# 13 · Jury demonstration and evidence pack

Principle: the jury performs the decisive checks. The team narrates; the system and the jury's own hands
provide the proof.

## 1. Seven-minute script (rehearse with a timer; `make demo-reset` before every run)

| Min | Deliverable shown | Action | What the jury sees |
| --- | --- | --- | --- |
| 0:00 | Framing | One sentence: "We will attack our own platform four ways and you will pick the fifth." Show the threat table of `03_CONTEXT.md` section 3.2 on one slide | Attackers TA1 to TA6 |
| 0:30 | O1, O2, O3 | Log in as `analyst.alpha`. Create an `app-target` environment, size S | State goes requested → running live; badge "gVisor"; limits listed |
| 1:15 | O1 (TA1) | In the command box run the connect probe against bravo's environment, the gateway, the host, a public address. Then `uname -r` | Every connection refused; kernel string differs from the host's shown in a terminal |
| 2:00 | O5, O4 (TA3) | Run the memory hog. Second browser window shows bravo's environment graph | Alpha's sandbox is killed; red alert arrives live; bravo's graph stays flat |
| 2:45 | O2, O3 (TA2, TA6) | As `analyst.alpha` paste bravo's environment URL. Then log in as `admin` and try to run a command in alpha's environment | 404 for the analyst; 403 for the admin; both refusals appear in the live audit feed |
| 3:30 | O9 | Upload the antivirus test file with detonation on; start a quick AI scan on the vulnerable stub | Verdict "malicious" with the rule name; AI findings listed with OWASP LLM risk IDs |
| 4:30 | O6, O7 (TA5) | As `auditor` open Audit, press Verify (OK), show the last signed checkpoint. **Ask a jury member to choose any row and any field.** A teammate changes it directly in the database as superuser | Within 30 s a red banner: HASH_MISMATCH at that sequence number |
| 5:30 | O7, the hard case | Reset. Run the "smart attacker" drill that edits a row and recomputes every later hash | The chain alone looks valid; the banner still turns red: ROOT_MISMATCH against the signed checkpoint |
| 6:15 | O7, independent proof | Hand the jury a laptop or USB stick with only `verify_audit.py`, the public key and the export | They run it; exit code 2 and the same verdict. They change one byte themselves; it fails again |
| 6:45 | O8, O5 | As `admin`: overview, lower bravo's quota, global kill switch | All environments stop; every action is in the ledger |

If something breaks live: say what failed, show the same step in the backup recording, move on.
Never restart services on stage without saying so.

## 2. Questions to expect, with honest answers

| Question | Answer |
| --- | --- |
| "Is a container really isolated?" | Not by itself. That is why every sandbox runs on gVisor, which handles system calls in its own user-space kernel instead of the host's, and why we test escape paths instead of asserting them. Limit: no protection against hardware side channels. |
| "What if your admin edits the log?" | The admin's database role cannot update or delete. A superuser can, and is detected: the hash chain catches edits, and signed checkpoints with a copy outside the database catch someone who recomputes the chain. |
| "What can you not detect?" | False records appended by someone holding a runtime role, and truncation of the last 30 seconds before a checkpoint. Both are stated in our limits. |
| "Can it analyse Windows malware?" | Static triage, yes. Detonation, no: the sandbox runs Linux binaries only. A hardware-virtualised Windows guest is the next step. |
| "Is the AI testing real?" | The scanner is a real open-source tool running real probes. The target in the demo is a small stub service so it runs offline; pointing the scanner at a real model endpoint is a configuration change. |
| "How do you know the AI-written code is correct?" | We do not trust it. Contracts were frozen first, tests are generated from the contracts, the verifier was written independently from the ledger, known-answer vectors were checked in two languages, and outside scanners and an outside person attacked the result. The bug journal lists where the agents were wrong. |
| "Has anyone built this before?" | Yes, in parts, and we chose each part because it is proven: gVisor isolates Google Cloud Run and GKE Sandbox, AWS CloudTrail signs log digests the way our notary signs checkpoints, KYPO and DETER are testbeds with per-user isolation. In the pages we read about those systems we did not find one that puts all three workload types and a ledger the jury can verify on one laptop. The list is in `14_PRIOR_ART.md`. |
| "How is this different from a cyber range such as KYPO?" | A range like KYPO builds full virtual networks on an OpenStack cloud for exercises. Ours is a laptop-scale testing platform: lighter isolation, no scenarios or scoring, and an audit ledger that an outsider can verify. |
| "Why should we trust the witness file? You hold it." | You should not, fully. In transparency logs the witnesses are independent parties. Ours is a file on the same host, which is a stated limit; an external anchor is the next step. |
| "Does it scale?" | One host today. The API only writes desired state and runners reconcile it, so more runner hosts can be added. Verification is linear in log size; Merkle consistency proofs are the scaling path. |

## 3. Evidence pack (`make evidence` builds `evidence/`)

```
evidence/
  INDEX.md            objective -> tests -> pass/fail -> file (generated)
  preflight.md        host facts and spike results
  VERSIONS.lock       every dependency with registry check and version
  tests/              JUnit XML for contract, security, e2e
  scans/              docker-bench, trivy, semgrep, gitleaks, zap, ACCEPTED.md
  witness/            checkpoint witness file, ledger export, verifier output
  break-it.md         outsider session: who, when, what they tried, what happened
  bug-journal.md      copy of docs/09_BUG_JOURNAL.md followed by the four team/<name>/work/JOURNAL.md files
  prior-art.md        copy of docs/14_PRIOR_ART.md
```

## 4. Standards mapping to print on one slide (claim only what the tests prove)

| Standard clause | What it asks | Our control | Proof |
| --- | --- | --- | --- |
| NIST SP 800-53 Rev. 5 AU-9 | Protect audit information from unauthorized access, modification and deletion | Append-only grants and triggers, scoped read access | T-AUD-03, T-RBAC-01 |
| NIST SP 800-53 Rev. 5 AU-9(3) | Cryptographic mechanisms to protect integrity of audit information | Hash chain, Merkle root, Ed25519-signed checkpoints | T-KAT, T-AUD-04, 05 |
| NIST SP 800-53 Rev. 5 AU-10 | Evidence that an individual performed an action | Actor, source address and request ID in every record, inside the signed history | T-AUD-01 |
| OWASP ASVS 5.0 8.2.1 | Function-level access restricted to explicit permissions | Deny-by-default matrix | T-RBAC-01, 05 |
| OWASP ASVS 5.0 7.2.3 | Session tokens from a CSPRNG with at least 128 bits of entropy | 256-bit opaque tokens, hashed at rest | T-AUTH-02 |
| OWASP Password Storage Cheat Sheet | Argon2id with at least m=19456, t=2, p=1 | Same or stronger | T-AUTH-01 |
| CIS Docker Benchmark (through Docker Bench) | Container runtime configuration | Sandbox profile | X-01, T-ISO-02 |
| OWASP Top 10 for LLM Applications 2025 | Risk taxonomy for LLM applications | Scan results labelled with risk IDs | T-WL-03 |
| CERT-In Directions, 28 April 2022 | Logs enabled and kept securely for a rolling 180 days; synchronised clocks | Retention setting of 180 days, NTP check in preflight | preflight 9 |

Wording rule for the slide and the talk: "designed against" or "tested against", never "compliant with" or
"certified".

## 5. Venue checklist
- The demo host: Parth's HP Omen with the Ubuntu VM. The backup: the same VM imported on Henil's Legion, with
  `make preflight` and one full demo run done on it. Both power adapters. Offline rehearsal done.
- Your own network: a small router or a phone hotspot that all four laptops and the jury's device can join
  without internet (risk R-20). Rehearse on it.
- A second laptop or phone browser for the bravo view. A third device or USB stick for the jury's verifier run.
- All images present by digest; `make preflight` green on the morning of the event.
- Certificate for the demo URL already trusted on the presenting browsers.
- Backup: screen recording of the full script; `evidence/` on a USB stick; the slide with limits.
- A cloud VM copy and a phone hotspot only as a last resort; do not plan on venue internet.
- Roles on stage: one narrator, one operator, one on the database terminal for the tamper step.

## 6. Scoring criteria: one sentence and one proof for each
The Gujarat portal pages read on 25 November publish no scoring rubric. The national Seva First Innovation
Challenge site scores every entry on six common criteria [S57]. Until the organisers say otherwise, prepare for these.

| Criterion (national site) | The question it asks [S57] | Our sentence | What to show |
| --- | --- | --- | --- |
| Problem clarity | Observed first-hand, defined precisely, worth solving? | Say where you saw it yourselves: a shared college lab, a CTF, an internship. One team's test breaks another's, and the logs can be edited by whoever owns the machine | Threat table TA1 to TA6 |
| Originality | What is new, given what already exists? | The parts are proven elsewhere. The combination on one laptop, with a ledger the jury can verify themselves, is ours | The slide of section 7 |
| Demonstrated feasibility | Built, tested or piloted with evidence? | Live attacks that fail, a generated index of test results, a logged break-it session | Demo, `evidence/INDEX.md`, `evidence/break-it.md` |
| Cost | What does one unit cost, and who pays? | One 4-core, 8 GB host admits 6 isolated size-S environments at once; our 6-core, 12 GB VM admits 10 (admission rule of `04` section 4). Built on open-source components; confirm each licence in `evidence/VERSIONS.lock` before saying "no licence cost" | Overview page host bars |
| Beneficiary impact | Who benefits, how many, by how much? | First users: a college security lab or club (give your real head-count). Then training centres: the NFSU cyber security centre in Gandhinagar and the Bharat National Cyber Range show that institutions already invest in this [S56] | One slide |
| Scalability | Can it be replicated elsewhere? | The API only writes desired state and runners reconcile it, so a second host is a second runner; setup is one script on a stock Ubuntu machine | `host/setup_host.sh`, limits slide |

## 7. Precedent slide (print it; say "the same technique as", never "as secure as")

| Our part | Already proven by |
| --- | --- |
| gVisor sandbox per environment | Google: millions of sandboxes a day under GKE Sandbox, Cloud Run and App Engine [S47]; UK AI Security Institute for most agentic AI evaluations [S49] |
| Limits enforced from outside the sandbox | AWS Firecracker under Lambda and Fargate [S48] |
| Signed log digests, a separate copy, a standalone validator | AWS CloudTrail log file integrity validation [S51]; Certificate Transparency logs and Sigstore Rekor [S52] |
| Per-team environments defined as code, monitored from outside | KYPO Cyber Range Platform [S44]; DETERLab [S45] |
| Planted flags and an open invitation to break in | Google kCTF and its reward programme [S46] |
| No network by default when detonating a file | CAPE Sandbox [S50] |
