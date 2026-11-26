# Hand-off notes · Bhavya (role C)

The agent appends one note at the end of every session (prompt P-HANDOFF), in the format of
`docs/07_ANTI_HALLUCINATION.md` section 5. Newest at the bottom. Teammates read this file to learn what is
really finished: only what was run and seen belongs here.

```
TASK: C0 Contract test harness & C1 Independent verifier (T-KAT-01..04, T-AUD-05, T-RBAC-01..04,07,09..12)
STATUS: partial (verifier and contract test harness done; core/API/stack checks blocked on Manas M1 scaffold and Henil core/API)
CHANGED:
  - tools/verify_audit.py (178 lines, new)
  - tests/contract/conftest.py (new)
  - tests/contract/test_audit_vectors.py (new)
  - tests/contract/test_rbac_matrix.py (new)
  - evidence/VERSIONS.lock (new)
COMMANDS RUN (with exit codes):
  $ (Get-Content d:\Cyber_Vault\tools\verify_audit.py).Count -> 0 (178)
  $ python d:\Cyber_Vault\tools\verify_audit.py --help -> 0
  $ python -m pytest d:\Cyber_Vault\tests\contract --collect-only -q -> 0 (211 tests collected in 1.38s)
  $ python -m pytest d:\Cyber_Vault\tests\contract\test_audit_vectors.py -k "verifier or exit_3 or t_aud_05" --hypothesis-show-statistics -q -> 0 (22 passed; Hypothesis: 60 passing, 0 failing, 0 invalid)
  $ python -m pytest d:\Cyber_Vault\tests\contract\test_audit_vectors.py -k "core" -q -> 1 (7 failed: abh_core.audit not available yet)
TESTS:
  - Passed: T-KAT-01..04 (verifier side, 10 tamper_cases + witness), exit-3 forbidden-input checks (4 cases), T-AUD-05 (60 Hypothesis examples)
  - Failed (expected, missing dependency): T-KAT-01..03 (core side: abh_core.audit not present)
  - Not run against live stack: T-RBAC-01..04, 07, 09..12 (Manas M1 scaffold and Henil API not present)
VERIFIED FACTS:
  - PyPI registry metadata for cryptography (50.0.2), pyyaml (6.0.4), pytest (9.2.0), hypothesis (6.170.17), httpx (0.28.1) checked via https://pypi.org/pypi/<name>/json and recorded in evidence/VERSIONS.lock.
  - tools/verify_audit.py is 178 lines (within 180-line budget) and imports only stdlib + cryptography.
UNVERIFIED / ASSUMED:
  - core/abh_core.audit conformance (T-KAT-01..03 core side) and live API RBAC enforcement (T-RBAC-*) unverified until Henil/Manas deliver scaffold and services.
DEGRADED PATHS: none
NEW DEPENDENCIES:
  - hypothesis==6.170.17 (PyPI verified, allowlisted in docs/03_CONTEXT.md section 6, recorded in evidence/VERSIONS.lock)
  - httpx==0.28.1 (PyPI verified, allowlisted in docs/03_CONTEXT.md section 6, recorded in evidence/VERSIONS.lock)
OPEN RISKS / QUESTIONS FOR HUMANS:
  - Waiting on Manas M1 scaffold (Makefile, pyproject.toml, compose.yaml) and Henil core/abh_core + services/api.
  - Local GitHub push credentials for solankibhavyadeepsinh-hub are not yet cached in Windows Credential Manager.
NEXT: C2 Security test suite (after C1 PR is merged and Parth/Manas/Henil runtime/API are available)
```

