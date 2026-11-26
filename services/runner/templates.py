"""Template policy for sandbox/templates/<name>/template.yaml (docs/04_CONTRACTS.md sections 4 and 8, D12).

parse_template validates a parsed mapping; load_template reads the file with PyYAML (allowlisted; its
registry check is pending in evidence/VERSIONS.lock, so load_template has not been run yet).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from services.runner.launch import DIGEST_RE, ContainerSpec, EnvRow, ProfileError

# section 8: the container set of each template
TEMPLATE_CONTAINERS: dict[str, frozenset[str]] = {
    "app-target": frozenset({"target", "toolbox"}),
    "file-analysis": frozenset({"analyzer", "detonator"}),
    "ai-redteam": frozenset({"llm-target", "scanner"}),
}
ISOLATION_PROFILE = "[T0.H2.N2] "  # decision D12; degraded mode is reported as T0.H1.N2
TOP_KEYS = frozenset({"name", "title", "description", "sizes", "containers"})
CONTAINER_KEYS = frozenset({"name", "image", "share_pct", "command", "env", "network"})


@dataclass(frozen=True)
class TemplateContainer:
    name: str
    image: str
    share_pct: int
    command: tuple[str, ...]
    env: Mapping[str, str]
    network_none: bool


@dataclass(frozen=True)
class Template:
    """The parts the runner uses; title, description and sizes are validated but not kept."""

    name: str
    containers: tuple[TemplateContainer, ...]


def _container(template: str, raw: object) -> TemplateContainer:
    if not isinstance(raw, Mapping) or set(raw) - CONTAINER_KEYS or not {"name", "image", "share_pct"} <= set(raw):
        raise ProfileError(f"{template}: container entries need name, image, share_pct and no other keys")
    image, share, network = raw["image"], raw["share_pct"], raw.get("network", "env")
    if not isinstance(image, str) or not DIGEST_RE.match(image):
        raise ProfileError(f"{template}/{raw['name']}: image must be referenced by sha256 digest")
    if not isinstance(share, int) or isinstance(share, bool) or not 0 < share <= 100:
        raise ProfileError(f"{template}/{raw['name']}: share_pct must be an integer 1..100")
    if network not in ("env", "none") or (template == "file-analysis" and network != "none"):
        raise ProfileError(f"{template}/{raw['name']}: network must be 'env' or 'none' ('none' for file-analysis)")
    command, env = raw.get("command", []), raw.get("env", {})
    if not isinstance(command, Sequence) or isinstance(command, str) or not all(isinstance(c, str) for c in command):
        raise ProfileError(f"{template}/{raw['name']}: command must be a list of strings")
    if not isinstance(env, Mapping) or not all(isinstance(k, str) and isinstance(v, str) for k, v in env.items()):
        raise ProfileError(f"{template}/{raw['name']}: env must map strings to strings")
    return TemplateContainer(str(raw["name"]), image, share, tuple(command), dict(env), network == "none")


def parse_template(data: object) -> Template:
    """Refuse anything outside the allowlisted shape; never fill in a default image."""
    if not isinstance(data, Mapping) or set(data) != TOP_KEYS:
        raise ProfileError(f"template keys must be exactly {sorted(TOP_KEYS)}")
    name, desc, sizes = data["name"], data["description"], data["sizes"]
    if name not in TEMPLATE_CONTAINERS:
        raise ProfileError(f"unknown template {name!r}")
    if not isinstance(desc, str) or not desc.startswith(ISOLATION_PROFILE):
        raise ProfileError(f"{name}: description must start with the isolation profile {ISOLATION_PROFILE.strip()}")
    if not isinstance(sizes, list) or not sizes or set(sizes) - {"S", "M", "L"} or len(set(sizes)) != len(sizes):
        raise ProfileError(f"{name}: sizes must be a non-empty list drawn from S, M, L")
    if not isinstance(data["containers"], list):
        raise ProfileError(f"{name}: containers must be a list")
    containers = tuple(_container(name, c) for c in data["containers"])
    if sorted(c.name for c in containers) != sorted(TEMPLATE_CONTAINERS[name]):
        raise ProfileError(f"{name}: containers must be exactly {sorted(TEMPLATE_CONTAINERS[name])}")
    if sum(c.share_pct for c in containers) != 100:
        raise ProfileError(f"{name}: share_pct values must sum to 100")
    return Template(name, containers)


def load_template(templates_dir: Path, name: str) -> Template:
    """Read sandbox/templates/<name>/template.yaml with yaml.safe_load (PyYAML; safe for untrusted input)."""
    import yaml  # PyYAML, allowlisted; imported here so the pure validators above need no third-party package

    if name not in TEMPLATE_CONTAINERS:
        raise ProfileError(f"unknown template {name!r}")
    with open(templates_dir / name / "template.yaml", encoding="utf-8") as f:
        template = parse_template(yaml.safe_load(f))
    if template.name != name:
        raise ProfileError(f"{templates_dir / name}/template.yaml names {template.name!r}")
    return template


def split(total: int, shares: Sequence[int]) -> list[int]:
    """Integer split whose sum equals ``total`` exactly; the last container takes the rounding remainder."""
    parts = [total * s // 100 for s in shares[:-1]]
    parts.append(total - sum(parts))
    if any(p <= 0 for p in parts):
        raise ProfileError(f"cannot split {total} into positive parts by {list(shares)}")
    return parts


def container_specs(template: Template, env: EnvRow) -> list[ContainerSpec]:
    """Per-container limits whose sums equal the environment's cpu_millis and mem_mb (docs/08 section 3)."""
    if env.template != template.name:
        raise ProfileError(f"env template {env.template!r} does not match {template.name!r}")
    shares = [c.share_pct for c in template.containers]
    cpus, mems = split(env.cpu_millis, shares), split(env.mem_mb, shares)
    return [
        ContainerSpec(c.name, c.image, cpu, mem, c.command, c.env, c.network_none)
        for c, cpu, mem in zip(template.containers, cpus, mems, strict=True)
    ]
