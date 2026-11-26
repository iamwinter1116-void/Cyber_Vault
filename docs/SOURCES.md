# Sources

Every external fact in this pack carries a number from this list. All pages were read on 25 November 2026.
S1 to S43 came with version 1; S44 to S60 were added for version 2 (precedents, devices, scoring criteria).
Anything in the pack that carries no number is a design decision, a calculation, or a lead that the
anti-hallucination protocol requires the agents to verify before use.

| # | Source | Used for |
| --- | --- | --- |
| S1 | SFIC official schedule page · https://www.sfic.co.in/importantdate.php | Finale on 27 November 2026 as prototype building and jury demonstrations; finalists declared 24 November |
| S2 | SFIC student manual PDF · https://www.sfic.co.in/datafiles/Student_User_Manual.pdf | Conflicting finale date of 2 December 2026; team size 1 to 8 |
| S3 | gVisor Docker quick start · https://gvisor.dev/docs/user_guide/quick_start/docker/ | `runsc install`, `docker run --runtime=runsc` |
| S4 | gVisor security model · https://gvisor.dev/docs/architecture_guide/security/ | System calls handled by the Sentry, none passed through; reliance on host cgroups; no side-channel protection |
| S5 | gVisor FAQ · https://gvisor.dev/docs/user_guide/faq/ | Linux only; x86_64 and ARM64; Linux ELF binaries |
| S6 | gVisor README · https://github.com/google/gvisor | "Containers are not a sandbox"; shared kernel means one vulnerability can allow escape |
| S7 | Docker Engine security · https://docs.docker.com/engine/security | Daemon runs as root unless rootless; only trusted users should control it |
| S8 | oss-security advisory, 5 November 2025 · https://openwall.com/lists/oss-security/2025/11/05/3 | runc container breakouts CVE-2025-31133, CVE-2025-52565, CVE-2025-52881 |
| S9 | gVisor issue 11370 · https://github.com/google/gvisor/issues/11370 | Maintainer statement that gVisor inside WSL 1 or 2 is unsupported; use a standalone VM |
| S10 | gVisor platform guide · https://gvisor.dev/docs/architecture_guide/platforms/ | `systrap` default and suited to VMs; KVM best on bare metal |
| S11 | gVisor application compatibility · https://gvisor.dev/docs/user_guide/compatibility/ | Limits not enforced between processes inside one sandbox; restrict through a host cgroup |
| S12 | Docker `container run` reference · https://docs.docker.com/reference/cli/docker/container/run/ | `--cpus`, `--memory`, `--pids-limit`, `--read-only`, `--tmpfs`, `--cap-drop`, `--security-opt no-new-privileges`, `--runtime`; `--storage-opt size` is limited to the btrfs, overlay2, windowsfilter and zfs drivers, and on overlay2 needs xfs with pquota |
| S13 | gVisor resource model · https://gvisor.dev/docs/architecture_guide/resources/ | Sandbox processes are not host processes; application memory accounted as shared memory; cgroup monitoring |
| S14 | Docker `volume create` reference · https://docs.docker.com/reference/cli/docker/volume/create/ | Local driver accepts mount-style options; tmpfs volume with `o=size=100m,uid=1000` |
| S15 | RFC 6962, Certificate Transparency · https://www.rfc-editor.org/info/rfc6962/ | Merkle tree hash with 0x00 leaf and 0x01 node prefixes; audit paths; consistency proofs; Signed Tree Head (section 3.5). Not a source for the hash chain, Ed25519 or the witness file, which are our design |
| S16 | Crosby and Wallach, Efficient Data Structures for Tamper-Evident Logging, USENIX Security 2009 · https://www.usenix.org/legacy/events/sec09/tech/full_papers/crosby.pdf and slides https://www.usenix.org/legacy/events/sec09/tech/slides/crosby.pdf | Semantics of tamper-evident logs; limitation that junk can still be logged |
| S17 | Docker bridge network driver · https://docs.docker.com/engine/network/drivers/bridge/ | Containers on different bridge networks are isolated except through published ports |
| S18 | Docker port publishing, gateway modes · https://docs.docker.com/engine/network/port-publishing/ | Internal networks still give the bridge an address reachable from containers; gateway mode `isolated` removes it |
| S19 | Docker Engine API · https://docs.docker.com/reference/api/engine/version/v1.57/operations/SystemEvents/ and https://docs.docker.com/reference/api/engine/version/v1.57/operations/ContainerStats/ | Event stream with label and type filters; live container statistics |
| S20 | Falco 0.44.0 release notes, 26 May 2026 · https://falco.org/blog/falco-0-44-0/ | Removal of the gVisor engine from Falco. Not a source for what we monitor with instead (see S19) |
| S21 | gVisor runtime monitoring · https://gvisor.dev/docs/user_guide/runtimemonitor/ | Trace points streamed to an external monitoring process |
| S22 | NIST SP 800-53 Rev. 5 · https://nvlpubs.nist.gov/NISTpubs/SpecialPublications/NIST.SP.800-53r5.pdf ; control text read at https://www.fedramp.gov/2026/reference/controls/audit-and-accountability/ and https://800-53-viewer.danielchapman.dev/AU/AU-9(3) | AU-9, AU-9(3), AU-10 wording |
| S23 | RFC 8785, JSON Canonicalization Scheme · https://www.rfc-editor.org/info/rfc8785/ | Standard for deterministic JSON serialisation |
| S24 | OWASP Password Storage Cheat Sheet · https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html | Argon2id minimum m=19456, t=2, p=1 |
| S25 | OWASP Session Management Cheat Sheet · https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html | HttpOnly; SameSite=Strict preferred; SameSite is not a CSRF-token replacement |
| S26 | OWASP ASVS 5.0 · https://github.com/OWASP/ASVS/blob/v5.0.0/5.0/en/0x16-V7-Session-Management.md and https://github.com/OWASP/ASVS/blob/master/5.0/en/0x17-V8-Authorization.md | Requirements 7.2.3 and 8.2.1 |
| S27 | YARA-X command line · https://virustotal.github.io/yara-x/docs/cli/commands/ | `yr scan` syntax |
| S28 | garak documentation · https://reference.garak.ai/en/stable/generators/rest.html , https://docs.garak.ai/garak/garak-components/using-generators , https://docs.garak.ai/garak/examples/basic-test | REST generator; offline test generators; JSONL report; differing option names across pages |
| S29 | OWASP Top 10 for LLM Applications 2025 · https://genai.owasp.org/llm-top-10/ and https://genai.owasp.org/llmrisk/llm01-prompt-injection/ | Risk IDs; LLM01 prompt injection |
| S30 | CERT-In Directions, 28 April 2022 · https://www.cert-in.org.in/PDF/CERT-In_Directions_70B_28.04.2022.pdf | Logs kept securely for a rolling 180 days in Indian jurisdiction; NTP synchronisation with NIC or NPL |
| S31 | Claude Code best practices · https://code.claude.com/docs/en/best-practices | Give the agent a check to run; ask for evidence; hooks and deny rules for rules without exceptions; fresh-context reviewer subagent; specific prompts |
| S32 | Claude Code memory files · https://code.claude.com/docs/en/claude-md | Keep `CLAUDE.md` under 200 lines; concrete, verifiable instructions; `CLAUDE.local.md` at the project root for personal, git-ignored instructions |
| S33 | Anthropic, Reduce hallucinations · https://platform.claude.com/docs/en/test-and-evaluate/strengthen-guardrails/reduce-hallucinations | Permission to say "I don't know"; quote first; verify claims and retract unsupported ones |
| S34 | Spracklen et al., We Have a Package for You!, USENIX Security 2025 · https://www.usenix.org/system/files/usenixsecurity25-spracklen.pdf | 19.7 % of 2.23 million generated package references did not exist |
| S35 | Docker Bench for Security · https://github.com/docker/docker-bench-security/ | Automated checks based on the CIS Docker Benchmark v1.6.0 |
| S36 | CIS on NIST SP 800-190 · https://www.cisecurity.org/cybersecurity-tools/mapping-compliance/mapping-and-compliance-with-the-cis-benchmarks and https://csrc.nist.gov/pubs/sp/800/190/final | Container runtime configuration should be checked automatically against standards such as the CIS Docker Benchmark |
| S37 | Trivy documentation · https://trivy.dev/docs/latest/guide/target/container_image/ and https://www.trivy.dev/docs/latest/guide/target/filesystem/ | Image and filesystem scans; misconfiguration scanning off by default |
| S38 | Schemathesis documentation · https://schemathesis.readthedocs.io/en/stable/ | Property-based API tests generated from an OpenAPI schema; stateful phase |
| S39 | gVisor filesystem guide · https://gvisor.dev/docs/user_guide/filesystem/ | Root filesystem overlay, backing media, optional size limit |
| S40 | OpenTimestamps · https://opentimestamps.org/ | Free public calendar servers for timestamp proofs (stretch S3) |
| S41 | Docker `network create` reference · https://docs.docker.com/reference/cli/docker/network/create/ | `--internal` networks have no default route; the gateway address still reaches host services |
| S42 | Claude Code permissions · https://code.claude.com/docs/en/permissions/ | Read and Edit rule syntax with gitignore-style paths; a leading `/` anchors a rule at the project root; `*` matches within one path segment; deny rules cannot be overridden by allow rules |
| S43 | ClamAV scanning manual · https://docs.clamav.net/manual/Usage/Scanning.html | `clamscan` for stretch S6 |
| S44 | KYPO Cyber Range: Design and Use Cases (ICSOFT 2017) · https://is.muni.cz/repo/1386573/2017-ICSOFT-kypo-cyber-range-design-paper.pdf and KYPO CRP documentation · https://docs.crp.kypo.muni.cz/ | Requirements (isolation, built-in monitoring, off-the-shelf hardware); six exercise runs for 50 participants; developed since 2013; open source; definitions in JSON and YAML; protection of monitoring from participants |
| S45 | A Plan for Malware Containment in the DETER Testbed (2007) · https://www.usenix.org/legacy/events/deter07/tech/full_papers/ostrenga/ostrenga_html/ and Cybersecurity Experiment Management (DETER project) · https://deter-project.org/sites/default/files/files/Sarnoff-T1T2.pdf | Funding in 2003; no direct IP path to the internet; panic button; removal of live malware before reuse; some 370 nodes; VLAN per experiment; list of testbed risks |
| S46 | Google kCTF · https://google.github.io/kctf/ , https://google.github.io/kctf/vrp.html , https://google.github.io/kctf/security-threat-model.html | Built to host untrusted vulnerable applications; separate sandbox per connection; reward programme with hidden flags; threat model listing unimplemented mitigations |
| S47 | gVisor users page · https://gvisor.dev/users/ ; Google Cloud blog, 5 November 2026 · https://cloud.google.com/blog/products/containers-kubernetes/open-infrastructure-for-autonomous-agents-comes-to-cncf ; Ant Group post, 2 December 2021 · https://gvisor.dev/blog/2021/12/02/running-gvisor-in-production-at-scale-in-ant/ ; Modal post, 11 November 2026 (vendor) · https://modal.com/blog/modal-gvisor-maintainer | Millions of sandboxes daily; GKE Sandbox, Cloud Run, App Engine; use by Anthropic, OpenAI, Modal, Snowflake as stated by Google; over 100,000 instances at Ant; over 40 million containers a day at Modal |
| S48 | Agache et al., Firecracker: Lightweight Virtualization for Serverless Applications, NSDI 2020 · https://www.usenix.org/conference/nsdi20/presentation/agache (paper: https://files.usenix.org/s3fs-public/cdn/nsdi20-paper-agache.pdf) | Lambda and Fargate; millions of workloads, trillions of requests a month; microVM as security boundary; jailer; rate limiters outside the guest |
| S49 | UK AI Security Institute, Sandboxed Execution · https://engineering-playbook.aisi.org.uk/isolate.html and The Inspect Sandboxing Toolkit, 7 August 2025 · https://www.aisi.gov.uk/blog/the-inspect-sandboxing-toolkit-scalable-and-secure-ai-agent-evaluations | T, H and N axes and their tiers; gVisor tier used for most agentic evaluations; adoption by other evaluators |
| S50 | CAPE Sandbox documentation · https://capev2.readthedocs.io/en/latest/introduction/what.html , https://capev2.readthedocs.io/en/latest/installation/host/routing.html and repository · https://github.com/kevoreilly/CAPEv2 | Host and isolated guests; routing default none; derived from Cuckoo; open source |
| S51 | AWS CloudTrail log file integrity validation · https://docs.aws.amazon.com/awscloudtrail/latest/userguide/cloudtrail-log-file-validation-intro.html , digest structure · https://docs.aws.amazon.com/awscloudtrail/latest/userguide/cloudtrail-log-file-validation-digest-file-structure.html , CLI · https://docs.aws.amazon.com/awscloudtrail/latest/userguide/cloudtrail-log-file-validation-cli.html | SHA-256 hashes; hourly signed digests; digest chaining; separate folder; command-line validation |
| S52 | Trillian README · https://github.com/google/trillian/blob/v1.7.3/README.md ; Verifiable data structures · https://transparency.dev/verifiable-data-structures/ ; Rekor specification · https://github.com/sigstore/architecture-docs/blob/main/rekor-spec.md ; Rekor overview · https://docs.sigstore.dev/logging/overview/ ; C2SP witness protocol · https://c2sp.org/tlog-witness%40main | Production use by Certificate Transparency log operators; signed tree heads; inclusion proofs with checkpoints; 99.5 % availability objective; witnesses cosign after a consistency check |
| S53 | Derczynski et al., garak: A Framework for Security Probing Large Language Models, arXiv 2406.11036 (preprint) · https://arxiv.org/abs/2406.11036 ; Erez et al., When Scanners Lie: Evaluator Instability in LLM Red-Teaming, arXiv 2603.14633 (preprint) · https://arxiv.org/abs/2603.14633 | What garak is; evaluator instability in 22 of 25 attack categories; success rates varying by up to 33 %. Both are preprints, not peer-reviewed |
| S54 | Küchler et al., Does Every Second Count? Time-based Evolution of Malware Behavior in Sandboxes, NDSS 2021 · https://doi.org/10.14722/ndss.2021.24475 | Recommendation to run samples for two minutes for classification or a behavioural report; most behaviour observed in the first two minutes |
| S55 | NIST NICE, The Cyber Range: A Guide (September 2023) · https://www.nist.gov/system/files/documents/2023/09/29/The%20Cyber%20Range_A%20Guide.pdf ; Yamin, Katt and Gkioulos, Cyber ranges and security testbeds, Computers & Security 2020 · https://doi.org/10.1016/j.cose.2019.101636 ; Lillemets et al., A Systematic Review of Cyber Range Taxonomies, Future Internet 2025 · https://doi.org/10.3390/fi17060259 | Virtualization as economic basis and protective barrier; taxonomy dimensions (monitoring, scoring, management, teaming, scenario). Read as search excerpts and abstracts only |
| S56 | Press Information Bureau, 2 December 2024 · https://pib.gov.in/PressReleaseIframePage.aspx?PRID=2079609 ; NFSU Centre of Excellence in Cyber Security · https://gujarat.nfsu.ac.in/department/coedetails/107 | Bharat National Cyber Range 1.0 by Rashtriya Raksha University; NFSU cyber range exercise certification and training reach |
| S57 | National Seva First Innovation Challenge site · https://sevafirst.mic.gov.in/tracks and https://sevafirst.mic.gov.in/ | Six common evaluation criteria. This is the national site; the Gujarat portal pages read list no rubric |
| S58 | VMware blog, 14 May 2026 · https://blogs.vmware.com/cloud-foundation/2026/05/14/announcing-vmware-workstation-and-fusion-26h1/ ; VirtualBox user manual · https://www.virtualbox.org/manual/UserManual.html and forum · https://forums.virtualbox.org/viewtopic.php?t=112113 ; Docker Engine on Ubuntu · https://docs.docker.com/engine/install/ubuntu/ ; AMD Ryzen 7 260 · https://www.amd.com/en/products/processors/laptop/ryzen/200-series/amd-ryzen-7-260.html | Workstation Pro free for commercial, educational and personal use; green turtle icon when a native hypervisor runs on the host; user reports of degraded speed (forum, self-reports); supported Ubuntu releases; 8 cores, 16 threads, AMD-V |
| S59 | Microsoft Learn, WSL · https://learn.microsoft.com/en-us/windows/wsl/wsl-config , https://learn.microsoft.com/en-us/windows/wsl/filesystems , https://learn.microsoft.com/en-us/windows/wsl/faq | Default memory 50 % of total; keep project files in the Linux file system; WSL 2 on Home editions |
| S60 | Claude Code setup · https://code.claude.com/docs/en/setup | Supported operating systems; 4 GB of RAM or more; native Windows or WSL |

## What was checked while preparing this pack, and what was not

Checked by execution:
- `contracts/audit_vectors.json`: generated with Python (`hashlib`, `cryptography` Ed25519), then independently
  re-verified with a JavaScript implementation using a different, iterative Merkle algorithm. The RFC 8032
  test key reproduced its published public key.
- The ten tamper verdicts: produced by a reference run of the algorithm in `04_CONTRACTS.md` section 7.8.
- `contracts/schema.sql`: applied on PostgreSQL 19.0 (PGlite build). Check constraints, the partial unique
  index, the append-only triggers and the role grants were exercised, and an audit record with non-ASCII text
  and escapes survived a `jsonb` round trip with identical canonical bytes.
- `contracts/rbac_matrix.yaml`: parses; 31 rules.

Not checked by execution (the agents must verify on your host, and the prompts say so):
- Everything involving Docker, gVisor, garak, YARA-X and the scanners on your actual machine.
- The code fragments in `08_TECHNICAL_IMPLEMENTATION.md`.
- The dependency allowlist names.
- Hardware sizing in the compatibility matrix.
- The `.claude/settings.json` rules on your installed agent version: test them once by asking the agent to
  edit `contracts/schema.sql`; it must be refused.