```
TASK: C2 Security test suite & tamper drill tool (T-ISO-01..07, T-STATIC-01, T-RES-01..06, T-AUD-01..04, 06..08, T-MON-01..04)
STATUS: partial (all 25 security tests and tamper_drill.py implemented and collected; live-stack execution blocked until Manas primary VM stack, Henil API, and Parth runner/probes are available)
CHANGED:
  - tools/tamper_drill.py (new)
  - tests/security/__init__.py (new)
  - tests/security/conftest.py (new)
  - tests/security/test_isolation.py (new)
  - tests/security/test_resources.py (new)
  - tests/security/test_audit_security.py (new)
  - tests/security/test_monitoring.py (new)
COMMANDS RUN (with exit codes):
  $ python d:\Cyber_Vault\tools\tamper_drill.py --help -> 0
  $ python d:\Cyber_Vault\tools\tamper_drill.py --case edit_field_no_rehash -> 2 (REFUSED: set ABH_ALLOW_TAMPER_DRILL=1 to run tamper-drill.)
  $ python -m pytest d:\Cyber_Vault\tests\security --collect-only -q -> 0 (25 tests collected in 0.56s)
  $ python -m pytest d:\Cyber_Vault\tests\security\test_isolation.py::test_t_static_01_compose_and_runner_no_dangerous_flags -q -> 1 (AssertionError: compose.yaml missing (Manas M1 scaffold not present))
TESTS:
  - Collected (25/25): T-ISO-01..07, T-STATIC-01, T-RES-01..06, T-AUD-01..04, T-AUD-06..08, T-MON-01..04
  - Failed (expected, missing stack): T-STATIC-01 (compose.yaml missing)
  - Not run against live stack: T-ISO-01..07, T-RES-01..06, T-AUD-01..04, 06..08, T-MON-01..04
VERIFIED FACTS:
  - Trigger names in contracts/schema.sql: audit_no_update_delete, audit_no_truncate.
  - Probe script names from team/parth/02_PROMPTS.md task B2: probe_connect, probe_env, probe_write, mem_hog, fork_bomb, disk_fill, cpu_burn.
UNVERIFIED / ASSUMED:
  - Live execution of all 25 security tests and tamper_drill.py against PostgreSQL + Docker/runsc on Manas's primary Ubuntu VM.
DEGRADED PATHS: none
NEW DEPENDENCIES: none (psycopg is lazy-imported in tools/tamper_drill.py and T-AUD-03/07 for VM execution)
OPEN RISKS / QUESTIONS FOR HUMANS:
  - Handoff to Manas: wire `tamper-drill` target in Makefile to invoke `python tools/tamper_drill.py --case $(CASE)`.
  - Next tasks C3..C6 (web console) depend on contracts/openapi.yaml from Manas/Henil at G0.
NEXT: C3 Console shell, login, environments (once contracts/openapi.yaml and Manas/Henil stack are available), or run C2 against Manas's primary VM.
```

```
TASK: C0/C2/C7/C8 Remaining independent test & evidence slice (T-AUTH-01..05, T-API-01, T-WL-01..03, T-E2E-01..04, evidence collector)
STATUS: partial (all test suites and evidence collector implemented and collected; live-stack execution and C3-C6 web/ UI await contracts/openapi.yaml and Manas/Henil/Parth stack)
CHANGED:
  - tests/contract/test_auth_contract.py (new)
  - tests/contract/test_openapi_conformance.py (new)
  - tests/security/test_workloads.py (new)
  - tests/e2e/test_demo_journeys.py (new)
  - tools/collect_evidence.py (new)
  - evidence/INDEX.md, evidence/bug-journal.md, evidence/prior-art.md (generated)
COMMANDS RUN (with exit codes):
  $ python -m pytest d:\Cyber_Vault\tests\contract --collect-only -q -> 0 (217 tests collected in 1.63s)
  $ python -m pytest d:\Cyber_Vault\tests\security --collect-only -q -> 0 (28 tests collected in 0.61s)
  $ python -m pytest d:\Cyber_Vault\tests\e2e --collect-only -q -> 0 (4 tests collected in 0.47s)
  $ python d:\Cyber_Vault\tools\collect_evidence.py --repo-root d:\Cyber_Vault -> 0
TESTS:
  - Collected: 217 contract tests, 28 security tests, 4 e2e tests
  - Not run against live stack: T-AUTH-01..05, T-API-01, T-WL-01..03, T-E2E-01..04
VERIFIED FACTS:
  - tools/collect_evidence.py generated evidence/INDEX.md, evidence/bug-journal.md, and evidence/prior-art.md from repository docs.
UNVERIFIED / ASSUMED:
  - Live-stack execution of auth, OpenAPI conformance, workload, and Playwright E2E tests.
DEGRADED PATHS: none
NEW DEPENDENCIES: none (schemathesis and playwright are lazy-imported when those suites run)
OPEN RISKS / QUESTIONS FOR HUMANS:
  - Handoff to Manas: wire `evidence` target in Makefile to invoke `python tools/collect_evidence.py`.
  - C3..C6 (web/) remain blocked until contracts/openapi.yaml is generated by Manas/Henil at G0.
NEXT: C3 Console shell, login, environments (once contracts/openapi.yaml lands on integration).
```

