"""Collector logic (services/runner/metrics.py) that needs no daemon or database. Stats documents below are
hand-written inputs in the Docker Engine API field layout, not captured output; the real-stats cross-check
(R-04) needs the Linux host."""

import json
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from services.runner import metrics
from services.runner.launch import EnvRow

ENV = EnvRow("0b6f0c1e-1111-4222-8333-444455556666", "7d2a4f00-aaaa-4bbb-8ccc-dddddddddddd", "app-target",
             500, 256, 128, 128)
CONTRACTS = (Path(__file__).resolve().parents[3] / "docs" / "04_CONTRACTS.md").read_text(encoding="utf-8")


def stats(cpu: int, pre_cpu: int, system: int, pre_system: int, mem: int, networks: object = None) -> dict[str, object]:
    doc: dict[str, object] = {
        "cpu_stats": {"cpu_usage": {"total_usage": cpu}, "system_cpu_usage": system, "online_cpus": 4},
        "precpu_stats": {"cpu_usage": {"total_usage": pre_cpu}, "system_cpu_usage": pre_system},
        "memory_stats": {"usage": mem, "stats": {"inactive_file": 50 * 1024 * 1024}},
        "pids_stats": {"current": 7},
    }
    if networks is not None:
        doc["networks"] = networks
    return doc


class Usage(unittest.TestCase):
    def test_cpu_memory_pids_network(self) -> None:
        u = metrics.usage(stats(3 * 10**8, 10**8, 4 * 10**9, 2 * 10**9, 100 * 1024 * 1024,
                                {"eth0": {"rx_bytes": 10, "tx_bytes": 3}, "eth1": {"rx_bytes": 5, "tx_bytes": 4}}))
        self.assertAlmostEqual(u.cores, 0.4)  # 2e8 / 2e9 * 4 CPUs, the docker CLI formula
        self.assertEqual(u.mem_mb, 100.0)  # cgroup total; inactive_file is not subtracted (R-04)
        self.assertEqual((u.pids, u.rx, u.tx), (7, 15, 7))

    def test_network_none_and_no_elapsed_time(self) -> None:
        u = metrics.usage(stats(10, 10, 5, 5, 0))
        self.assertEqual((u.cores, u.rx, u.tx), (0.0, 0, 0))

    def test_missing_fields_raise_instead_of_reading_zero(self) -> None:
        doc = stats(1, 0, 2, 1, 1)
        del doc["memory_stats"]["usage"]  # type: ignore[attr-defined]
        with self.assertRaises(KeyError):
            metrics.usage(doc)

    def test_env_sample_cpu_relative_to_env_limit(self) -> None:
        a, b = metrics.Usage(0.4, 100.0, 3, 10, 1), metrics.Usage(0.1, 20.5, 4, 5, 2)
        s = metrics.env_sample(ENV, [a, b], 12.345)
        self.assertEqual(s, {"cpu_pct": 100.0, "mem_mb": 120.5, "storage_mb": 12.35, "pids": 7,
                             "net_rx_bytes": 15, "net_tx_bytes": 3})
        self.assertEqual(tuple(s), metrics.SAMPLE_KEYS)


class Thresholds(unittest.TestCase):
    def test_mem_high_needs_three_samples_above_90_percent(self) -> None:
        high = (10.0, 231.0, 1.0)  # 231 / 256 = 90.2 %
        self.assertEqual(metrics.due_alerts(ENV, [high] * 3), ["alert.mem_high"])
        self.assertEqual(metrics.due_alerts(ENV, [high] * 2), [])
        self.assertEqual(metrics.due_alerts(ENV, [high, high, (10.0, 230.4, 1.0)]), [])  # exactly 90 %: not above

    def test_cpu_saturated_needs_five_samples_above_95_percent(self) -> None:
        busy = (95.5, 1.0, 1.0)
        self.assertEqual(metrics.due_alerts(ENV, [busy] * 5), ["alert.cpu_saturated"])
        self.assertEqual(metrics.due_alerts(ENV, [busy] * 4 + [(50.0, 1.0, 1.0)]), [])

    def test_storage_high_on_latest_sample(self) -> None:
        self.assertEqual(metrics.due_alerts(ENV, [(1.0, 1.0, 115.3)]), ["alert.storage_high"])
        self.assertEqual(metrics.due_alerts(ENV, [(1.0, 1.0, 115.2), (1.0, 1.0, 128.0)]), [])  # 90.0 % exactly

    def test_newest_first_order_matters(self) -> None:
        old_high = [(1.0, 1.0, 1.0)] + [(1.0, 250.0, 1.0)] * 3
        self.assertEqual(metrics.due_alerts(ENV, old_high), [])

    def test_every_kind_is_in_the_contract(self) -> None:
        for kind, _, _ in metrics.THRESHOLDS:
            self.assertIn(f"`{kind}` [warn]", CONTRACTS)
        self.assertIn("`alert.oom_killed` [critical]", CONTRACTS)
        self.assertIn("`env.oom_killed`", CONTRACTS)


class Parsing(unittest.TestCase):
    def test_df_posix_output(self) -> None:
        out = (b"Filesystem     1024-blocks    Used Available Capacity Mounted on\n"
               b"tmpfs  131072  2048  129024   2% /workspace\n")
        self.assertEqual(metrics.df_used_mb(out), 2.0)
        for bad in (b"", b"header only\n", out + b"extra line 1 2 3\n"):
            with self.assertRaises(ValueError):
                metrics.df_used_mb(bad)

    def test_payload_is_the_contract_shape_and_small(self) -> None:
        sample = metrics.env_sample(ENV, [metrics.Usage(0.25, 64.0, 5, 10**12, 10**12)], 100.0)
        ts = datetime(2026, 11, 26, 10, 0, 1, 234567, tzinfo=timezone(timedelta(hours=5, minutes=30)))
        text = metrics.payload(ENV.id, ts, sample)
        data = json.loads(text)
        self.assertEqual(set(data), {"env_id", "ts", "cpu_pct", "mem_mb", "storage_mb", "pids", "net_rx_bytes",
                                     "net_tx_bytes"})  # 04 section 6: {env_id, ...MetricSample}
        self.assertEqual(data["ts"], "2026-11-26T04:30:01.234Z")
        self.assertNotIn(" ", text)
        self.assertLess(len(text.encode()), 1000)  # PostgreSQL NOTIFY payload limit is 8000 bytes (R-16)

    def test_classify_events(self) -> None:
        attrs = {"abh.env_id": ENV.id, "abh.managed": "true", "name": f"abh-{ENV.id}-target", "exitCode": "137"}
        for action in ("oom", "die"):
            ev = {"Type": "container", "Action": action, "Actor": {"ID": "c1", "Attributes": attrs}}
            self.assertEqual(metrics.classify(ev), (ENV.id, action, attrs))
        for ev in ({"Type": "container", "Action": "exec_die", "Actor": {"Attributes": attrs}},
                   {"Type": "network", "Action": "die", "Actor": {"Attributes": attrs}},
                   {"Type": "container", "Action": "die", "Actor": {"Attributes": {"abh.env_id": "x"}}},
                   {"Type": "container", "Action": "oom"}):
            self.assertIsNone(metrics.classify(ev))
        self.assertEqual(metrics.EVENT_FILTERS, {"type": "container", "label": "abh.managed=true",
                                                 "event": ["oom", "die"]})


if __name__ == "__main__":
    unittest.main()
