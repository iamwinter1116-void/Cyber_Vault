# 14 · Prior art: who has already built this, and what we took from them

Why this file exists: the question "has anyone done this before?" has an honest answer, and the answer makes the
project stronger. Every hard part of PS0001 has been solved by someone at scale. No single system below does
everything the problem statement lists, and none of them fits on one laptop. Our work is the selection and the
combination, plus proof the jury can run.

Reading rules
- Each fact carries a source number from `SOURCES.md`. All pages were read on 25 November 2026.
- "Adopted" and "left out" are our decisions, not statements by those systems' authors.
- A precedent justifies a design choice. It proves nothing about our build. Only the tests in
  `06_VERIFICATION.md` do that (failure mode F12).

## 1. The systems

| System | What its sources say it has achieved | Mechanism that matters | We adopted | We left out, and why |
| --- | --- | --- | --- | --- |
| **KYPO Cyber Range Platform**, Masaryk University [S44] | Developed since 2013; prototype validated in six runs of a cyber defence exercise for 50 participants; released as open source | Sandboxes are isolated virtualized networks on an OpenStack cloud; machines and trainings defined in JSON and YAML; built-in monitoring; requirement to run on off-the-shelf hardware | Environments defined as code; monitoring collected where the tenant cannot switch it off; browser access | OpenStack and a full VM per node: too heavy for one laptop |
| **DETERLab**, USC/ISI and UC Berkeley [S45] | Security testbed first funded in 2003; some 370 experimental nodes; DDoS, worm and BGP experiments run on it | No direct IP path from an experimental node to the internet; a VLAN per experiment on the control plane; a panic button; the containment plan removes live malware before nodes are reused | Its written risk list as a check on our threat model; the kill switch; destroy-and-verify after every file job (T-WL-02) | Physical nodes and switch hardware |
| **Google kCTF** [S46] | Built by Google's security team to host untrusted, vulnerable applications in competitions; a reward programme invites outsiders to break out of a live demo cluster | A separate sandbox per connection; a published threat model that lists mitigations it does not plan to implement | Planted flags for our break-it session (X-08); a threat model that names what is not built | Kubernetes and nsjail: more parts than Docker with gVisor on one host |
| **gVisor in production** [S47] | Millions of sandboxes a day under GKE Sandbox, Cloud Run and App Engine; Google says Anthropic and OpenAI use it to contain code execution; Ant Group reported over 100,000 instances in 2021; Modal, a vendor, reports over 40 million containers a day | System calls are served by a user-space kernel, not the host kernel [S4] | Our mandatory runtime (D1), on the `systrap` platform because we run in a VM [S10] | The KVM platform and GPU access |
| **AWS Firecracker** [S48] | In AWS Lambda and Fargate, supporting millions of production workloads and trillions of requests a month (peer-reviewed, NSDI 2020) | One microVM per function as the security boundary; a jailer as a second layer; rate limits enforced outside the guest because the guest is not trusted | Limits enforced from outside the sandbox (D3); a second layer on top of gVisor (dropped capabilities, read-only root, non-root user) | Firecracker itself: it needs KVM |
| **Inspect Sandboxing Toolkit**, UK AI Security Institute [S49] | Used for the institute's own AI agent evaluations; it says it helped the US Centre for AI Standards and Innovation, METR and Apollo Research adopt it | Isolation classified on three axes (tooling, host, network); gVisor is the host tier used for most agentic evaluations | The T.H.N notation as a label on every template (D12) | Kubernetes, domain allowlists, VM sandboxes |
| **CAPE Sandbox** [S50] | Open-source malware sandbox derived from Cuckoo. The pages read give no usage figures | A host manages the analysis; guests are isolated; network routing for an analysis defaults to none; guests are snapshotted | No network by default for detonation; a fresh environment per sample; a structured report | Windows guest VMs and behaviour instrumentation: days of setup. Stated as limit L2 |
| **AWS CloudTrail log file integrity validation** [S51] | A documented feature of a production cloud service | A hash of every log file; an hourly digest signed with a private key; each digest chained to the previous one; digests kept apart from logs; a command-line validator | Nothing new: it is the same pattern as our checkpoints, witness file and standalone verifier. We now name it on the precedent slide | Empty digests for quiet periods |
| **Trillian, Certificate Transparency, Sigstore Rekor** [S52] | Trillian is used in production by many large Certificate Transparency log operators; Rekor's public instance runs with a 99.5 % availability objective | Append-only Merkle tree logs with signed tree heads (checkpoints); inclusion proofs; independent witnesses that cosign after a consistency check | The vocabulary; stretch S7 (inclusion proof); limit L10 (our witness is not independent) | Consistency proofs and third-party witnesses |
| **garak** [S53] | A 2024 preprint introduces it as a framework for probing language models; a 2026 preprint calls it widely used and finds its verdicts unstable across evaluators in 22 of 25 attack categories | Structured probes against a target model | Our scanner; results worded "scanner-flagged"; our test compares two targets instead of trusting one score (L9) | Human review of each flagged output |
| **Bharat National Cyber Range 1.0**, Rashtriya Raksha University; **NFSU Centre of Excellence in Cyber Security**, Gandhinagar [S56] | The range was inaugurated at the Bharat National Cyber Exercise 2024; the NFSU centre offers a cyber range exercise certification and trains officers from more than 70 countries | No technical description in the pages read | Nothing technical. They show that Indian institutions, two of them in Gujarat, already invest in this category | Not applicable |

