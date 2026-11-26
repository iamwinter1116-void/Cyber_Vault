# Hand-off notes · Parth (role B)

The agent appends one note at the end of every session (prompt P-HANDOFF), in the format of
`docs/07_ANTI_HALLUCINATION.md` section 5. Newest at the bottom. Teammates read this file to learn what is
really finished: only what was run and seen belongs here.


## 2026-11-26 · B0 host preflight and spikes (scripts written; not yet run on the demo VM)
```
TASK: B0 · Host preflight and spikes (gate G0)
STATUS: partial -- scripts written and locally checked; "done when" needs Manas's primary Ubuntu VM
CHANGED: host/preflight.sh (new, 118 lines), host/setup_host.sh (new, 32 lines); total 150 = B0 limit
COMMANDS RUN (with exit codes), on Parth's Windows laptop (MINGW64_NT-10.0-26300, Git Bash), NOT the demo VM:
  $ git switch work/parth                      -> 0  (base 6dc40c8, tree was clean)
  $ sh -n / dash -n host/preflight.sh, host/setup_host.sh   -> 0 (all four)
  $ wc -l host/*.sh                            -> 118 + 32 = 150
  $ grep -nE 'privileged|cap_add|docker\.sock|network host|TODO|FIXME' host/*.sh -> 1 (no hits)
  $ sh host/preflight.sh (scratch copy)        -> 1
    FAIL 1 os: MINGW64_NT-10.0-26300/x86_64    (stops at check 1 as required; no later check ran)
    header also recorded: cpus=24 mem_kb=24786004 for this laptop
  $ check-1 case logic fed 4 /proc/version samples -> WSL2 FAIL, WSL1 FAIL, Ubuntu x86_64 PASS, aarch64 FAIL
  $ wsl.exe -d Ubuntu -- sh host/preflight.sh  -> could not start: Wsl/Service/CreateInstance/CreateVm/HCS/HCS_E_SERVICE_NOT_AVAILABLE
  $ sh host/setup_host.sh (non-root)           -> 1  "setup_host.sh: run as root (sudo)"
TESTS: none of T-ISO/T-RES run (not applicable before B1); preflight checks 2-10 and all three spikes NOT run
VERIFIED FACTS:
  Docker Engine apt install steps -- https://docs.docker.com/engine/install/ubuntu/ (read 2026-11-26 via a fetch tool; supports 24.04 and 26.04 LTS)
  gVisor apt install steps; apt package auto-configures an installed Docker; tarball path uses `runsc install` + `systemctl reload docker`
    -- https://gvisor.dev/docs/user_guide/install/ (read 2026-11-26)
  gateway_mode_ipv4=isolated is allowed only with --internal and assigns no bridge address
    -- https://docs.docker.com/engine/network/port-publishing/ (read 2026-11-26; page states no minimum Engine version)
UNVERIFIED / ASSUMED:
  - Fetched commands were extracted by a summarizing fetch tool; re-read both install pages on the VM before running setup_host.sh.
  - setup_host.sh: added -y; Docker's sources file written with printf instead of the page's `tee <<EOF` (same fields).
  - docker info --format field names (OperatingSystem, ServerVersion, CgroupVersion, CgroupDriver, Driver, DriverStatus,
    DockerRootDir, Runtimes) not checked against the installed Engine; a wrong name makes check 2 FAIL visibly.
  - busybox applets used by the spikes (nc -w, httpd -f -p, dd, tail, head -c) not checked on the pulled image;
    the network spike pairs every refusal with a positive control (peer reached, host listener up) so a broken nc FAILs, not PASSes.
  - Container cgroup directory located by `find /sys/fs/cgroup -name *<id>*`; path layout under runsc not yet observed.
  - Storage V1 relies on the local volume driver accepting o=loop; that is exactly what the spike measures.
  - Interpretations of mine, not stated in the docs: FAIL in checks 6-10 makes the final exit non-zero; "8 GB" = 7,812,500 kB MemTotal;
    "20 GB free" = 19,531,250 kB on DockerRootDir; spike image default busybox; public address default 1.1.1.1;
    CPU spike pass bound 57.5 % (115 % of --cpus 0.5, borrowed from T-RES-04); host listener on port 18080 via python3.
  - With zero sandbox/templates/*/template.yaml (none exist yet) check 10 passes and says "0 template.yaml files".
DEGRADED PATHS: none taken. If gateway_mode_ipv4=isolated is rejected, check 6 FAILs and the firewall fallback
  is NOT applied automatically (needs a team decision, docs/08 section 1 item 6).
NEW DEPENDENCIES: none installed. Host tools used at run time: docker, runsc, python3, mkfs.ext4, truncate, timedatectl, systemd-detect-virt.
OPEN RISKS / QUESTIONS FOR HUMANS:
  - Manas: please add Makefile target `preflight:` running `sh host/preflight.sh` (repo root), plus SSH access and a test
    window on the primary VM. Run `sudo sh host/setup_host.sh` once, then `sh host/preflight.sh` as a docker-group user.
  - Bhavya/Manas: preflight writes evidence/preflight.md (Bhavya's path); agree who commits it after the VM run.
  - CLAUDE.local.md is git-ignored at every depth (.gitignore:1), so team/parth/CLAUDE.local.md is absent from my clone.
  - Directory modes/owners for /var/lib/abhedya/{vol,quarantine,witness} are not specified; setup creates them root-owned default mode.
  - Snapshot the VM after B0 passes (team/parth/00_START_HERE.md item 5).
NEXT: run B0 on the primary VM and paste evidence/preflight.md here; then B1.
```

