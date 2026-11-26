"""Templates route: R10."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from services.api.authz import ScopedAuth, authorize
from services.api.schemas import TemplateOut

router = APIRouter(prefix="/templates", tags=["templates"])

_TEMPLATES: list[TemplateOut] = [
    TemplateOut(
        name="app-target",
        title="Web Application Target",
        description="[T0.H2.N2] Deliberately vulnerable web target paired with an isolated toolbox.",
        containers=["target", "toolbox"],
        sizes=["S", "M", "L"],
    ),
    TemplateOut(
        name="file-analysis",
        title="Suspicious File Triage",
        description="[T0.H2.N2] Static YARA-X triage and optional no-network Linux detonation.",
        containers=["analyzer", "detonator"],
        sizes=["S", "M", "L"],
    ),
    TemplateOut(
        name="ai-redteam",
        title="AI Red-Team Probe",
        description="[T0.H2.N2] Offline AI red-team probing mapped to OWASP LLM Top 10.",
        containers=["llm-target", "scanner"],
        sizes=["S", "M", "L"],
    ),
]


@router.get("")
def list_templates(_auth: Annotated[ScopedAuth, Depends(authorize("R10"))]) -> dict[str, list[TemplateOut]]:
    """Return the allowlisted environment templates."""
    return {"items": _TEMPLATES}
