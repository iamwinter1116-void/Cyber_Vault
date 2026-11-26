# 08 · Technical implementation notes

These notes say how to build each part with the least code. Code fragments here were **not executed**; they
show intent and names. Confirm every library call against the installed version (rule H2) before relying on it.
Items marked **SPIKE** are unknowns that must be settled by a ten-minute experiment on the demo host, with the
result written to `evidence/preflight.md`.

## 1. Host preflight and setup (B) · `host/preflight.sh`, `host/setup_host.sh`

`make preflight` fails fast, in this order, and prints one PASS or FAIL line per check:
1. Linux, x86_64, and not WSL (`/proc/version` must not mention Microsoft).
2. `docker info`: server is Docker Engine (not Docker Desktop); record Server Version, Cgroup Version,
   Cgroup Driver, Storage Driver, Backing Filesystem, Runtimes.
3. `runsc --version`; `runsc` listed under Runtimes. Install from the gVisor apt repository, run
   `sudo runsc install`, restart Docker [S3].
4. `docker run --rm --runtime=runsc hello-world` exits 0.
5. `docker run --rm --runtime=runsc <base image> uname -r` differs from host `uname -r`.
6. **SPIKE network:** create a network with `--internal` and option
   `com.docker.network.bridge.gateway_mode_ipv4=isolated`; start two `runsc` containers on it; they reach
   each other; neither reaches the host's addresses or the internet. If the option is rejected, fall back to
   `--internal` plus a host firewall rule that drops traffic from sandbox subnets to the host, and record it.
7. **SPIKE limits under runsc:** a 64 MB container that allocates 200 MB is OOM-killed; a container with
   `--pids-limit 64` survives a fork bomb without hurting the host; `--cpus 0.5` holds a busy loop near 50 %.
   Record what `docker stats` and the cgroup files report in each case.
8. **SPIKE storage:** run the ladder of section 4 and record the first method that passes.
9. Clock synchronised (`timedatectl`), at least 4 CPUs and 8 GB RAM, 20 GB free disk. Record the CPU count and
   memory: they are the host capacity used by admission control.
10. Every image in `sandbox/templates/*/template.yaml` present locally by digest.

On the Omen this script runs inside the Ubuntu VM built by `team/parth/01_DEVICE_SETUP.md`, and on the Legion
inside the imported copy. It is never run in WSL (check 1 fails there by design).

`setup_host.sh` is idempotent and only does: install Docker Engine and runsc from their official repositories,
register the runtime, create `/var/lib/abhedya/{vol,quarantine,witness}`, enable the NTP client.

## 2. Compose file (C, with blocks from A and B)
Follow `04_CONTRACTS.md` section 9 exactly. Checks that C enforces in review: only `proxy` publishes a port;
only `runner` mounts the Docker socket; `control` is `internal: true`; every service has a read-only root
filesystem where the image allows it, drops capabilities, and has memory and CPU limits so the control plane
cannot starve itself; secrets are mounted files; database init applies `contracts/schema.sql` then sets the
three role passwords from secrets.

## 3. Runner (B) · `services/runner/`

Suggested modules: `main.py` (loops), `launch.py` (the one hardened launch function), `net.py`, `storage.py`,
`collect.py` (events and stats), `jobs.py`, `templates.py`.

**Reconcile loop** (every second, plus wake on NOTIFY): select environments where observed and desired state
differ or `expires_at` has passed, with `FOR UPDATE SKIP LOCKED`.
- `requested` → set `provisioning`; create network, volume, containers; set `running` and `isolation_tier`;
  append `env.provisioned`. On any error: remove what was created, set `failed` with `failure_reason`, append `env.failed`.
- desired `stopped` → stop containers; set `stopped`; append `env.stopped`.
- desired `destroyed` or expired → remove containers, network, volume; set `destroyed`; append `env.destroyed` or `env.expired`.
- Every state write also inserts an `env.state_changed` activity event in the same transaction.
- Idempotent by construction: every Docker object is named from the environment ID and looked up before
  creation, so a crash and restart converges (T-RES-06).
- **Reaper** (every 30 s): any container, network or volume labelled `abh.managed=true` whose environment row
  is `destroyed` or missing is removed.

**One launch function.** Every sandbox container in every template goes through a single function that
applies the whole profile of `04` section 8. No other code calls the Docker SDK's run or create.
```python
def launch(env: EnvRow, spec: ContainerSpec) -> Container:
    return docker.containers.run(
        spec.image_digest, spec.command, name=f"abh-{env.id}-{spec.name}", detach=True,
        runtime=settings.sandbox_runtime, user="1000:1000",
        cap_drop=["ALL"], security_opt=["no-new-privileges"], read_only=True, privileged=False,
        tmpfs={"/tmp": "rw,noexec,nosuid,size=64m"},
        mounts=[workspace_mount(env), *spec.readonly_mounts],
        nano_cpus=env.cpu_millis * 1_000_000,
        mem_limit=f"{env.mem_mb}m", memswap_limit=f"{env.mem_mb}m", pids_limit=env.pids_limit,
        network=spec.network or net_name(env), environment=spec.env,
        labels={"abh.managed": "true", "abh.env_id": str(env.id), "abh.team_id": str(env.team_id),
                "abh.template": env.template},
    )
```
CPU and memory of a multi-container template are split between its containers so the sum equals the
environment's limits (for `app-target`: target 60 %, toolbox 40 %).
Each `template.yaml` `description` starts with the isolation profile of decision D12, for example
`[T0.H2.N2] ...`. In degraded mode the `alert.isolation_degraded` message names `T0.H1.N2`.