## 2026-11-26 · B0 review fix and B1 local slice (work order docs/16_BUILD_NOW_HOST_LATER.md, origin/work/manas c61b5ae)

```
TASK: B0 repair (Manas's review finding) and the locally testable part of B1. STATUS: partial.
  Local implementation evidence only. B0, B1, T-ISO-01, T-ISO-02 and every O1/G0 item stay OPEN.
HOST: Windows 11 laptop, Git Bash (MINGW64), Python 3.15.2, stdlib only. Not Linux; no Docker/runsc/PostgreSQL used.
TESTED COMMIT: 400dfe9b66ea04118ff16b8c0da30b6d711492f2 (tests re-run in a clean `git worktree` of that commit).
FILES CHANGED:
  28cf689 host/preflight.sh (2 lines, still 118; host/ total 150)
  400dfe9 services/runner/{__init__,launch,net,templates,state}.py, tests/unit/runner/{__init__,test_launch,test_templates,test_state}.py
B0 FIXES:
  1. res compared the check ID numerically; `res FAIL 7a ...` aborted with "[: 7a: integer expression expected"
     (finding in team/manas/work/JOURNAL.md). Now compares "${2%%[a-z]*}".
  2. `RV=$(runsc --version 2>&1 | head -1)` lost runsc's exit status, so a missing runsc was not caught there.
     Now captured first, trimmed after.
COMMANDS AND RESULTS:
  sh -n / dash -n host/preflight.sh and host/setup_host.sh -> exit 0 (all four)
  real res line extracted from the file, `res FAIL <id>` under set -eu:
    7a, 7b, 7c, 6, 10 -> continued, FAILED=1, exit 0;   5, 1 -> exit 1
  same harness with the HEAD~ res line and id 7a -> "[: 7a: integer expression expected", exit 1 (bug reproduced)
  runsc absent: new RV line -> res FAIL 3 called, exit 1; old RV line -> not caught, exit 0
  python -m unittest tests.unit.runner.test_launch tests.unit.runner.test_templates tests.unit.runner.test_state
    -> "Ran 22 tests ... OK", exit 0
  placeholder grep (TODO|FIXME|NotImplementedError|mock|simulat|STUB-G0|privileged=True|docker.sock|cap_add) on
    services/runner/*.py -> no hits (grep exit 1)
  committed blobs: 0 CR bytes in every host/, services/runner/, tests/unit/runner/ file
VERIFIED FACTS (source: docker-py 7.2.0, the current PyPI release per https://pypi.org/pypi/docker/json,
  upload 2026-07-09; files fetched from raw.githubusercontent.com/docker/docker-py/7.2.0/):
  - every key build_create_kwargs emits is in RUN_CREATE_KWARGS or RUN_HOST_CONFIG_KWARGS, or is `network`
    (popped in _create_container_args); checked by ast parsing, 0 unaccepted keys for both network modes.
  - containers.run() catches ImageNotFound and calls images.pull() (models/containers.py ~876-881). Section 8 says
    "pull policy never", so launch() uses containers.create() + start(); create() raises ImageNotFound instead.
    This deviates from the docs/08 section 3 snippet, which calls run().
  - HostConfig passes `mounts` through unchanged; nano_cpus and pids_limit must be int and are dropped when 0.
  - networks.create(name, ...) forwards to api.create_network(name, driver, options, ipam, check_duplicate, internal, labels, ...).
WHAT THE SLICE DOES (no Docker or DB call is exercised):
  launch.py  build_create_kwargs: runtime, user 1000:1000, cap_drop ALL, no-new-privileges, privileged False,
             read-only root, /tmp tmpfs rw,noexec,nosuid,size=64m, only the /workspace mount (volume or tmpfs; bind refused),
             nano_cpus/mem/memswap/pids, network abh-env-<id> or none, abh.* labels, name abh-<env>-<container>.
             Refuses: image not by sha256 digest, ABH_* env vars, non-positive/bool limits, bad names.
             choose_runtime: runsc -> gvisor; else runc-hardened only with allow_degraded; otherwise IsolationUnavailable.
  net.py     internal bridge, option com.docker.network.bridge.gateway_mode_ipv4=isolated, abh.* labels.
  templates.py  validates a parsed template mapping: exact keys, [T0.H2.N2] description prefix, exact container set per
             template (section 8), digests, share_pct sum 100, file-analysis containers network none; integer split
             (S: target 300m/153 MB, toolbox 200m/103 MB) whose sums equal the env limits.
  state.py   decide(observed, desired, expired) over all 36 schema combinations -> step + 7.6 audit action +
             section 6 activity kinds (env.state_changed always first).
NOT VERIFIED / NOT IMPLEMENTED (pending):
  - launch() and create_network() have never called a Docker daemon; no unit test fakes them.
  - Reconcile loop SQL (FOR UPDATE SKIP LOCKED, one short tx with abh_core.audit.append + activity insert),
    main loop, idempotent lookup-before-create, reaper, storage.py, YAML file loading: not written.
  - abh_core is on origin/work/henil only (core.abh_core, d3b772e); not imported yet.
  - ruff and mypy strict not run (not installed; no dependency added). `Any` remains only for the docker client/objects
    (docker-py ships no type stubs).
  - No template.yaml, Dockerfile, vulnerable app or toolbox image yet; digests can only come from real builds.
  - B0 preflight itself has still never run on Linux.
INTERPRETATIONS (mine, docs silent):
  - pids_limit is applied per container at the env's full value (section 8 says only "pids_limit"); the split rule in
    docs/08 covers CPU and memory only.
  - observed stopped + desired running is left unchanged: no start route exists (R11-R17, R30).
  - desired destroyed wins over expiry (audited env.destroyed, not env.expired).
  - requested + desired stopped (kill switch before provisioning) goes to stopped without creating anything.
  - Template yaml keys (name, title, description, sizes, containers[name, image, share_pct, command, env, network])
    are my definition inside sandbox/templates; no contract fixes them.
  - Image references accept repo@sha256:<64 hex> or a bare sha256:<64 hex> image ID.
NEW DEPENDENCIES: none installed. Runner will need docker, psycopg[binary,pool], pyyaml (all on the 03 section 6
  allowlist) once their registry check is recorded in evidence/VERSIONS.lock (Bhavya's path; coordinate who writes it).
BUDGET: services/runner 336 non-test lines so far (budget 800; B1 prompt budget 350, so the reconcile loop must stay small).
OPEN QUESTIONS: who appends runner deps to evidence/VERSIONS.lock; may I import core.abh_core before it reaches integration.
NEXT: Docker/DB-free remainder is small; next real slice is the reconcile SQL against real PostgreSQL once a
  Postgres is available to me (or on the Linux host), then B1 acceptance in Manas's test window.
```

