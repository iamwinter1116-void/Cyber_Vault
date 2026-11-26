"""Unit tests for SSE stream scope filtering."""

from __future__ import annotations

from uuid import UUID

from services.api.routes.monitor import scope_allows_event

TEAM_A = UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")
TEAM_B = UUID("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb")


def test_sse_scope_filtering() -> None:
    assert scope_allows_event("admin", None, "audit", str(TEAM_A)) is True
    assert scope_allows_event("auditor", None, "audit", str(TEAM_B)) is True
    assert scope_allows_event("team_lead", TEAM_A, "audit", str(TEAM_A)) is True
    assert scope_allows_event("team_lead", TEAM_A, "audit", str(TEAM_B)) is False
    assert scope_allows_event("analyst", TEAM_A, "audit", str(TEAM_A)) is False

    assert scope_allows_event("analyst", TEAM_A, "activity", str(TEAM_A)) is True
    assert scope_allows_event("analyst", TEAM_A, "activity", str(TEAM_B)) is False
    assert scope_allows_event("analyst", TEAM_A, "metric", str(TEAM_A)) is True
    assert scope_allows_event("analyst", TEAM_A, "metric", str(TEAM_B)) is False