```
TASK: Probe contract alignment with Parth (2075dbf) for T-ISO-03 and T-WL-01
STATUS: done (local test alignment; live-stack execution awaits primary VM)
CHANGED:
  - tests/security/test_isolation.py (updated T-ISO-03 for probe_connect, probe_icmp with sent check, and probe_dns)
  - tests/security/test_workloads.py (parsed JSON line in T-WL-01 instead of literal string match)
FOR PARTH (probe contract response):
  - Agreed on all 5 probe JSON schemas in team/parth/work/HANDOFFS.md (2075dbf): probe_connect, probe_icmp, probe_dns, probe_env, probe_write.
  - For T-ISO-03 ICMP under cap_drop=ALL: updated test_t_iso_03_cross_team_network_isolation so ICMP asserts reachable==False only when sent==True, and records icmp_note via pytest record_property (in JUnit XML) as not testable when sent==False rather than counting an unsent probe as isolation evidence.
```

```
TASK: Fix Manas & Parth review gaps in VERSIONS.lock, collect_evidence, T-ISO-04..06, T-MON-02/04, T-WL-02, exec_in_env
STATUS: done (local updates verified; live-stack execution awaits Manas primary VM)
CHANGED:
  - evidence/VERSIONS.lock (added docker==7.2.0, psycopg-binary==3.3.9, pydantic-settings==2.16.3; updated pyyaml==6.0.4)
  - tools/collect_evidence.py (normalized trailing newline in evidence/bug-journal.md)
  - evidence/bug-journal.md, evidence/INDEX.md, evidence/prior-art.md (regenerated)
  - tests/security/conftest.py (exec_in_env deadline 65s -> 75s)
  - tests/security/test_isolation.py (T-ISO-04 bridge gateway check; T-ISO-05 exec/stream check; T-ISO-06 mounts & docker.sock check)
  - tests/security/test_monitoring.py (T-MON-02 30s SSE >=6 metrics; T-MON-04 10 events replayed once in order)
  - tests/security/test_workloads.py (T-WL-02 detonation case, mode-0400 quarantine check, container/network/volume cleanup, EICAR source comment)
OPEN NOTE FOR MANAS & PARTH:
  - Acknowledged Parth's probe additions (probe_env mounts & cap_eff, disk_fill).
  - Remaining CR/discussion items: T-ISO-01 (degraded-mode alert branch vs strict runsc) and T-ISO-03 (unsent ICMP under cap_drop=ALL) if a CR is needed for docs/06_VERIFICATION.md.
```

