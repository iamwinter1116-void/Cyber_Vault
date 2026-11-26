"""Real-time SSE stream (R22) and activity events list (R23)."""

from __future__ import annotations

import asyncio
import contextlib
import json
from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Annotated, Literal, cast
from uuid import UUID

import psycopg
from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse
from psycopg_pool import ConnectionPool

from services.api.authz import ScopedAuth, authorize
from services.api.deps import get_pool
from services.api.schemas import ActivityEventOut

router = APIRouter(tags=["monitor"])


def scope_allows_event(
    role: str,
    caller_team_id: UUID | None,
    event_type: Literal["activity", "audit", "metric"],
    event_team_id: str | None,
) -> bool:
    """Apply server-side scope filtering per docs/04_CONTRACTS.md section 6."""
    if event_type == "audit":
        if role in ("admin", "auditor"):
            return True
        if role == "team_lead":
            return caller_team_id is not None and event_team_id == str(caller_team_id)
        return False
    if role in ("admin", "auditor"):
        return True
    return caller_team_id is not None and event_team_id == str(caller_team_id)


def _row_to_event(row: tuple[object, ...]) -> ActivityEventOut:
    return ActivityEventOut(
        id=int(cast(int, row[0])),
        ts=str(row[1]),
        team_id=cast(UUID | None, row[2]),
        env_id=cast(UUID | None, row[3]),
        severity=cast(Literal["info", "warn", "critical"], str(row[4])),
        kind=str(row[5]),
        message=str(row[6]),
        data=cast(dict[str, object], row[7]),
    )


@dataclass
class _Subscriber:
    role: str
    team_id: UUID | None
    queue: asyncio.Queue[str]


class StreamHub:
    """Single-process PostgreSQL LISTEN/NOTIFY fan-out to bounded subscriber queues."""

    def __init__(self) -> None:
        self._subs: set[_Subscriber] = set()
        self._task: asyncio.Task[None] | None = None

    def ensure_started(self, pool: ConnectionPool[psycopg.Connection[tuple[object, ...]]], dsn: str) -> None:
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self._listen_loop(pool, dsn))

    def subscribe(self, role: str, team_id: UUID | None) -> _Subscriber:
        sub = _Subscriber(role=role, team_id=team_id, queue=asyncio.Queue(maxsize=128))
        self._subs.add(sub)
        return sub

    def unsubscribe(self, sub: _Subscriber) -> None:
        self._subs.discard(sub)

    def _publish(self, event_type: Literal["activity", "audit", "metric"], team_id: str | None, frame: str) -> None:
        for sub in list(self._subs):
            if not scope_allows_event(sub.role, sub.team_id, event_type, team_id):
                continue
            try:
                sub.queue.put_nowait(frame)
            except asyncio.QueueFull:
                self._subs.discard(sub)

    async def _listen_loop(
        self,
        pool: ConnectionPool[psycopg.Connection[tuple[object, ...]]],
        dsn: str,
    ) -> None:
        while self._subs:
            try:
                async with await psycopg.AsyncConnection.connect(dsn, autocommit=True) as aconn:
                    await aconn.execute("LISTEN abh_activity; LISTEN abh_audit; LISTEN abh_metric;")
                    async for notify in aconn.notifies():
                        self._handle_notify(pool, notify.channel, notify.payload)
            except asyncio.CancelledError:
                raise
            except psycopg.Error:
                await asyncio.sleep(1.0)

    def _handle_notify(
        self,
        pool: ConnectionPool[psycopg.Connection[tuple[object, ...]]],
        channel: str,
        payload: str,
    ) -> None:
        if channel == "abh_metric":
            data = cast(dict[str, object], json.loads(payload))
            team_id = cast(str | None, data.get("team_id"))
            self._publish("metric", team_id, f"event: metric\ndata: {payload}\n\n")
            return
        if channel == "abh_activity":
            with pool.connection() as conn, conn.cursor() as cur:
                cur.execute(
                    "SELECT id, to_char(ts AT TIME ZONE 'UTC', 'YYYY-MM-DD\"T\"HH24:MI:SS\"Z\"'), "
                    "team_id, env_id, severity, kind, message, data FROM activity_event WHERE id = %s",
                    (int(payload),),
                )
                row = cur.fetchone()
            if row is not None:
                ev = _row_to_event(row)
                tid = None if ev.team_id is None else str(ev.team_id)
                self._publish("activity", tid, f"id: {ev.id}\nevent: activity\ndata: {ev.model_dump_json()}\n\n")
            return
        if channel == "abh_audit":
            with pool.connection() as conn, conn.cursor() as cur:
                cur.execute(
                    "SELECT v, seq, ts, actor_type, actor_id, actor_role, team_id, action, "
                    "target_type, target_id, outcome, ip, request_id, detail, prev_hash, hash "
                    "FROM audit_log WHERE seq = %s",
                    (int(payload),),
                )
                row = cur.fetchone()
            if row is not None:
                keys = (
                    "v", "seq", "ts", "actor_type", "actor_id", "actor_role", "team_id", "action",
                    "target_type", "target_id", "outcome", "ip", "request_id", "detail", "prev_hash", "hash",
                )
                rec = dict(zip(keys, row, strict=True))
                self._publish("audit", str(rec["team_id"]), f"event: audit\ndata: {json.dumps(rec)}\n\n")


