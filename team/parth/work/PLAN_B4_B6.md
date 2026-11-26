# Phased plan · B4–B6 local slices (Parth, role B) · 2026-11-26

Base: `work/parth` e67a81b, synced with integration 26a71e0. Work order: docs/16 plus Manas's message of
2026-11-26 ("start B4–B6 in phases ... keep Docker calls and host acceptance explicitly unverified").
Every phase: stdlib unittest for pure logic, real-PostgreSQL tests (run by Manas on a disposable Compose DB),
and no Docker run is claimed. Budget: `services/runner` 800 lines (docs/05); the counting rule comes from Manas.

## Phase R · failed-env recovery rule (standing gap 2)
- Rule: a `failed` row is terminal (no start route), so its objects serve nothing. The reaper treats `failed` like
  `destroyed`: every 30 s it retries `destroy()` for failed envs that still have labelled objects or a V1 image,
  until none remain. The row stays `failed`; the later user delete still writes `env.destroyed`.
- Files: `services/runner/reconcile.py` (`LIVE_SQL`), `tests/unit/runner/test_reconcile_pg.py`.
- Test: liveness query returns running/stopped rows and excludes failed, destroyed, missing ids.
- Acceptance pending: real Docker removal on Linux (T-RES-06 neighbourhood).

## Phase B4 · collectors and alerts · `services/runner/collect.py` · T-MON-02, alert part of T-RES-01
Contract: 04 section 6 (kinds, thresholds), section 7.6 (`env.oom_killed`), schema `metric_sample`,
`activity_event`; docs/08 section 5; risks R-03, R-04, R-16.
- Pure: parse one docker stats document (CPU from `cpu_stats`/`precpu_stats` deltas, memory = cgroup total
  `memory_stats.usage` per R-04, pids, summed network bytes); sum per env; CPU percent of the env's own limit;
  threshold rule (mem > 90 % for 3 samples, cpu > 95 % for 5, storage > 90 % latest); `df -P -k` parse for
  V2/V3 storage; event classification (`oom`, `die`, canonical `abh.env_id`); compact NOTIFY payload.
- DB: insert sample + `pg_notify('abh_metric', json)` in one transaction; alert throttle from `activity_event`
  (one per env per kind per 5 min, restart-safe); `oom` -> `env.oom_killed` audit + `alert.oom_killed`;
  unexpected `die` of a running, unexpired env -> `failed` through `reconcile.record`; delete samples > 1 h.
- Docker (unverified): events stream with `since` reconnect; `stats(stream=False)` per running container;
  `exec_run(["df","-P","-k","/workspace"])` for V2/V3 storage.
- Tests: `tests/unit/runner/test_collect.py` (pure), `test_collect_pg.py` (real PostgreSQL, LISTEN receives the
  payload; throttle; delete; die/expiry race).
- Acceptance pending (Linux): memory cross-check vs cgroup total with numbers; OOM alert within 5 s; T-MON-02.

## Phase B5 · exec jobs · `services/runner/jobs.py` · supports T-E2E-01, T-RBAC-12; risk R-14
- Claim SQL from docs/08 section 6; container from input validated against the template's names.
- argv `["timeout", "-s", "KILL", "60", "sh", "-c", <command>]` passed as a list to `exec_run(user="1000:1000")`:
  the command is one argv element, never formatted into a host string. Output capped at 65536 bytes with
  `truncated`; status `done`/`timeout`/`error`; one `job.finished` audit record and activity event.
- Image requirement for B4/B5 images: `timeout` and `sh` in every exec-able container (to agree with Bhavya's
  probe contract).
- Tests: pure argv/result/cap/timeout classification; PG claim/finish. Hostile-command test inside a sandbox,
  70 s sleep, 200000-byte output: Linux pending.

## Phase B6 · file analysis · local part only
- Pure now: deterministic verdict rule (04 section 5), result shape, detonation tail (last 4 KiB), quarantine path
  check (`<sha256>` only, inside `ABH_QUARANTINE_DIR`), read-only single-file sample mount per section 8.
- Waits for Linux/images: YARA-X command syntax from its own `--help`, the official antivirus test string,
  analyzer/detonator images and digests, T-WL-02.

## Probe contract with Bhavya (before any sandbox image)
Proposal sent in HANDOFFS.md; images are built only after she agrees. No image is started on Windows.

## Budget
Before: 756 physical / 542 code lines. Estimates: R ~0, B4 ~140, B5 ~60, B6 local ~40 code lines -> ~782 code.
Physical lines will pass 800 during B4; recorded in JOURNAL.md when the counting rule is fixed.
