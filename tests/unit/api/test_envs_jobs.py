"""Unit tests for env sizes and quarantine upload streaming."""

from __future__ import annotations

import hashlib
import io
import stat
from pathlib import Path

import pytest
from fastapi import UploadFile
from services.api.middleware import ApiError
from services.api.routes.envs import SIZES
from services.api.routes.jobs import MAX_UPLOAD_BYTES, stream_to_quarantine


def test_env_sizes_match_contract() -> None:
    assert SIZES["S"] == (500, 256, 128, 128)
    assert SIZES["M"] == (1000, 512, 256, 256)
    assert SIZES["L"] == (2000, 1024, 512, 512)


@pytest.mark.anyio
async def test_stream_to_quarantine_hashes_and_enforces_limit(tmp_path: Path) -> None:
    payload = b"hello-abhedya-sample"
    up = UploadFile(filename="../../evil.bin", file=io.BytesIO(payload))
    digest, size = await stream_to_quarantine(up, tmp_path)
    assert digest == hashlib.sha256(payload).hexdigest()
    assert size == len(payload)
    saved = tmp_path / digest
    assert saved.read_bytes() == payload
    assert stat.S_IMODE(saved.stat().st_mode) == 0o400

    too_big = UploadFile(filename="big.bin", file=io.BytesIO(b"a" * (MAX_UPLOAD_BYTES + 1)))
    with pytest.raises(ApiError) as exc_info:
        await stream_to_quarantine(too_big, tmp_path)
    assert exc_info.value.status_code == 413
    assert exc_info.value.code == "PAYLOAD_TOO_LARGE"