## 2026-11-26 · B1/B3 local slice: reconcile DB loop, objects, reaper, storage, template loading

```
TASK: database reconcile loop, cleanup (reaper), storage ladder, template loading. STATUS: partial, local evidence only.
  B1, B3, T-ISO-01/02, T-RES-03/06 and every O1/O5/G0 item stay OPEN.
HOST: Windows 11, Git Bash, Python 3.15.2 stdlib only. No Docker daemon (Docker Desktop not running; WSL failed to
  start earlier with HCS_E_SERVICE_NOT_AVAILABLE), no PostgreSQL, no psycopg/docker/PyYAML installed.
TESTED COMMIT: 4b6dffb (parent 2327512).
FILES: services/runner/{reconcile,objects,storage,main}.py (new), launch.py, templates.py (changed),
  tests/unit/runner/{test_storage,test_reconcile_pg}.py (new), test_launch.py (changed).
COMMANDS AND RESULTS:
  python -m unittest tests.unit.runner.test_launch tests.unit.runner.test_templates tests.unit.runner.test_state
    tests.unit.runner.test_storage -> "Ran 30 tests ... OK", exit 0
  python -m unittest tests.unit.runner.test_reconcile_pg (no DSNs set) -> RuntimeError "set ABH_TEST_OWNER_DSN and
    ABH_TEST_RUNNER_DSN; this test is not skipped silently" (intended refusal; NOT a pass)
  python -m compileall -q services/runner tests/unit/runner -> exit 0
  placeholder grep on services/runner/*.py -> no hits; ast check: no function over 40 lines; 0 CR bytes in all files
  Combined check (temporary worktree of 4b6dffb, local merge of origin/work/henil 04d2df6, never pushed):
    no conflicts (git status empty after merge); all 9 names imported from core.abh_core.{audit,db,settings} are
    defined there; the 30 stdlib tests pass on the merged tree.
VERIFIED FROM SOURCE (upstream tags, fetched 2026-11-26): psycopg 3.3.9 Connection.execute/transaction, Cursor
  fetchone/fetchall, types.json.Jsonb; PyYAML 6.0.4 safe_load ("safe for untrusted input"); docker-py 7.2.0
  containers.get/list(all, filters)/status/start/stop/remove(force), networks.get/list/remove, volumes.create(name,
  driver, driver_opts, labels)/get/list/remove(force), client.info, errors.NotFound.
DESIGN:
  claim(): one tx, SELECT ... FOR UPDATE SKIP LOCKED LIMIT 20; requested rows become provisioning in that tx with an
    env.state_changed event (no audit action exists for provisioning in 7.6). The SQL excludes rows decide() leaves
    alone (failed/stopped not destroyed and not expired), so they cannot starve the LIMIT.
  Docker work with no transaction open; then one short tx: UPDATE ... WHERE observed_state = <expected> (stale write ->
    nothing written), append(env.*), activity events. Provision error -> destroy what exists -> failed + env.failed
    (outcome error, reason <= 500 chars, detail reason <= 200). Stop/destroy errors are logged and retried next pass.
  Degraded: isolation.degraded audit + alert.isolation_degraded [critical] naming T0.H1.N2.
  Reaper: labelled abh.managed=true containers/networks/volumes -> env ids -> LIVE_SQL -> destroy the rest.
  Storage: CHOSEN_METHOD = None until B0 check 8 chooses; provisioning refuses with StorageUnavailable until then.
  Workspace accepted by launch(): exactly {Target /workspace, Source abh-vol-<env id>, Type volume, ReadOnly False},
    or V3 tmpfs "size=<n>m,uid=1000,gid=1000" (HostConfig.Tmpfs, the form B0 tests). remove_image accepts only a
    canonical UUID (ids come from Docker labels).
INTERPRETATIONS (mine; please review):
  - pids_limit: every container gets the env's full pids_limit (only CPU/memory are split in docs/08) - Manas asked
    to keep this visible.
  - Runner audit Actor = (service, "runner", role "", team_id = env.team_id) so team-scoped audit views include env.*
    records; target_type "env", target_id env id (same as Henil's env routes).
  - Polling every 1 s, no LISTEN: no env-change NOTIFY channel exists in the contract.
  - Volume names abh-vol-<env id>; V1 image <ABH_VOLUME_DIR>/<env id>.img, assumes the runner sees the host path
    at the same path (mount volume dir at identical path in compose).
  - Labelled objects without abh.env_id are ignored by the reaper; a V1 image left without its volume (crash between
    the two steps) is only removed by that env's destroy.
NOT RUN / PENDING:
  - test_reconcile_pg.py on real PostgreSQL (Manas offered his Compose DB; commands below).
  - Anything in objects.py, main.py, make_image (mkfs.ext4), load_template: never executed.
  - ruff, mypy strict; runner Dockerfile, template.yaml files and images (no digests yet).
BUDGET: services/runner 730 physical lines / 520 code lines (no blanks, comments, docstrings) of 800. Collectors and
  jobs (B4-B7) still to come; which count make check-fast uses decides whether that fits.
NEW DEPENDENCIES: none installed. Registry evidence for Bhavya (evidence/VERSIONS.lock), from https://pypi.org/pypi/<name>/json
  read 2026-11-26T12:35Z, all on docs/03 section 6 allowlist:
    docker==7.2.0          uploaded 2026-07-09T14:53:45Z  Apache-2.0    requires_python >=3.8   github.com/docker/docker-py
    psycopg==3.3.9         uploaded 2026-11-12T08:58:18Z  LGPL-3.0-only >=3.10  author Daniele Varrazzo  psycopg.org
    psycopg-binary==3.3.9  uploaded 2026-11-12T08:58:23Z  LGPL-3.0-only >=3.10  (the [binary] extra)
    psycopg-pool==3.3.3    uploaded 2026-09-22T15:53:23Z  LGPL-3.0-only >=3.10  (the [pool] extra)
    PyYAML==6.0.4          uploaded 2026-11-20T23:34:39Z  MIT           >=3.10  author Kirill Simonov  pyyaml.org
  Also needed at run time through core.abh_core: pydantic-settings (Henil's dependency).
FOR MANAS (DB test on a DISPOSABLE Compose database; it writes permanent audit rows and refuses if any live env row exists):
  git worktree add ../cv-combo origin/work/parth && cd ../cv-combo && git merge --no-edit origin/work/henil   # local only
  python -m venv .venv && . .venv/bin/activate && pip install "psycopg[binary,pool]==3.3.9" pydantic-settings
    (only after the VERSIONS.lock entries exist)
  ABH_TEST_OWNER_DSN=postgresql://postgres:<owner pw>@<db host>:5432/abhedya \
  ABH_TEST_RUNNER_DSN=postgresql://abh_runner:<runner pw>@<db host>:5432/abhedya \
  python -m unittest -v tests.unit.runner.test_reconcile_pg
  Expect 6 tests. The db service publishes no port and sits on the internal control network, so this must run from a
  container on that network or with a temporary port mapping you choose; please paste output and exit code.
NEXT: B4 collectors (pure threshold logic first), templates/images on a Linux host, then B1 acceptance in a test window.
```

