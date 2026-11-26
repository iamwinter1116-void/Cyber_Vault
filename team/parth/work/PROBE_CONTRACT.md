# B2 probe and workload-command contract (role B, Parth) · version 3 · 2026-11-26

Status: interface agreed with Bhavya for the five probes (team/parth/work/HANDOFFS.md, 2075dbf) plus the additive
correction (`mounts`, `cap_eff`, `disk_fill`). This version adds the four workload commands and the failure
rules her tests already depend on. The implementation language and the images are NOT approved yet
(team/parth/work/CR_PROPOSAL_sandbox_images.md); no probe exists in the repository. Nothing here is evidence.

## Rules for every command
- Installed on PATH in every container that has a network, i.e. `toolbox` and `target` (Manas 2026-11-26:
  T-ISO-04 applies to every sandbox shipped; exec reaches `target` through R17 `container: "target"`), and
  `probe_connect` in `detonator` (T-WL-02 runs it from a detonation script).
- Run through the exec job path (`timeout -s KILL 60 sh -c <command>`, uid 1000).
- Output: the LAST stdout line is one JSON object in Python `json.dumps` default style (", " and ": ").
- Exit status: 0 = the probe ran and its JSON is the answer (an unreachable target is still exit 0);
  1 = the command was stopped by the condition it measures (named in its JSON, below); 2 = bad arguments.
  137 with no JSON = killed (deadline or OOM); a test must not read 137 as success of a limit unless it also
  checks the limit's own evidence (alert, audit, error name).
- `error` is `null` or a short text that starts with the failing step (`resolve:`, `connect:`, `send:`, ...).

## Probes (exit 0 when they ran)
| Command | JSON |
| --- | --- |
| `probe_connect <host> <port> <timeout_s>` | `{"reachable": bool, "host": str, "port": int, "error": str or null}`; a name that does not resolve is `reachable: false` with `error: "resolve: ..."` |
| `probe_icmp <ip> <timeout_s>` | `{"reachable": bool, "sent": bool, "error": str or null}`; tries an unprivileged ICMP datagram socket only (no capability is added); `sent: false` is never isolation evidence |
| `probe_dns <name> <timeout_s>` | `{"resolved": bool, "addresses": [str], "error": str or null}` |
| `probe_env` | `{"env_vars": [names only, no values], "mounts": [mount point str], "cap_eff": str (CapEff hex from /proc/self/status), "uid": int, "gid": int, "kernel_release": str}` |
| `probe_write <path>` | `{"ok": bool, "path": str, "error": str or null}`; on a read-only root the error names the errno (e.g. `EROFS`) |

## Workload commands (exit 1 = contained by the limit; JSON says which)
| Command | Behaviour | JSON on its last line |
| --- | --- | --- |
| `mem_hog <mb> [hold_s]` | allocates and writes every page, 1 MiB at a time, up to `<mb>`, then keeps it for `hold_s` seconds (default 0) so the B4 memory cross-check can read a known allocation | exit 0 `{"allocated_mb": n, "error": null}` (limit did NOT hold); exit 1 `{"allocated_mb": n, "error": "MemoryError"}`; OOM kill = 137, no JSON |
| `disk_fill <path>` | writes 1 MiB chunks to `<path>/disk_fill.bin` with fsync until a write fails; the file is left for the neighbour/host checks | exit 1 `{"bytes_written": n, "errno": "ENOSPC", "error": str}`; any other errno is reported the same way with its name; deadline kill = 137, no JSON (a missing quota then looks like 137) |
| `cpu_burn <seconds>` | one busy worker per CPU the sandbox reports, for `<seconds>` | exit 0 `{"seconds": n, "workers": n}` |
| `fork_bomb` | forks until fork fails, then waits | exit 1 `{"forks": n, "errno": str, "error": str}` when contained (errno name, e.g. `EAGAIN`, is part of the evidence of which limit held); deadline kill = 137 |

## Procedures decided by Manas (2026-11-26)
- T-RES-02: run the fork bomb and the neighbour checks for the full 30 s; then explicitly DELETE the environment
  and verify the runner removes its containers, network and volume within 15 s. Record which limit contained
  the bomb. The runner has no rule that deletes an environment after a fork bomb; nothing may assume one.
- T-ISO-04: required for every sandbox shipped: gateway, host LAN and public IP, from `toolbox` and `target`.
  The detonator loopback-only subcheck applies only if detonation ships; if docs/02 cut 5 removes detonation,
  that subcheck is recorded as out of scope and detonation is not claimed as tested.

## What tests need from this (for Bhavya; her files, her decision)
- T-RES-03: `exit_code != 0` alone also passes when the quota is missing (the 60 s deadline gives 137). The
  contract lets the test require `errno == "ENOSPC"` and `bytes_written <= storage_mb * 1048576`.
- T-RES-01: an OOM kill is 137 with no JSON; docs/06 also requires `alert.oom_killed` within 5 s,
  `env.oom_killed` audited and the neighbour's 1 s loop missing at most one beat.
- T-WL-01: docs/06 says the name "does not resolve" from another environment; `probe_dns target 3` tests that
  directly; `probe_connect target ...` passes on resolve failure by the rule above.
- T-ISO-06: "writes fail with a read-only error": `probe_write`'s `error` carries the errno.

## Measured on the Linux host before any claim (UNVERIFIED now)
Whether unprivileged ICMP can send under runsc with cap_drop ALL (if not, T-ISO-03 fails until a CR decides);
whether `/sys/class/net` exists in a runsc sandbox (T-ISO-04 detonator check lists it); OOM behaviour of runsc
for a process inside the sandbox (process kill vs whole sandbox).
