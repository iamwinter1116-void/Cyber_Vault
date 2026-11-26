"""Job, file-analysis, and AI-scan routes: R18-R21."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
import uuid
from pathlib import Path
from typing import Annotated, Literal, cast
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile

from core.abh_core.audit import append as audit_append
from core.abh_core.settings import Settings
from services.api.authz import ScopedAuth, authorize, record_denied
from services.api.middleware import ApiError
from services.api.quota import create_env_with_quota
from services.api.schemas import AiScanRequest, JobOut

router = APIRouter(tags=["jobs"])
MAX_UPLOAD_BYTES = 10 * 1024 * 1024

_JOB_COLS = (
    "id, kind, env_id, team_id, requested_by, input, status, result, "
    "to_char(created_at AT TIME ZONE 'UTC', 'YYYY-MM-DD\"T\"HH24:MI:SS\"Z\"'), "
    "to_char(started_at AT TIME ZONE 'UTC', 'YYYY-MM-DD\"T\"HH24:MI:SS\"Z\"'), "
    "to_char(finished_at AT TIME ZONE 'UTC', 'YYYY-MM-DD\"T\"HH24:MI:SS\"Z\"')"
)


def _row_to_job(row: tuple[object, ...]) -> JobOut:
    return JobOut(
        id=cast(UUID, row[0]),
        kind=cast(Literal["exec", "file_analysis", "ai_scan"], str(row[1])),
        env_id=cast(UUID, row[2]),
        team_id=cast(UUID, row[3]),
        requested_by=cast(UUID, row[4]),
        input=cast(dict[str, object], row[5]),
        status=cast(Literal["queued", "running", "done", "timeout", "error"], str(row[6])),
        result=cast(dict[str, object], row[7]),
        created_at=str(row[8]),
        started_at=cast(str | None, row[9]),
        finished_at=cast(str | None, row[10]),
    )


async def stream_to_quarantine(upload: UploadFile, quarantine_dir: Path) -> tuple[str, int]:
    """Stream upload to quarantine_dir/<sha256> (mode 0400) enforcing 10 MiB max."""
    quarantine_dir.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=".upload-", dir=str(quarantine_dir))
    tmp_path = Path(tmp_name)
    hasher = hashlib.sha256()
    total = 0
    try:
        with os.fdopen(fd, "wb") as out:
            while chunk := await upload.read(65536):
                total += len(chunk)
                if total > MAX_UPLOAD_BYTES:
                    raise ApiError("PAYLOAD_TOO_LARGE", 413, "File exceeds 10 MiB limit")
                hasher.update(chunk)
                out.write(chunk)
        digest = hasher.hexdigest()
        dest = quarantine_dir / digest
        os.chmod(tmp_path, 0o400)
        os.replace(tmp_path, dest)
        return digest, total
    except Exception:
        tmp_path.unlink(missing_ok=True)
        raise


@router.get("/jobs")
def list_jobs(
    auth: Annotated[ScopedAuth, Depends(authorize("R18"))],
    kind: str | None = None,
    env_id: UUID | None = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    cursor: UUID | None = None,
) -> dict[str, object]:
    where_parts = ["team_id = %s"]
    params: list[object] = [auth.ctx.user.team_id]
    if auth.scope == "own":
        where_parts.append("requested_by = %s")
        params.append(auth.ctx.user.id)
    if kind is not None:
        where_parts.append("kind = %s")
        params.append(kind)
    if env_id is not None:
        where_parts.append("env_id = %s")
        params.append(env_id)
    if cursor is not None:
        where_parts.append("id > %s")
        params.append(cursor)
    params.append(limit + 1)
    sql = f"SELECT {_JOB_COLS} FROM job WHERE {' AND '.join(where_parts)} ORDER BY id LIMIT %s"
    with auth.ctx.transaction() as conn, conn.cursor() as cur:
        cur.execute(sql, params)
        rows = cur.fetchall()
    has_more = len(rows) > limit
    items = [_row_to_job(r) for r in rows[:limit]]
    return {"items": items, "next_cursor": str(items[-1].id) if has_more else None}


@router.get("/jobs/{job_id}", response_model=JobOut)
def get_job(job_id: UUID, auth: Annotated[ScopedAuth, Depends(authorize("R19"))]) -> JobOut:
    with auth.ctx.transaction() as conn, conn.cursor() as cur:
        cur.execute(f"SELECT {_JOB_COLS} FROM job WHERE id = %s", (job_id,))
        row = cur.fetchone()
    if row is None:
        raise ApiError("NOT_FOUND", 404, "Not found")
    job = _row_to_job(row)
    if job.team_id != auth.ctx.user.team_id:
        record_denied(auth.ctx, auth.rule, target_type="job", target_id=str(job_id), reason="cross_team")
        raise ApiError("NOT_FOUND", 404, "Not found")
    if auth.scope == "own" and job.requested_by != auth.ctx.user.id:
        record_denied(auth.ctx, auth.rule, target_type="job", target_id=str(job_id), reason="not_owner")
        raise ApiError("FORBIDDEN", 403, "Forbidden")
    return job


@router.post("/files", status_code=202, response_model=JobOut)
async def submit_file(
    auth: Annotated[ScopedAuth, Depends(authorize("R20"))],
    file: Annotated[UploadFile, File()],
    detonate: Annotated[bool, Form()] = False,
) -> JobOut:
    """Stream sample to quarantine/<sha256> (0400), create S env + file_analysis job."""
    cfg = Settings()
    digest, size_bytes = await stream_to_quarantine(file, Path(cfg.quarantine_dir))
    filename = Path(file.filename or "sample").name[:128]
    job_input = {"sha256": digest, "filename": filename, "size_bytes": size_bytes, "detonate": detonate}
    with auth.ctx.transaction() as conn:
        env = create_env_with_quota(
            conn,
            auth,
            cfg,
            name=f"file-{uuid.uuid4().hex[:8]}",
            template="file-analysis",
            size="S",
            ttl_minutes=10,
        )
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO job (kind, env_id, team_id, requested_by, input) "
                f"VALUES ('file_analysis', %s, %s, %s, %s::jsonb) RETURNING {_JOB_COLS}",
                (env.id, env.team_id, auth.ctx.user.id, json.dumps(job_input)),
            )
            jrow = cur.fetchone()
            assert jrow is not None
        job = _row_to_job(jrow)
        audit_append(
            conn,
            actor=auth.ctx.actor,
            action="file.submit",
            target_type="job",
            target_id=str(job.id),
            outcome="success",
            ip=auth.ctx.ip,
            request_id=auth.ctx.request_id,
            detail={"sha256": digest, "size_bytes": size_bytes, "detonate": detonate},
        )
        return job


@router.post("/ai-scans", status_code=202, response_model=JobOut)
def start_ai_scan(
    body: AiScanRequest,
    auth: Annotated[ScopedAuth, Depends(authorize("R21"))],
) -> JobOut:
    """Create M ai-redteam env + queued ai_scan job."""
    cfg = Settings()
    job_input = {"target": body.target, "probe_set": body.probe_set}
    with auth.ctx.transaction() as conn:
        env = create_env_with_quota(
            conn,
            auth,
            cfg,
            name=f"ai-{uuid.uuid4().hex[:8]}",
            template="ai-redteam",
            size="M",
            ttl_minutes=10,
        )
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO job (kind, env_id, team_id, requested_by, input) "
                f"VALUES ('ai_scan', %s, %s, %s, %s::jsonb) RETURNING {_JOB_COLS}",
                (env.id, env.team_id, auth.ctx.user.id, json.dumps(job_input)),
            )
            jrow = cur.fetchone()
            assert jrow is not None
        job = _row_to_job(jrow)
        audit_append(
            conn,
            actor=auth.ctx.actor,
            action="ai.scan_start",
            target_type="job",
            target_id=str(job.id),
            outcome="success",
            ip=auth.ctx.ip,
            request_id=auth.ctx.request_id,
            detail={"target": body.target, "probe_set": body.probe_set},
        )
        return job