## 2026-11-26 · Reaper review cases (Manas) · commit ee0bb65

```
TASK: Manas's two cleanup cases. STATUS: code done locally; Docker behaviour unexecuted (Linux host pending).
CASE 1 abh.managed=true object with missing or non-canonical abh.env_id:
  Before: ignored (labelled_env_ids discarded "" ids; a bogus id reached destroy(), whose remove_image raised).
  Now: found by the reaper's label listing (_managed: containers, networks, volumes filtered abh.managed=true);
  removed directly by remove_unowned() in that order (containers first so networks/volumes are free).
  Contract basis: section 8 lifetime "The reaper removes any labelled object whose env row is destroyed or
  missing"; an object with no usable env id has no row, so this is the "missing" case. No CR needed, in my reading.
  Risk to state: anything else on the daemon labelled abh.managed=true is removed; preflight uses abh.preflight=true,
  and R-23 already requires one stack per daemon.
CASE 2 V1 image left behind (crash after make_image, before volumes.create):
  Found: storage.image_env_ids(ABH_VOLUME_DIR) lists regular files named <canonical uuid>.img or .img.tmp; those
  ids join the labelled ids before the LIVE_SQL check. Removed: destroy(id) -> remove_image. Only files of a non-live
  env (row destroyed or missing) are removed; requested/provisioning/running/stopped/failed rows keep theirs.
  Other file names, directories and upper-case ids are never touched. Image files are not Docker objects, so this
  is implementation detail of docs/08 section 4 V1, not a contract change.
  Residual (stated, not fixed): a failed env whose cleanup also failed keeps objects/image until its row is destroyed.
COMMANDS AND RESULTS (Windows, Python 3.15.2, stdlib):
  python -m unittest tests.unit.runner.test_launch tests.unit.runner.test_templates tests.unit.runner.test_state
    tests.unit.runner.test_storage -> "Ran 32 tests ... OK", exit 0 (new: test_image_env_ids_finds_orphan_images_only,
    test_canonical_id)
  compileall exit 0; placeholder grep no hits; 0 CR bytes.
  Temporary merge of ee0bb65 with origin/work/henil 053e32c: merge exit 0, no conflicts, 32 tests OK; Actor, Outcome,
    append, record_hash, create_pool, transaction, Settings all still defined there.
BUDGET: services/runner 781 physical / 557 code lines of 800.
STILL OPEN: B1, T-ISO-01/02, T-RES-03/06, all Docker/runsc/storage acceptance; test_reconcile_pg.py not yet run
  (Manas will run it in a disposable Compose project after Bhavya records the dependencies). pids_limit per
  container remains an interpretation (matches docs/08 section 3 example) until docker inspect and resource tests pass.
```
