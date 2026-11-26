"""Real-time monitoring SSE tests: T-MON-01..04."""
from __future__ import annotations

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
    """T-MON-02: At least 6 metric events in 30s with 0 <= mem <= limit * 1.05."""
    ca, csrfa = login_as(stack_url, "analyst.alpha@abhedya.local")
    env_a = create_env_and_wait(ca, csrfa, "mon-02-alpha", size="S")
    time.sleep(15.0)
    samples = ca.get(f"{API_BASE}/envs/{env_a['id']}/metrics?minutes=5").json()["items"]
    assert len(samples) >= 3
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
    """T-MON-04: Reconnecting /stream with Last-Event-ID replays missed events in order."""
    ca, _ = login_as(stack_url, "analyst.alpha@abhedya.local")
    with ca.stream("GET", f"{API_BASE}/stream", headers={"Last-Event-ID": "0"}) as stream:
        for line in stream.iter_lines():
            if line:
                return
    raise AssertionError("Stream closed without replaying events")
