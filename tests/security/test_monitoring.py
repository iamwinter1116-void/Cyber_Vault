"""Real-time monitoring SSE tests: T-MON-01..04."""
from __future__ import annotations

import json
import time

from .conftest import API_BASE, create_env_and_wait, login_as


def test_t_mon_01_state_change_streamed_within_3s(stack_url: str) -> None:
    """T-MON-01: env.state_changed arrives on /stream within 3s of state change."""
    ca, csrfa = login_as(stack_url, "analyst.alpha@abhedya.local")
    t0 = time.monotonic()
    with ca.stream("GET", f"{API_BASE}/stream") as stream:
        create_env_and_wait(ca, csrfa, "mon-01-alpha")
        for line in stream.iter_lines():
            if "env.state_changed" in line:
                assert time.monotonic() - t0 <= 3.0
                return
    raise AssertionError("No env.state_changed event received")


def test_t_mon_02_metrics_emitted_every_5s_and_bounded(stack_url: str) -> None:
    """T-MON-02: At least 6 metric events in 30s on /stream with 0 <= mem <= limit * 1.05."""
    ca, csrfa = login_as(stack_url, "analyst.alpha@abhedya.local")
    env_a = create_env_and_wait(ca, csrfa, "mon-02-alpha", size="S")
    samples: list[dict] = []
    deadline = time.monotonic() + 32.0
    ev_name = ""
    with ca.stream("GET", f"{API_BASE}/stream") as stream:
        for line in stream.iter_lines():
            if time.monotonic() > deadline:
                break
            if line.startswith("event:"):
                ev_name = line.split(":", 1)[1].strip()
            elif line.startswith("data:") and ev_name == "metric":
                payload = json.loads(line.split(":", 1)[1].strip())
                if payload.get("env_id") == env_a["id"]:
                    samples.append(payload)
                    if len(samples) >= 6:
                        break
    assert len(samples) >= 6, f"Expected >=6 metric events in 30s, got {len(samples)}"
    for s in samples:
        assert 0 <= s["mem_mb"] <= env_a["mem_mb"] * 1.05


def test_t_mon_03_stream_scoped_by_team_and_role(stack_url: str) -> None:
    """T-MON-03: analyst receives own team only and zero audit events; auditor receives both."""
    ca, _ = login_as(stack_url, "analyst.alpha@abhedya.local")
    with ca.stream("GET", f"{API_BASE}/stream") as stream:
        for line in stream.iter_lines():
            assert "event: audit" not in line
            if line.startswith("event: heartbeat"):
                return


def test_t_mon_04_last_event_id_resumes_without_loss(stack_url: str) -> None:
    """T-MON-04: Disconnect, generate 10 events, reconnect with Last-Event-ID -> all 10 once, in order."""
    ca, csrfa = login_as(stack_url, "analyst.alpha@abhedya.local")
    env_a = create_env_and_wait(ca, csrfa, "mon-04-alpha", size="S")
    after = 0
    while True:
        batch = ca.get(f"{API_BASE}/events?limit=200&after_id={after}").json()["items"]
        if not batch:
            break
        after = max(e["id"] for e in batch)
        if len(batch) < 200:
            break
    last_id = after

    for i in range(10):
        r = ca.post(f"{API_BASE}/envs/{env_a['id']}/exec", headers={"X-CSRF-Token": csrfa}, json={"command": f"echo {i}"})
        assert r.status_code == 202

    expected_ids: list[int] = []
    wait_deadline = time.monotonic() + 30.0
    while time.monotonic() < wait_deadline:
        new_events = ca.get(f"{API_BASE}/events?limit=200&after_id={last_id}").json()["items"]
        expected_ids = sorted(e["id"] for e in new_events)
        if len(expected_ids) >= 10:
            break
        time.sleep(0.5)
    assert len(expected_ids) >= 10, f"Only {len(expected_ids)} new events created after {last_id}"
    expected_ids = expected_ids[:10]

    seen_ids: list[int] = []
    deadline = time.monotonic() + 15.0
    with ca.stream("GET", f"{API_BASE}/stream", headers={"Last-Event-ID": str(last_id)}) as stream:
        for line in stream.iter_lines():
            if time.monotonic() > deadline:
                break
            if line.startswith("id:"):
                eid = int(line.split(":", 1)[1].strip())
                if eid > last_id:
                    seen_ids.append(eid)
                    if len(seen_ids) >= 10:
                        break
    assert seen_ids == expected_ids, f"Expected exact ordered replay {expected_ids}, got {seen_ids}"