## 4. Storage quota ladder (B) · **SPIKE**, decided at G0
Try in order under `runsc`; keep the first that passes T-RES-03; write the choice to `evidence/preflight.md`.

| Method | How | Property |
| --- | --- | --- |
| V1 loop image | Create a sparse file of `storage_mb` under `ABH_VOLUME_DIR`, format it ext4 with the root directory owned by 1000:1000, create a local-driver volume with `type=ext4`, `device=<host path of the file>`, `o=loop` | Disk-backed, hard cap equals image size, independent of the memory limit |
| V2 tmpfs volume | Local-driver volume with `type=tmpfs`, `device=tmpfs`, `o=size=<n>m,uid=1000,gid=1000` (the documented form [S14]) | RAM-backed; check how it is charged against the memory limit and record it |
| V3 tmpfs mount | Container tmpfs mount on `/workspace` with `size=` | RAM-backed inside the sandbox |

`--storage-opt size=` is not on the ladder: under `overlay2` it needs an xfs backing filesystem mounted with
`pquota` [S12], which we do not assume the demo host has. Leaving it out is our decision.
Because the root filesystem is read-only, the only writable places are `/tmp` (64 MB) and `/workspace`.
gVisor can also cap its own root overlay with a size option [S39]; that is not needed while the root is read-only.
`storage_mb` in metric samples: for V1 the allocated size of the image file; for V2 and V3 the used size
reported by the filesystem inside the container.

## 5. Collectors and alerts (B) · `collect.py`
- **Events:** one long-lived subscription to Docker events filtered by label `abh.managed=true` and type
  container [S19]. Map `oom` and `die` with an out-of-memory flag to `alert.oom_killed` plus audit
  `env.oom_killed`; unexpected `die` to `env.failed`.
- **Stats:** every `ABH_METRIC_INTERVAL_SEC`, one-shot stats per running container, summed per environment,
  inserted into `metric_sample` and sent with `pg_notify('abh_metric', <json>)`. CPU percent is relative to
  the environment's own limit. Under gVisor read total memory from the cgroup total, not the anonymous
  figure [S13]. Process count from the engine reflects host-side tasks of the sandbox; say so in the console tooltip.
- **Threshold alerts** are computed in the runner from the last samples (`04` section 6). One alert per
  environment per kind per five minutes.
- Delete metric rows older than one hour.

## 6. Jobs (B) · `jobs.py`
Claim with `UPDATE job SET status='running' ... WHERE id = (SELECT id FROM job WHERE status='queued' ORDER BY
created_at FOR UPDATE SKIP LOCKED LIMIT 1) RETURNING *`. Every job ends with one `job.finished` audit record
and activity event.
- **exec:** `exec_run` in the named container as UID 1000 with a 60 s deadline, `sh -c <command>`; capture at
  most 65536 bytes. The command is user data: never interpolate it into a host shell.
- **file_analysis:** the API created an S `file-analysis` environment and stored the sample. `analyzer`
  (network `none`, sample mounted read-only): SHA-256, type identification, `yr scan` over the baked rule
  directory [S27]. If `detonate`: `detonator` (network `none`, sample copied to `/workspace`, 120 s deadline; an NDSS 2021 study of sandbox run times
  recommends two minutes when the goal is a behavioural report [S54])
  runs scripts with their interpreter and ELF files directly; record exit code, duration, last 4 KiB of
  output, timeout flag. Apply the verdict rule of `04` section 5. Destroy the environment.
  Rules: ship a small in-repo rule set including one for the standard antivirus test file (tagged
  `malicious`) and a few behaviour-string rules (tagged `suspicious`). Take the test string from its
  official source and verify it; do not type it from memory.
- **ai_scan:** an M `ai-redteam` environment. `llm-target` is an in-repo HTTP stub (about 60 lines): it holds a
  system instruction and a planted secret; in vulnerable mode it obeys instructions found in the user message,
  in guarded mode it refuses messages matching a small deny list. `scanner` runs garak through its REST
  generator [S28] against `http://llm-target:<port>` with a probe list fixed in the template for `quick` and
  `full`. **SPIKE:** choose probes that run with no internet access and bake everything they need into the
  image; read option names from `garak --help` of the installed version. Parse `report.jsonl` into the result
  shape; `owasp_llm` comes from a small in-repo map from probe family to OWASP LLM 2025 ID [S29].
  Wording everywhere is "scanner-flagged": a 2026 preprint found garak's verdicts depend on the evaluator in
  22 of 25 attack categories [S53].

