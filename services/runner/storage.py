"""Workspace storage ladder (docs/08 section 4): V1 loop image, V2 tmpfs volume, V3 tmpfs mount.

B0 check 8 picks the first method that passes on the Linux host and records it in evidence/preflight.md.
Until that result exists CHOSEN_METHOD is None and the runner refuses to provision; no method is assumed.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

from services.runner.launch import WORKSPACE, EnvRow, canonical_id, labels, volume_name

METHODS = ("V1", "V2", "V3")
CHOSEN_METHOD: str | None = None  # set from B0 check 8 output, by commit, once it has run on the demo host


class StorageUnavailable(RuntimeError):
    """No storage method has been chosen, or an unknown one was named."""


def require(method: str | None) -> str:
    if method not in METHODS:
        raise StorageUnavailable(f"storage method {method!r} not chosen by B0 preflight check 8 (docs/08 section 4)")
    return method


def image_path(volume_dir: str, env: EnvRow) -> Path:
    return Path(volume_dir) / f"{env.id}.img"


def volume_create_kwargs(env: EnvRow, method: str, volume_dir: str) -> dict[str, object] | None:
    """docker-py ``volumes.create`` arguments (name, driver, driver_opts, labels), or None for V3."""
    if require(method) == "V3":
        return None
    if method == "V1":
        opts = {"type": "ext4", "device": str(image_path(volume_dir, env)), "o": "loop"}
    else:
        opts = {"type": "tmpfs", "device": "tmpfs", "o": f"size={env.storage_mb}m,uid=1000,gid=1000"}
    return {"name": volume_name(env), "driver": "local", "driver_opts": opts, "labels": labels(env)}


def workspace(env: EnvRow, method: str) -> dict[str, object]:
    """The /workspace argument for launch(): the env's volume, or for V3 a sized tmpfs."""
    if require(method) == "V3":
        return {"Target": WORKSPACE, "Type": "tmpfs", "Options": f"size={env.storage_mb}m,uid=1000,gid=1000"}
    return {"Target": WORKSPACE, "Source": volume_name(env), "Type": "volume", "ReadOnly": False}


def make_image(volume_dir: str, env: EnvRow) -> None:
    """V1: sparse file of storage_mb formatted ext4 with root owned by 1000:1000; renamed into place when done."""
    final = image_path(volume_dir, env)
    if final.exists():
        return
    tmp = final.with_name(final.name + ".tmp")
    with open(tmp, "wb") as f:
        f.truncate(env.storage_mb * 1024 * 1024)
    subprocess.run(["mkfs.ext4", "-q", "-E", "root_owner=1000:1000", str(tmp)], check=True, timeout=60)
    os.replace(tmp, final)


def image_env_ids(volume_dir: str) -> set[str]:
    """Env ids named by V1 image files (<id>.img, <id>.img.tmp), so the reaper also finds an image whose volume
    was never created (runner crash between make_image and volumes.create). Other files are never touched."""
    root = Path(volume_dir)
    if not root.is_dir():
        return set()
    names = (p.name.removesuffix(".tmp") for p in root.iterdir() if p.is_file())
    return {i for n in names if n.endswith(".img") and (i := canonical_id(n.removesuffix(".img"))) is not None}


def remove_image(volume_dir: str, env_id: str) -> None:
    """env_id may come from a Docker label (reaper), so only a canonical UUID may name a file."""
    if canonical_id(env_id) is None:
        raise ValueError(f"not a canonical env id: {env_id!r}")
    for p in (Path(volume_dir) / f"{env_id}.img", Path(volume_dir) / f"{env_id}.img.tmp"):
        p.unlink(missing_ok=True)
