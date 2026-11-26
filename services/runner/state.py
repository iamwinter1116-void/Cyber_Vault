"""Reconciler decisions for one env row (contracts/schema.sql env, docs/08 section 3, 04 sections 6 and 7.6).

Pure: the caller does the Docker work first, then writes the state, the audit record and the activity events in
one short transaction (risk R-10). The API offers no start operation, so ``stopped`` with desired ``running``
cannot arise from the API and is left unchanged rather than guessed at.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

OBSERVED = frozenset({"requested", "provisioning", "running", "stopped", "destroyed", "failed"})
DESIRED = frozenset({"running", "stopped", "destroyed"})


class Work(Enum):
    PROVISION = "provision"
    STOP = "stop"
    DESTROY = "destroy"


@dataclass(frozen=True)
class Step:
    work: Work
    target_state: str  # observed_state written after the Docker work succeeds
    audit_action: str  # closed list of section 7.6
    activity: tuple[tuple[str, str], ...]  # (kind, severity), closed list of section 6


def _changed(*extra: tuple[str, str]) -> tuple[tuple[str, str], ...]:
    return (("env.state_changed", "info"), *extra)


PROVISION = Step(Work.PROVISION, "running", "env.provisioned", _changed())
STOP = Step(Work.STOP, "stopped", "env.stopped", _changed())
DESTROY = Step(Work.DESTROY, "destroyed", "env.destroyed", _changed())
EXPIRE = Step(Work.DESTROY, "destroyed", "env.expired", _changed(("env.expired", "info")))
FAILED = Step(Work.DESTROY, "failed", "env.failed", _changed(("env.failed", "warn")))  # cleanup after an error


def decide(observed: str, desired: str, expired: bool) -> Step | None:
    """The next step for one row, or None when it has converged or is terminal."""
    if observed not in OBSERVED or desired not in DESIRED:
        raise ValueError(f"state outside the schema CHECK lists: observed={observed!r} desired={desired!r}")
    if observed == "destroyed":
        return None
    if desired == "destroyed":
        return DESTROY
    if expired:
        return EXPIRE
    if observed == "failed":
        return None
    if desired == "stopped":
        return None if observed == "stopped" else STOP
    if observed in ("requested", "provisioning"):  # provisioning again = resume after a runner crash
        return PROVISION
    return None