_HUB = StreamHub()


@router.get("/events")
def list_events(
    auth: Annotated[ScopedAuth, Depends(authorize("R23"))],
    severity: str | None = None,
    env_id: UUID | None = None,
    after_id: int | None = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    cursor: int | None = None,
) -> dict[str, object]:
    """List activity events in caller's scope."""
    where_parts = ["true"]
    params: list[object] = []
    if auth.scope == "team":
        where_parts.append("team_id = %s")
        params.append(auth.ctx.user.team_id)
    if severity is not None:
        where_parts.append("severity = %s")
        params.append(severity)
    if env_id is not None:
        where_parts.append("env_id = %s")
        params.append(env_id)
    min_id = after_id if after_id is not None else cursor
    if min_id is not None:
        where_parts.append("id > %s")
        params.append(min_id)
    params.append(limit + 1)
    sql = (
        "SELECT id, to_char(ts AT TIME ZONE 'UTC', 'YYYY-MM-DD\"T\"HH24:MI:SS\"Z\"'), "
        f"team_id, env_id, severity, kind, message, data FROM activity_event WHERE {' AND '.join(where_parts)} "
        "ORDER BY id LIMIT %s"
    )
    with auth.ctx.transaction() as conn, conn.cursor() as cur:
        cur.execute(sql, params)
        rows = cur.fetchall()
    has_more = len(rows) > limit
    items = [_row_to_event(r) for r in rows[:limit]]
    return {"items": items, "next_cursor": str(items[-1].id) if has_more else None}


@router.get("/stream")
async def stream_events(
    request: Request,
    auth: Annotated[ScopedAuth, Depends(authorize("R22"))],
) -> StreamingResponse:
    """Server-Sent Events stream with server-side scope filter, resume, and 15s heartbeat."""
    pool = get_pool(request)
    last_id_hdr = request.headers.get("Last-Event-ID", "").strip()
    replay: list[str] = []
    if last_id_hdr.isdigit() and pool is not None:
        where = "id > %s" if auth.scope == "all" else "id > %s AND team_id = %s"
        params: tuple[object, ...] = (int(last_id_hdr),) if auth.scope == "all" else (int(last_id_hdr), auth.ctx.user.team_id)
        with pool.connection() as conn, conn.cursor() as cur:
            cur.execute(
                "SELECT id, to_char(ts AT TIME ZONE 'UTC', 'YYYY-MM-DD\"T\"HH24:MI:SS\"Z\"'), "
                f"team_id, env_id, severity, kind, message, data FROM activity_event WHERE {where} ORDER BY id",
                params,
            )
            for row in cur.fetchall():
                ev = _row_to_event(row)
                replay.append(f"id: {ev.id}\nevent: activity\ndata: {ev.model_dump_json()}\n\n")

    sub = _HUB.subscribe(auth.ctx.user.role, auth.ctx.user.team_id)
    if pool is not None:
        raw_dsn = auth.ctx.pool.conninfo
        dsn = raw_dsn if isinstance(raw_dsn, str) else raw_dsn()
        _HUB.ensure_started(pool, dsn)

    async def _gen() -> AsyncIterator[str]:
        try:
            for frame in replay:
                yield frame
            while True:
                if await request.is_disconnected():
                    break
                try:
                    yield await asyncio.wait_for(sub.queue.get(), timeout=15.0)
                except TimeoutError:
                    ts = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
                    yield f"event: heartbeat\ndata: {json.dumps({'ts': ts})}\n\n"
        except asyncio.CancelledError:
            with contextlib.suppress(Exception):
                _HUB.unsubscribe(sub)
            raise
        finally:
            _HUB.unsubscribe(sub)

    return StreamingResponse(
        _gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
