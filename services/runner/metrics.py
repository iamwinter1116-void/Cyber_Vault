"""Pure collector logic (docs/08 section 5; docs/04_CONTRACTS.md section 6; risks R-04, R-16): stats parsing,
per-environment sums, threshold rule, df parsing, NOTIFY payload and event classification. No I/O here."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from services.runner.launch import MANAGED, EnvRow, canonical_id

MIB = 1024 * 1024
EVENT_FILTERS = {"type": "container", "label": MANAGED, "event": ["oom", "die"]}
# Order matches the (cpu_pct, mem %, storage %) tuple built in due_alerts. Kind, samples, percent (04 section 6).
THRESHOLDS = (("alert.cpu_saturated", 5, 95.0), ("alert.mem_high", 3, 90.0), ("alert.storage_high", 1, 90.0))
SAMPLE_KEYS = ("cpu_pct", "mem_mb", "storage_mb", "pids", "net_rx_bytes", "net_tx_bytes")


@dataclass(frozen=True)
class Usage:
    cores: float
    mem_mb: float
    pids: int
    rx: int
    tx: int


def usage(stats: Mapping[str, Any]) -> Usage:
    """One ``stats(stream=False)`` document (the engine waits two cycles, so ``precpu_stats`` is filled).

    CPU is cores in use, computed as the docker CLI does. Memory is the cgroup total ``usage`` without
    subtracting cache: under gVisor application memory is accounted as shared memory (R-04)."""
    cpu, pre = stats["cpu_stats"], stats["precpu_stats"]
    sys_delta = cpu["system_cpu_usage"] - pre.get("system_cpu_usage", 0)
    online = cpu.get("online_cpus") or len(cpu["cpu_usage"].get("percpu_usage") or [1])
    cpu_delta = cpu["cpu_usage"]["total_usage"] - pre.get("cpu_usage", {}).get("total_usage", 0)
    nets = (stats.get("networks") or {}).values()  # absent for network none containers
    return Usage(cpu_delta / sys_delta * online if sys_delta > 0 else 0.0, stats["memory_stats"]["usage"] / MIB,
                 int(stats["pids_stats"]["current"]), sum(n["rx_bytes"] for n in nets),
                 sum(n["tx_bytes"] for n in nets))


def env_sample(env: EnvRow, parts: Sequence[Usage], storage_mb: float) -> dict[str, float | int]:
    """One metric_sample row; cpu_pct is relative to the environment's own CPU limit (schema comment)."""
    return {"cpu_pct": round(sum(p.cores for p in parts) * 100_000 / env.cpu_millis, 2),
            "mem_mb": round(sum(p.mem_mb for p in parts), 2), "storage_mb": round(storage_mb, 2),
            "pids": sum(p.pids for p in parts), "net_rx_bytes": sum(p.rx for p in parts),
            "net_tx_bytes": sum(p.tx for p in parts)}


def due_alerts(env: EnvRow, recent: Sequence[Sequence[float]]) -> list[str]:
    """Threshold kinds whose condition holds; ``recent`` is (cpu_pct, mem_mb, storage_mb), newest first."""
    pct = [(s[0], s[1] * 100 / env.mem_mb, s[2] * 100 / env.storage_mb) for s in recent]
    return [kind for i, (kind, n, limit) in enumerate(THRESHOLDS)
            if len(pct) >= n and all(p[i] > limit for p in pct[:n])]


def df_used_mb(output: bytes) -> float:
    """``df -P -k /workspace``: POSIX format, a header and one line whose third field is used 1024-byte blocks."""
    lines = output.decode("utf-8", "replace").strip().splitlines()
    if len(lines) != 2:
        raise ValueError(f"unexpected df output: {lines!r}")
    return int(lines[1].split()[2]) / 1024


def payload(env_id: str, ts: datetime, sample: Mapping[str, float | int]) -> str:
    """NOTIFY abh_metric data, exactly ``{env_id, ...MetricSample}`` (04 section 6); compact for R-16."""
    stamp = ts.astimezone(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
    return json.dumps({"env_id": env_id, "ts": stamp, **sample}, separators=(",", ":"))


def classify(ev: Mapping[str, Any]) -> tuple[str, str, Mapping[str, str]] | None:
    """(env_id, action, attributes) for an oom or die event of a managed container with a canonical env id."""
    attrs = (ev.get("Actor") or {}).get("Attributes") or {}
    env_id = canonical_id(attrs.get("abh.env_id"))
    if ev.get("Type") != "container" or ev.get("Action") not in ("oom", "die") or env_id is None:
        return None
    return env_id, str(ev["Action"]), attrs
