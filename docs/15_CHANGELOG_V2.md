# 15 · What changed from version 1 to version 2 (25 November 2026)

## Structure
| Change | Reason |
| --- | --- |
| New `team/` folder with `parth/`, `henil/`, `bhavya/` | Each person finds all their own files in one place |
| `docs/10_MEMBER_A.md`, `11_MEMBER_B.md`, `12_MEMBER_C.md` moved to `team/henil/02_PROMPTS.md`, `team/parth/02_PROMPTS.md`, `team/bhavya/02_PROMPTS.md` | Same reason. Every cross-reference was updated |
| Per person: `00_START_HERE.md`, `01_DEVICE_SETUP.md`, `03_MY_OBJECTIVES_AND_TESTS.md`, `CLAUDE.local.md`, `work/JOURNAL.md`, `work/HANDOFFS.md` | Personal clock, machine-specific setup, own slice of objectives, an agent that knows its person and machine, journals that three people never edit at once |
| New `README.md`, `.gitignore`, `docs/14_PRIOR_ART.md`, this file | Map of the pack; keep local files and secrets out of git; precedents; traceability |
| Shared contracts and documents stay in one copy under `contracts/` and `docs/` | Three copies would drift within a day |

## Roles and machines
| Change | Reason |
| --- | --- |
| Parth = role B and demo host; Henil = role A and backup host; Bhavya = role C | The sandbox runtime needs a full Linux VM [S9][S10]; the 24 GB laptop is the one that can carry it |
| Demo VM: Ubuntu Server 24.04 LTS, 6 virtual CPUs, 12 GB, VMware Workstation Pro or VirtualBox | Docker supports that release; VMware Workstation Pro is free [S58]; sizes are planning numbers |
| Henil and Bhavya develop in WSL 2; all full-stack checks run on the demo VM | WSL 2 is fine for code that starts no sandbox; file-system and memory facts from Microsoft [S59] |
| GPUs are unused by mandatory objectives | The AI target is a stub chosen for offline, in-sandbox operation |
| One stack per Docker daemon, operated by Parth (risk R-23) | Two reapers would delete each other's sandboxes |

## Schedule
| Change | Reason |
| --- | --- |
| Start moved to 25 November 19:00; clock times replace hour offsets; three tripwires added | About 23 working hours remain before the freeze, against a gate plan written for 32 |

## Agent control
| Change | Reason |
| --- | --- |
| Deny rules now start with `/`, which anchors them at the project root | A pattern without the leading slash is relative to the current directory [S42]; a session started in a subfolder could have slipped past |
| New deny rules for `team/*.md`, `team/*/*.md`, `README.md`, `CLAUDE.local.md`; `team/*/work/` stays writable | In these patterns `*` matches within one path segment only [S42] |
| P-GROUND asks which machine the agent is on; P-HANDOFF and P-UNSTICK write into `team/<name>/work/` | Failure mode F11 (right command, wrong machine); hand-offs become readable by teammates |
| Two new failure modes, F11 and F12 | Three laptops with different roles; precedents must not be used as proof |

## Design changes taken from proven systems
See `14_PRIOR_ART.md` section 2 (M1 to M11). In short: isolation profile labels, a 120-second detonation
deadline, three new stated limits (L8, L9, L10), planted flags for the break-it session, a clean-up assertion
in T-WL-02, two new stretch objectives (S7, S8), a precedent slide, a scoring-criteria map.

## New risks
R-20 venue network · R-21 Windows hypervisor slows the VM · R-22 WSL file system · R-23 two runners ·
R-24 untested backup host · R-25 scanner score presented as fact · R-26 "clean" read as "safe" ·
R-27 finalist list and finale format.

## Not changed
`contracts/schema.sql`, `contracts/rbac_matrix.yaml`, `contracts/audit_vectors.json`, sections 2 to 11 of
`04_CONTRACTS.md`, the nine mandatory objectives, the dependency allowlist, the code budgets, the ten hard rules.

## Not verified by execution in version 2
Nothing new was executed for this version. The VM sizes, the network options, the export and import of the VM,
the behaviour of the new deny rules on your installed agent version, and every command on your three laptops
remain to be checked by you. The guard-rail test in `00_START_HERE.md` step 4 checks the deny rules.