```
TASK: Manas review fixes — Phase 1 (RBAC tests), Phase 2 (VERSIONS.lock + collect_evidence.py LF), Phase 3 (T-ISO-03/04/05)
STATUS: partial (all local review fixes, collection, T-RBAC-05, T-KAT-01..04, T-AUD-05, T-STATIC-01 verified; live-stack contract/security/E2E suites await Manas primary VM)
CHANGED:
  - tests/contract/test_rbac_matrix.py (T-RBAC-03 real owned objects + exact 403; T-RBAC-02 real cross-team objects + bravo owner control + exact 404; T-RBAC-01 real resource IDs + 2xx for allowed roles; T-RBAC-05 route-set & startup-refusal check)
  - evidence/VERSIONS.lock (restored explicit psycopg-binary==3.3.9 and psycopg-pool==3.3.3; added PyPI-verified argon2-cffi==25.1.0, fastapi==0.165.0, pydantic==2.14.4, uvicorn==0.54.0, python-multipart==0.0.34, ruff==0.17.6, mypy==2.4.1)
  - tools/collect_evidence.py (deterministic LF output and trailing-whitespace stripping)
  - evidence/INDEX.md, evidence/bug-journal.md, evidence/prior-art.md (regenerated cleanly with LF)
  - tests/security/test_isolation.py (T-ISO-03 fails if ICMP sent==False; T-ISO-04 inspects actual Docker network Gateway/isolated mode without .1 assumption; T-ISO-05 verifies bravo stream control and checks alpha stream over bounded 5s window)
COMMANDS RUN (with exit codes):
  $ python d:\Cyber_Vault\tools\collect_evidence.py --repo-root d:\Cyber_Vault (run twice) -> 0
  $ git -C d:\Cyber_Vault diff --check -> 0 (clean)
  $ python -m py_compile ... -> 0
  $ python -m pytest d:\Cyber_Vault\tests\contract --collect-only -q -> 0 (216 tests collected in 1.80s)
  $ python -m pytest d:\Cyber_Vault\tests\security --collect-only -q -> 0 (28 tests collected in 0.92s)
  $ python -m pytest d:\Cyber_Vault\tests\e2e --collect-only -q -> 0 (4 tests collected in 0.67s)
  $ python -m pytest tests/contract/test_rbac_matrix.py::test_t_rbac_05_registered_routes_match_matrix tests/contract/test_audit_vectors.py tests/security/test_isolation.py::test_t_static_01_compose_and_runner_no_dangerous_flags -q -> 0 (31 passed in 21.36s)
TESTS:
  - Passed locally (31): T-RBAC-05, T-KAT-01..04 (core + verifier), T-AUD-05 (60 Hypothesis examples), T-STATIC-01
  - Unrun live-stack tests (need Manas primary VM + full Compose stack + Parth sandbox images): T-RBAC-01..03, 07, 09..12; T-AUTH-01..05; T-API-01; T-ISO-01..07; T-RES-01..06; T-AUD-01..04, 06..08; T-MON-01..04; T-WL-01..03; T-E2E-01..04
VERIFIED FACTS:
  - PyPI metadata verified via https://pypi.org/pypi/<pkg>/json for all 7 newly recorded packages in evidence/VERSIONS.lock.
  - services/api/main.py create_app() matches all 31 rules in contracts/rbac_matrix.yaml and verify_route_coverage(..., require_all=True) raises RuntimeError on unmapped routes.
UNVERIFIED / ASSUMED:
  - All live-stack contract, security, and E2E tests remain unrun until Manas's primary Ubuntu VM stack is up.
DEGRADED PATHS: none
NEW DEPENDENCIES: none installed locally in this phase (only recorded in evidence/VERSIONS.lock)
OPEN RISKS / QUESTIONS FOR HUMANS:
  - T-ISO-03 fails if ICMP cannot send under cap_drop=ALL; requires team CR on docs/06_VERIFICATION.md or CAP_NET_RAW decision.
  - C3..C6 (web/) remains intentionally absent until Manas lands contracts/openapi.yaml and the real service stack.
NEXT: Open PR from work/bhavya to integration for Manas review; start C3 once contracts/openapi.yaml is merged.
```

