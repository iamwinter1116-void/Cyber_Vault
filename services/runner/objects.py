"""Docker side of the reconciler (docs/08 section 3). Every object is named from the env id and looked up before
creation, so a runner killed mid-provision converges on restart (T-RES-06). Calls checked against docker-py 7.2.0
source; none has run against a daemon yet (Linux-host acceptance pending).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import docker.errors

from services.runner import storage
from services.runner.launch import EnvRow, RuntimeChoice, choose_runtime, container_name, launch, net_name, volume_name
from services.runner.net import create_network
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
            create_network(self.client, env)
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
        """abh.env_id of every container, network and volume labelled abh.managed=true."""
        flt = {"label": MANAGED}
        ids = {str(c.labels.get("abh.env_id", "")) for c in self.client.containers.list(all=True, filters=flt)}
        for coll in (self.client.networks, self.client.volumes):
            ids |= {str((o.attrs.get("Labels") or {}).get("abh.env_id", "")) for o in coll.list(filters=flt)}
        ids.discard("")
        return ids

    def _by_env(self, env_id: str) -> list[Any]:
        return list(self.client.containers.list(all=True, filters={"label": f"abh.env_id={env_id}"}))

    @staticmethod
    def _exists(collection: Any, name: str) -> bool:
        try:
            collection.get(name)
        except docker.errors.NotFound:
            return False
        return True
