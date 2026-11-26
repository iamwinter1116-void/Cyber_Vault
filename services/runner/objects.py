"""Docker side of the reconciler (docs/08 section 3). Every object is named from the env id and looked up before
creation, so a runner killed mid-provision converges on restart (T-RES-06). Calls checked against docker-py 7.2.0
source; none has run against a daemon yet (Linux-host acceptance pending).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import docker.errors

from services.runner import storage
from services.runner.launch import (
    EnvRow,
    RuntimeChoice,
    canonical_id,
    choose_runtime,
    container_name,
    launch,
    net_name,
    network_create_kwargs,
    volume_name,
)
from services.runner.templates import container_specs, load_template

MANAGED = "abh.managed=true"


class DockerOps:
    def __init__(self, client: Any, *, runtime: str, allow_degraded: bool, volume_dir: str,
                 templates_dir: Path, storage_method: str | None) -> None:
        self.client, self.runtime, self.allow_degraded = client, runtime, allow_degraded
        self.volume_dir, self.templates_dir, self.storage_method = volume_dir, templates_dir, storage_method

    def provision(self, env: EnvRow) -> RuntimeChoice:
        method = storage.require(self.storage_method)
        choice = choose_runtime(self.runtime, set(self.client.info().get("Runtimes") or {}), self.allow_degraded)
        specs = container_specs(load_template(self.templates_dir, env.template), env)
        if not self._exists(self.client.networks, net_name(env)):
            self.client.networks.create(**network_create_kwargs(env))
        kwargs = storage.volume_create_kwargs(env, method, self.volume_dir)
        if kwargs is not None and not self._exists(self.client.volumes, volume_name(env)):
            if method == "V1":
                storage.make_image(self.volume_dir, env)
            self.client.volumes.create(**kwargs)
        workspace = storage.workspace(env, method)
        for spec in specs:
            try:
                container = self.client.containers.get(container_name(env, spec.name))
            except docker.errors.NotFound:
                launch(self.client, env, spec, choice, workspace)
                continue
            if container.status != "running":
                container.start()
        return choice

    def stop(self, env: EnvRow) -> None:
        for c in self._by_env(env.id):
            c.stop(timeout=10)

    def destroy(self, env_id: str) -> None:
        """Remove every container, network and volume labelled with env_id, then the V1 image file."""
        flt = {"label": f"abh.env_id={env_id}"}
        for c in self._by_env(env_id):
            c.remove(force=True)
        for n in self.client.networks.list(filters=flt):
            n.remove()
        for v in self.client.volumes.list(filters=flt):
            v.remove(force=True)
        storage.remove_image(self.volume_dir, env_id)

    def labelled_env_ids(self) -> set[str]:
        """Canonical abh.env_id of every abh.managed=true object, plus env ids named by V1 image files."""
        ids = {i for _, lbl, _ in self._managed() if (i := canonical_id(lbl.get("abh.env_id"))) is not None}
        return ids | storage.image_env_ids(self.volume_dir)

    def remove_unowned(self) -> int:
        """abh.managed=true objects without a canonical abh.env_id match no env row ("missing" in the section 8
        lifetime rule), so they are removed directly. Containers go first so networks and volumes are free."""
        removed = 0
        for kind, lbl, obj in self._managed():
            if canonical_id(lbl.get("abh.env_id")) is not None:
                continue
            if kind == "network":
                obj.remove()
            else:
                obj.remove(force=True)
            removed += 1
        return removed

    def _managed(self) -> list[tuple[str, dict[str, str], Any]]:
        flt = {"label": MANAGED}
        out = [("container", dict(c.labels), c) for c in self.client.containers.list(all=True, filters=flt)]
        for kind, coll in (("network", self.client.networks), ("volume", self.client.volumes)):
            out += [(kind, dict(o.attrs.get("Labels") or {}), o) for o in coll.list(filters=flt)]
        return out

    def _by_env(self, env_id: str) -> list[Any]:
        return list(self.client.containers.list(all=True, filters={"label": f"abh.env_id={env_id}"}))

    @staticmethod
    def _exists(collection: Any, name: str) -> bool:
        try:
            collection.get(name)
        except docker.errors.NotFound:
            return False
        return True