```
TASK: Quota-safe RBAC fixtures + BR1..BR4 (T-RBAC-09..12) + PROBE_CONTRACT.md v2 alignment (T-RES-01..03, T-WL-01, T-ISO-06)
STATUS: partial (all local tests pass; live-stack and Linux/runsc host tests remain unrun until primary VM stack is up)
CHANGED:
  - tests/contract/test_rbac_matrix.py (module-scoped real_rbac_ids fixture with cleanup, exec job instead of stub-vulnerable, real BR1..BR4 409 checks in T-RBAC-09..12)
  - tests/security/test_resources.py (T-RES-01 alert.oom_killed <=5s, env.oom_killed audit, neighbor 1s loop; T-RES-02 30s healthz/neighbor window + destroy <=15s; T-RES-03 exit_code==1 + errno==ENOSPC + bytes_written<=storage_mb*1048576)
  - tests/security/test_workloads.py (T-WL-01 probe_dns target 3 resolved==False)
  - tests/security/test_isolation.py (T-ISO-06 cap_eff==0000000000000000 + EROFS/read-only error check)
COMMANDS RUN (with exit codes):
  $ python -m py_compile ... -> 0
  $ git -C d:\Cyber_Vault diff --check -> 0
  $ python -m pytest d:\Cyber_Vault\tests\contract --collect-only -q -> 0 (216 tests collected in 1.97s)
  $ python -m pytest d:\Cyber_Vault\tests\security --collect-only -q -> 0 (28 tests collected in 0.98s)
  $ python -m pytest d:\Cyber_Vault\tests\e2e --collect-only -q -> 0 (4 tests collected in 0.52s)
  $ python -m pytest tests/contract/test_rbac_matrix.py::test_t_rbac_05_registered_routes_match_matrix tests/contract/test_audit_vectors.py tests/security/test_isolation.py::test_t_static_01_compose_and_runner_no_dangerous_flags -q -> 0 (31 passed in 20.54s)
TESTS:
  - Passed locally (31): T-RBAC-05, T-KAT-01..04 (core + verifier), T-AUD-05 (60 Hypothesis examples), T-STATIC-01
  - Still requires Linux/runsc host + full Compose stack: T-ISO-01..07, T-RES-01..06, T-AUD-01..04, 06..08, T-MON-01..04, T-WL-01..03, T-E2E-01..04, T-RBAC-01..03, 07, 09..12, T-AUTH-01..05, T-API-01
CONTRACT CONFLICT FOR TEAM REVIEW:
  - T-RES-02 (docs/06_VERIFICATION.md s5): docs/06 states "afterwards the environment stops and is removed within 15 s", whereas services/runner has no automatic post-fork-bomb stop rule. Test currently issues DELETE /envs/{id} after the 30 s stress window and asserts removal <= 15 s; team decision needed on whether runner should auto-stop on fork-bomb or docs/06 should be updated via CR.
NEXT: Manas reviews PR from work/bhavya to integration; Bhavya runs live suites on primary VM and starts C3 once contracts/openapi.yaml lands.
```

```
TASK: PR #20 review fixes (RBAC wait_running/cleanup, T-RES-01..06, T-ISO-04 toolbox+target, T-WL-01 unique target DNS)
STATUS: partial (all local checks pass; all Linux/runsc and live-stack checks remain unrun until primary VM stack is up)
CHANGED:
  - tests/contract/test_rbac_matrix.py (real_rbac_ids waits for observed_state=running before exec; _delete_env asserts 202 and waits for destroyed/failed)
  - tests/security/conftest.py (added delete_env_and_wait helper)
  - tests/security/test_resources.py (T-RES-01 neighbor loop across stress + <=5s alert from OOM; T-RES-02 Docker objects removed <=15s + record_property limit evidence; T-RES-03 host free space bound + neighbor write; T-RES-05 exact 409 QUOTA_EXCEEDED without 201; T-RES-06 network/volume cleanup + runner restart convergence; finally cleanup everywhere)
  - tests/security/test_isolation.py (T-ISO-04 probes from both toolbox and target; detonator conditional on ABH_ENABLE_DETONATION)
  - tests/security/test_workloads.py (T-WL-01 tests alpha unique target container name via probe_dns + probe_connect from bravo + cleanup)
COMMANDS RUN (with exit codes):
  $ python -m py_compile ... -> 0
  $ git -C d:\Cyber_Vault diff --check -> 0
  $ python -m pytest d:\Cyber_Vault\tests\contract --collect-only -q -> 0 (216 tests collected in 1.47s)
  $ python -m pytest d:\Cyber_Vault\tests\security --collect-only -q -> 0 (28 tests collected in 0.67s)
  $ python -m pytest d:\Cyber_Vault\tests\e2e --collect-only -q -> 0 (4 tests collected in 0.55s)
  $ python -m pytest tests/contract/test_rbac_matrix.py::test_t_rbac_05_registered_routes_match_matrix tests/contract/test_audit_vectors.py tests/security/test_isolation.py::test_t_static_01_compose_and_runner_no_dangerous_flags -q -> 0 (31 passed in 17.58s)
TESTS:
  - Passed locally (31): T-RBAC-05, T-KAT-01..04 (core + verifier), T-AUD-05 (60 Hypothesis examples), T-STATIC-01
  - Unrun Linux/runsc & live-stack checks: T-ISO-01..07, T-RES-01..06, T-AUD-01..04, 06..08, T-MON-01..04, T-WL-01..03, T-E2E-01..04, T-RBAC-01..03, 07, 09..12, T-AUTH-01..05, T-API-01
OPEN ITEMS FOR TEAM:
  - T-RES-02 contract note: runner has no auto-stop on fork bomb; test issues DELETE after 30s window per Manas's procedure in PROBE_CONTRACT.md v3.
  - R21 / T-WL-03 stub-target conflict remains open for the four-person O9 CR (not counted as working).
NEXT: Manas reviews updated PR #20 (work/bhavya -> integration); run live suites on Linux/runsc primary VM once stack is up.
```