## 7. API (A) · `services/api/`
Suggested modules: `main.py`, `deps.py`, `authz.py`, `schemas.py`, `routes/{auth,users,teams,envs,jobs,monitor,audit,admin}.py`.

- **Authorization in one place.** `authorize("R12")` is a dependency that: resolves the session cookie to a
  user (401); checks the CSRF header on unsafe methods (403); checks the role against the matrix (403, audited);
  for object routes loads the object and applies the scope (404 or 403, audited); returns a context with
  `user`, `actor`, `ip`, `request_id` and a transaction helper. Route bodies contain no role or team checks.
- **Startup check:** registered routes must equal matrix rules, else exit (T-RBAC-05).
- **State change pattern** (the only shape a mutating route may have):
```python
@router.post("/envs", status_code=201, response_model=Env)
def create_env(body: EnvCreate, ctx: Ctx = Depends(authorize("R12"))) -> Env:
    with ctx.transaction() as conn:
        team = lock_team(conn, ctx.user.team_id)
        ensure_quota(conn, team, SIZES[body.size])        # raises QuotaExceeded -> 409, denied record
        env = insert_env(conn, ctx.user, body)
        audit.append(conn, actor=ctx.actor, action="env.create", target_type="env", target_id=str(env.id),
                     outcome="success", ip=ctx.ip, request_id=ctx.request_id,
                     detail={"template": body.template, "size": body.size})
    return env
```
- **Schemas** are pydantic models with unknown fields forbidden on input and explicit field lists on output.
- **SQL** is parameterised, written next to its route, no string formatting of values, no ORM.
- **Stream:** one listener task per process holds a connection with `LISTEN abh_activity, abh_audit,
  abh_metric`, loads the row for each notification and fans out to per-subscriber bounded queues after the
  scope filter. A full queue drops the subscriber, who reconnects with `Last-Event-ID`.
- **R28 verify** runs steps 1 to 4 of `04` section 7.8 over the database with `abh_core`. It cannot see the
  witness file by design; the independent verifier with `--witness` is the stronger check. The public key
  for R27 is read from `ABH_NOTARY_PUBKEY_PATH` (a public file mounted read-only).
- **Uploads:** stream to a temporary file while hashing, enforce 10 MiB while streaming, rename to
  `<sha256>`, chmod 0400.

## 8. Ledger and notary (A) · `core/abh_core/audit.py`, `services/notary/`
- `append` is about 30 lines: lock, read tail, read database clock, build the 15-key body, validate value
  types recursively (reject float, None, NUL, bad keys, canonical `detail` over 2048 bytes, unknown action),
  hash, insert, return `seq`.
- **Notary loop:** on start, if the ledger is empty append `audit.genesis`. Every 5 s: verify records after
  the last verified `seq` (steps 1 to 3). When the checkpoint condition holds: recompute the root for every
  checkpoint in the witness file and compare the database checkpoint table with the witness file. Any
  mismatch → critical `alert.tamper_detected`, append `audit.tamper_detected` with the verdict in `detail`,
  and stop signing until restarted with an explicit operator flag. Otherwise sign, insert, append to the
  witness file and fsync.
- Key handling: `make secrets` creates the 32-byte seed and writes the public key hex beside it. The seed is
  mounted only into `notary`.

## 9. Independent verifier (C) · `tools/verify_audit.py`
One file, standard library plus `cryptography` for Ed25519. No import from `core/` or `services/`. Written
from `04_CONTRACTS.md` section 7 and the vectors only; C's agent is told not to open `core/abh_core/audit.py`.
Reads NDJSON, implements section 7.8 in order, prints one JSON line, sets the exit code.

## 10. Console (C) · `web/`
- Typed client generated from `contracts/openapi.yaml`; one fetch wrapper that adds `X-CSRF-Token` (kept in
  memory, refreshed from R03 on load) and maps the error envelope.
- One `useStream` hook around `EventSource` that feeds the query cache; pages never poll while it is connected.
- Pages: Login · Overview (counts, host allocation bars, isolation badge, ledger status with last checkpoint)
  · Environments (table with state, tier badge, live CPU, memory, storage against limits; create; stop;
  destroy) · Environment detail (charts, command box with output, events) · Files (upload, reports) ·
  AI red team (start, results by probe with OWASP ID) · Activity (live feed, severity filter) · Audit
  (filter, export, Verify, checkpoints, red banner on `alert.tamper_detected`) · Users and Teams (admin).
- Navigation and buttons follow the role from R03, but the server remains the only enforcement point.
- Never render untrusted text as HTML: command output, filenames and audit details go into text nodes.

## 11. Things that are easy to get wrong
See the pre-filled risks in `09_BUG_JOURNAL.md` (R-01 to R-27). Read them before your first prompt.

## 12. Demo flags (C writes the reset step; nothing else changes)
`make demo-reset` plants the two flags defined in the fixtures of `06_VERIFICATION.md`. `flag_env` is written
through the public API as `analyst.alpha` (create an S `app-target` environment, wait for `running`, one exec
that writes the file). `flag_host` is written by the reset script on the host with `sudo`, never by a
container. The idea comes from Google kCTF, whose reward programme hides flags that can only be read by
breaking out [S46].
