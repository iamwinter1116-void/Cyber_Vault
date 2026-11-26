"""Per-environment network (docs/04_CONTRACTS.md section 8, Network row).

docker-py 7.2.0 ``APIClient.create_network(name, driver, options, ipam, check_duplicate, internal, labels, ...)``
(docker/api/network.py). The isolated gateway mode is the network option B0's check 6 tests; the firewall
fallback named in docs/08 is not implemented, so a host that rejects the option cannot provision.
"""

from __future__ import annotations

from typing import Any

from services.runner.launch import EnvRow, labels, net_name

GATEWAY_MODE_OPTION = "com.docker.network.bridge.gateway_mode_ipv4"


def network_create_kwargs(env: EnvRow) -> dict[str, object]:
    return {
        "name": net_name(env),
        "driver": "bridge",
        "internal": True,
        "options": {GATEWAY_MODE_OPTION: "isolated"},
        "labels": labels(env),
    }


def create_network(client: Any, env: EnvRow) -> Any:
    """``client`` is a ``docker.DockerClient``; no published ports exist anywhere in the profile."""
    kwargs = network_create_kwargs(env)
    name = kwargs.pop("name")
    return client.networks.create(name, **kwargs)
