"""The one hardened launch path: docs/04_CONTRACTS.md section 8, docs/08 section 3.

Argument names were checked against docker-py 7.2.0 source (docker/models/containers.py,
docker/types/containers.py). ``containers.run()`` pulls the image when it is missing, which section 8
forbids ("pull policy never"), so ``launch`` calls ``containers.create()`` and then ``start()``.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

DIGEST_RE = re.compile(r"^(?:[a-z0-9][a-z0-9._/:-]*@)?sha256:[0-9a-f]{64}$")
CONTAINER_NAME_RE = re.compile(r"^[a-z][a-z0-9-]{0,30}$")
SANDBOX_USER = "1000:1000"
TMP_TMPFS = {"/tmp": "rw,noexec,nosuid,size=64m"}
WORKSPACE = "/workspace"
TMPFS_OPTS_RE = re.compile(r"^size=[1-9][0-9]*m,uid=1000,gid=1000$")


class ProfileError(ValueError):
    """A request that would violate the sandbox profile; the runner refuses it."""


class IsolationUnavailable(RuntimeError):
    """runsc is not usable and degraded mode is not allowed: refuse to provision."""


@dataclass(frozen=True)
class EnvRow:
    """The env columns the launch path reads (contracts/schema.sql, table env)."""

    id: str
    team_id: str
    template: str
    cpu_millis: int
    mem_mb: int
    storage_mb: int
    pids_limit: int


@dataclass(frozen=True)
class ContainerSpec:
    """One container of a template, with its share of the environment's CPU and memory."""

    name: str
    image: str
    cpu_millis: int
    mem_mb: int
    command: tuple[str, ...] = ()
    env: Mapping[str, str] = field(default_factory=dict)
    network_none: bool = False


@dataclass(frozen=True)
class RuntimeChoice:
    runtime: str
    isolation_tier: str  # schema: 'gvisor' or 'runc-hardened'
    degraded: bool


def choose_runtime(configured: str, available: set[str], allow_degraded: bool) -> RuntimeChoice:
    """Never a silent fallback: runsc, or runc only when ABH_ALLOW_DEGRADED=true (section 8, rule 5)."""
    if configured == "runsc" and "runsc" in available:
        return RuntimeChoice("runsc", "gvisor", False)
    if allow_degraded and "runc" in available:
        return RuntimeChoice("runc", "runc-hardened", True)
    raise IsolationUnavailable(
        f"sandbox runtime {configured!r} is not available (daemon runtimes: {sorted(available)}) "
        "and ABH_ALLOW_DEGRADED is false; refusing to provision"
    )


def container_name(env: EnvRow, spec_name: str) -> str:
    return f"abh-{env.id}-{spec_name}"


def net_name(env: EnvRow) -> str:
    return f"abh-env-{env.id}"


def volume_name(env: EnvRow) -> str:
    return f"abh-vol-{env.id}"


def labels(env: EnvRow) -> dict[str, str]:
    return {"abh.managed": "true", "abh.env_id": env.id, "abh.team_id": env.team_id, "abh.template": env.template}


def _check(env: EnvRow, spec: ContainerSpec, workspace: Mapping[str, object]) -> None:
    if not CONTAINER_NAME_RE.match(spec.name):
        raise ProfileError(f"invalid container name {spec.name!r}")
    if not DIGEST_RE.match(spec.image):
        raise ProfileError(f"image {spec.image!r} is not referenced by sha256 digest")
    bad = [k for k in spec.env if k.upper().startswith("ABH_")]
    if bad:
        raise ProfileError(f"ABH_ variables may not enter a sandbox: {bad}")
    if not all(isinstance(v, str) for v in spec.env.values()):
        raise ProfileError("environment values must be strings")
    for n in (spec.cpu_millis, spec.mem_mb, env.pids_limit):
        if not isinstance(n, int) or isinstance(n, bool) or n <= 0:
            raise ProfileError(f"limits must be positive integers, got {n!r}")
    volume = {"Target": WORKSPACE, "Source": volume_name(env), "Type": "volume", "ReadOnly": False}
    if dict(workspace) != volume and not (
        set(workspace) == {"Target", "Type", "Options"} and workspace["Target"] == WORKSPACE
        and workspace["Type"] == "tmpfs" and TMPFS_OPTS_RE.match(str(workspace["Options"]))
    ):
        raise ProfileError("workspace must be this env's volume or a sized tmpfs at /workspace, never a host directory")


def build_create_kwargs(
    env: EnvRow, spec: ContainerSpec, choice: RuntimeChoice, workspace: Mapping[str, object]
) -> dict[str, object]:
    """Every section 8 setting for one container, as docker-py ``containers.create`` keyword arguments.

    Only /tmp and the workspace (a volume, or a tmpfs for storage V3) are produced; the file-analysis sample mount (B6) is not
    implemented here, so no third mount can be requested.
    """
    _check(env, spec, workspace)
    kwargs: dict[str, object] = {
        "image": spec.image,
        "command": list(spec.command) or None,
        "name": container_name(env, spec.name),
        "detach": True,
        "runtime": choice.runtime,
        "user": SANDBOX_USER,
        "cap_drop": ["ALL"],
        "security_opt": ["no-new-privileges"],
        "read_only": True,
        "privileged": False,
        "tmpfs": dict(TMP_TMPFS),
        "mounts": [],
        "nano_cpus": spec.cpu_millis * 1_000_000,
        "mem_limit": f"{spec.mem_mb}m",
        "memswap_limit": f"{spec.mem_mb}m",
        "pids_limit": env.pids_limit,
        "environment": dict(spec.env),
        "labels": labels(env),
    }
    if workspace["Type"] == "tmpfs":  # storage V3: HostConfig.Tmpfs, the form B0 check 8 tests
        kwargs["tmpfs"] = {**TMP_TMPFS, WORKSPACE: str(workspace["Options"])}
    else:
        kwargs["mounts"] = [dict(workspace)]
    if spec.network_none:
        kwargs["network_mode"] = "none"
    else:
        kwargs["network"] = net_name(env)
    return kwargs


def launch(client: Any, env: EnvRow, spec: ContainerSpec, choice: RuntimeChoice, workspace: Mapping[str, object]) -> Any:
    """The only place the runner creates a container. ``client`` is a ``docker.DockerClient``."""
    kwargs = build_create_kwargs(env, spec, choice, workspace)
    image = kwargs.pop("image")
    container = client.containers.create(image, **kwargs)
    container.start()
    return container