```
TASK: PR #20 follow-up fixes (T-RES-01..06, T-ISO-04) + explicit C decisions on Parth's CR_ENTRIES_FOR_09.md
STATUS: partial (all local checks pass; all Linux/runsc and live-stack checks remain unrun until primary VM stack is up)
CHANGED:
  - tests/security/test_resources.py (T-RES-01 5s alert delta from OOM timestamp; T-RES-02 assert PidsLimit + fork_bomb errno and clean up env_hostile in finally; T-RES-03 free_before after provisioning and strict <= storage_mb bound without +16 MiB; T-RES-04 measure avg CPU pct <= 115% over 20s burn; T-RES-05 assert denied env.create audit record and Team.usage == SQL sum; T-RES-06 assert provisioning state before runner restart + exact 2 containers, 1 network, 1 volume)
  - tests/security/test_isolation.py (T-ISO-04 removed ABH_ENABLE_DETONATION env bypass; detonator check always runs unless docs/02 cut is recorded)
CR DECISIONS (Bhavya = role C, from team/parth/work/CR_ENTRIES_FOR_09.md):
  - CR 1 (docs/03_CONTEXT.md s6: python:3.13-slim-trixie by digest, curl in toolbox, stdlib probes, transitive deps with sha256 in VERSIONS.lock): C = YES
  - CR 2 (docs/05_OBJECTIVES.md: services/runner code budget 800 -> 1000 for B6 file analysis): C = YES
COMMANDS RUN (with exit codes):
  $ python -m py_compile ... -> 0
  $ git -C d:\Cyber_Vault diff --check -> 0
  $ python -m pytest d:\Cyber_Vault\tests\contract --collect-only -q -> 0 (216 tests collected in 1.81s)
  $ python -m pytest d:\Cyber_Vault\tests\security --collect-only -q -> 0 (28 tests collected in 0.70s)
  $ python -m pytest d:\Cyber_Vault\tests\e2e --collect-only -q -> 0 (4 tests collected in 0.56s)
  $ python -m pytest tests/contract/test_rbac_matrix.py::test_t_rbac_05_registered_routes_match_matrix tests/contract/test_audit_vectors.py tests/security/test_isolation.py::test_t_static_01_compose_and_runner_no_dangerous_flags -q -> 0 (31 passed in 17.24s)
TESTS:
  - Passed locally (31): T-RBAC-05, T-KAT-01..04 (core + verifier), T-AUD-05 (60 Hypothesis examples), T-STATIC-01
  - Unrun Linux/runsc & live-stack checks: T-ISO-01..07, T-RES-01..06, T-AUD-01..04, 06..08, T-MON-01..04, T-WL-01..03, T-E2E-01..04, T-RBAC-01..03, 07, 09..12, T-AUTH-01..05, T-API-01
  - Open CR: R21 / T-WL-03 stub-target conflict remains pending the four-person O9 CR.
NEXT: Manas reviews updated PR #20 (work/bhavya -> integration); run live/Linux suites on primary VM once stack is up.
```

