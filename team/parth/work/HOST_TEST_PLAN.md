# Linux host test plan · role B (Parth) acceptance items · 2026-11-26

For Manas's test window on the demo host only (Docker Engine + runsc). Nothing here has run. WSL and Docker
Desktop results do not count (CLAUDE.md). One stack per daemon (R-23): the reaper removes every
`abh.managed=true` object it does not own. Each step records command, exit code, output, host and commit.
Steps that need sandbox images wait for the image CR; steps marked [no images] can run first.

## 0. Host identity (before any sandbox check; team/parth/CLAUDE.local.md)
`uname -a` · `cat /proc/version` · `docker version` · `docker info --format '{{json .Runtimes}}'` · `runsc --version`

## 1. B0 preflight [no images]
`make preflight` (host/preflight.sh), full output pasted. Records the storage method of check 8; only then is
`storage.CHOSEN_METHOD` set, by a commit. Measurements Manas asked to keep open:
- Docker socket: `stat -c '%u %g %a %n' /var/run/docker.sock` -> the group id the non-root runner user joins
  (no chmod 666, no privileged, no added capability).
- V1 only if check 8 picks it: the volume's `device` path must be the same path inside the runner container and
  on the host; check with `docker volume inspect abh-vol-<env_id>` and `ls -l` of that path on the host.

## 2. B1 provisioning and profile (T-ISO-01, T-ISO-02, T-RES-06)
- Insert a `requested` app-target row; observe `running` within 20 s (B1 done-when).
- `docker inspect` of every `abh.managed=true` container, pasted, against every row of docs/04 section 8.
- Kill the runner during provisioning, restart it: exactly one set of containers/network/volume per env.
- Per-container `pids_limit` interpretation: read `HostConfig.PidsLimit` of each container and record it.

## 3. B5 exec (supports T-E2E-01, T-RBAC-12; R-14)
Through R17 as analyst.alpha, each result pasted from GET /jobs/{id}:
- hostile command `a'b"c; echo $(id) \`id\` > /tmp/x; cat /tmp/x` -> runs only inside the sandbox (output shows
  uid 1000; nothing appears on the host);
- `sleep 70` -> status `timeout`; output of 200000 bytes -> `truncated: true`, output 65536 bytes;
- the same command to `container: "target"`.

## 4. Stop and delete latency (T-ISO-05 control check, T-MON-01, T-RES-02)
- `time` from the stop request (R14) to the `env.state_changed` activity event of that env: must be within
  5 s for Bhavya's T-ISO-05 control. Also `time docker stop <container>` for each container: well under the
  10 s stop timeout only if PID 1 handles SIGTERM (image CR, section 3).
- From the delete request (R15) to: env row `destroyed`, `env.destroyed` audited, and empty
  `docker ps -a --filter label=abh.env_id=<id>`, `docker network ls --filter label=abh.env_id=<id>`,
  `docker volume ls --filter label=abh.env_id=<id>`. Target 15 s (Manas, T-RES-02).
- Known delay sources from the code (reconcile.py, main.py): the loop polls every 1 s; one pass applies its
  claimed rows one after another, so a stop (up to 10 s per container) or a provision in the same pass, or the
  30 s reap, delays a delete behind it. Measure under the test's real load before changing anything.

## 5. T-RES-02 fork bomb (procedure decided by Manas 2026-11-26)
1. Neighbour env running; hostile S env running. 2. Exec `fork_bomb` in the hostile env. 3. For the full 30 s:
`GET /healthz` under 1 s, neighbour `echo ok` exec within 5 s, and every ~5 s `docker stats --no-stream` of the
hostile containers (PIDS, MEM USAGE). 4. Record `fork_bomb`'s JSON (`forks`, `errno`) if it ended, the
containers' `HostConfig.PidsLimit` and `Memory`, any `alert.oom_killed`, and whether the containers stayed up.
5. DELETE the env; measure step 4's removal. 6. Write down which limit contained the bomb from these numbers
only. R-03: under gVisor the host process counter sees sandbox threads, not tenant processes, so PIDS in
`docker stats` is not the bomb's process count.

## 6. B4 collectors (T-MON-02, alert part of T-RES-01; R-04)
- Memory cross-check: `mem_hog <mb> 30` inside a sandbox; read the runner's `mem_mb` sample and the container
  cgroup's own memory total during the hold; paste both numbers (B4 done-when). How the cgroup file is located
  on this host is to be recorded, not assumed.
- OOM: `mem_hog` above the container limit; `alert.oom_killed` on the stream within 5 s and exactly one
  `env.oom_killed` audit record, with timestamps. Record whether runsc killed one process or the whole sandbox
  (if the sandbox dies, the env becomes `failed` through collect.on_die and the exec result has no exit_code).
- T-MON-02: at least 6 metric events in 30 s for one running env.

## 7. B2 probes and isolation (T-ISO-03, 04, 06, 07; after the image CR)
- Each probe once in `toolbox` and in `target`, JSON pasted (team/parth/work/PROBE_CONTRACT.md).
- `probe_icmp`: report `sent`; an unsent probe is not isolation evidence (Manas).
- B2's own table: from alpha, every bravo address, the bridge gateway (or the recorded fact that the isolated
  network has none), the host LAN address on 443/5432/8000, a public address on 53/443: all fail.
- Detonator loopback-only check only if detonation ships; otherwise recorded as out of scope.
