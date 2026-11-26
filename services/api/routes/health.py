"""Health endpoint (rule R31)."""

from __future__ import annotations

import psycopg
from fastapi import APIRouter, Request

from services.api.deps import get_pool
from services.api.schemas import HealthzOut

router = APIRouter(tags=["health"])


@router.get("/healthz", response_model=HealthzOut)
def healthz(request: Request) -> HealthzOut:
    """Return service status and live database connectivity."""
    pool = get_pool(request)
    db_ok = False
    if pool is not None:
        try:
            with pool.connection() as conn, conn.cursor() as cur:
                cur.execute("SELECT 1")
                db_ok = cur.fetchone() is not None
        except psycopg.Error:
            db_ok = False
    return HealthzOut(status="ok", db=db_ok)