## 2. What the precedents changed in this pack

| # | Change | Taken from | Where |
| --- | --- | --- | --- |
| M1 | Every template carries an isolation profile, `T0.H2.N2` | UK AI Security Institute [S49] | `03` D12, `08` section 3, tasks B1, C3, C6 |
| M2 | Detonation deadline raised from 30 to 120 seconds | NDSS 2021 study: two minutes recommended for a behavioural report [S54] | `08` section 6, task B6 |
| M3 | New limit L8: "clean" is never "safe" | Same study, plus our Linux-only sandbox | `03` section 3.4, task C6 |
| M4 | New limit L9 and the wording "scanner-flagged" | 2026 preprint on evaluator instability in garak [S53] | `03` section 3.4, `08` section 6, tasks B7, C6 |
| M5 | New limit L10: the witness is not independent | Witness protocol of transparency logs [S52] | `03` section 3.4, `13` questions |
| M6 | Planted flags `flag_env` and `flag_host`; break-it session has five flags | Google kCTF [S46] | `06` fixtures and X-08, `08` section 12, tasks C2, C8 |
| M7 | T-WL-02 also asserts that nothing of the environment remains | DETER containment plan [S45] | `06` section 8, task B6 |
| M8 | Stretch S7: inclusion proof for one record | Sigstore Rekor [S52], RFC 6962 [S15] | `05` |
| M9 | Stretch S8: a real model as AI target through one allowlisted route | AISI network tier N1 [S49] | `05`, Parth's device file |
| M10 | Precedent slide and three new jury answers | All of section 1 | `13` sections 2 and 7 |
| M11 | Scoring-criteria map | National challenge site [S57] | `13` section 6 |

## 3. What the precedents did not change
- **No contract changed.** The schema, the authorization matrix, the ledger format with its test vectors and
  the 31 routes are byte-for-byte those of version 1. The precedents confirmed the design.
- **No new dependency.** Nothing was added to the allowlist.
- **No new mandatory objective.** The time left does not allow one.

## 4. Where we sit among cyber ranges
Published taxonomies describe cyber ranges by dimensions such as scenario, monitoring, scoring, management and
teaming [S55], and a NIST guide notes that virtualization is what makes ranges economically viable and also
protects the underlying infrastructure from the target environment [S55]. Against those dimensions:

| Dimension | Us |
| --- | --- |
| Environment and its isolation | Yes: this is the core |
| Monitoring | Yes: live resource and activity stream, audit ledger |
| Management | Yes: users, teams, quotas, kill switch |
| Scenarios with a storyline | No: three fixed templates |
| Scoring | No |
| Teaming (red, blue, white roles in an exercise) | No: we have access roles, not exercise roles |

So do not call the project a cyber range. Call it what the problem statement calls it: a secure, isolated and
auditable testing platform. Its distinguishing part is the audit ledger that an outsider can verify.

## 5. The honest sentence about originality
In the pages we read about the systems above we did not find one that combines application, file and AI
workloads with a tamper-evident ledger of the platform's own activity, at laptop scale, with the decisive checks
handed to an outsider. That is a statement about what we read, not about everything that exists. Say it that
way.
