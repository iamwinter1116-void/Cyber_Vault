"""Exec job rules with no I/O (docs/04_CONTRACTS.md section 5 `exec`, docs/08 section 6, risk R-14).

The user's command is only ever the single argument after ``sh -c`` inside the sandbox; it is never formatted
into a string for a host shell. Every container that runs jobs must provide ``timeout`` and ``sh``.
"""

from __future__ import annotations

from collections.abc import Mapping

from services.runner.launch import EnvRow, container_name
from services.runner.templates import TEMPLATE_CONTAINERS

DEADLINE_SEC = 60
OUTPUT_CAP = 65536
COMMAND_MAX = 4096  # R17: command is 1 to 4096 characters
KILLED = 137  # exit status of `timeout -s KILL` when the deadline fires


def exec_argv(command: str) -> list[str]:
    return ["timeout", "-s", "KILL", str(DEADLINE_SEC), "sh", "-c", command]


def target(env: EnvRow, observed: str, data: Mapping[str, object]) -> tuple[str, str]:
    """(container name, command) for a job input, or ValueError when the job cannot run."""
    command, name = data.get("command"), data.get("container", "toolbox")
    if not isinstance(command, str) or not 1 <= len(command) <= COMMAND_MAX:
        raise ValueError("command must be a string of 1 to 4096 characters")
    if observed != "running":
        raise ValueError(f"environment is {observed}, not running")
    if not isinstance(name, str) or name not in TEMPLATE_CONTAINERS.get(env.template, frozenset()):
        raise ValueError(f"template {env.template} has no container {name!r}")
    return container_name(env, name), command


def clean_output(data: bytes, truncated: bool) -> tuple[str, bool]:
    """At most OUTPUT_CAP bytes of valid UTF-8 with no U+0000, which PostgreSQL jsonb cannot store."""
    raw = data.decode("utf-8", "replace").replace("\x00", "�").encode("utf-8")
    if len(raw) > OUTPUT_CAP:
        raw, truncated = raw[:OUTPUT_CAP], True
    return raw.decode("utf-8", "ignore"), truncated


def status(exit_code: int | None, duration_ms: int, deadline_hit: bool) -> str:
    """timeout when the in-sandbox deadline killed the command or the host-side bound ended the read."""
    if deadline_hit or (exit_code == KILLED and duration_ms >= DEADLINE_SEC * 1000):
        return "timeout"
    return "error" if exit_code is None else "done"
