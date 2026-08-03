import io

import pytest
from fastapi import UploadFile

from app.config import settings
from app.errors import APIError
from app.services.file_validator import validate_upload


@pytest.mark.anyio
async def test_empty_file_rejected():
    upload = UploadFile(filename="x.pdf", file=io.BytesIO(b""))
    with pytest.raises(APIError) as exc:
        await validate_upload(upload)
    assert exc.value.code == "EMPTY_FILE"


@pytest.mark.anyio
async def test_mime_mismatch_rejected():
    upload = UploadFile(filename="x.pdf", file=io.BytesIO(b"\x89PNG\r\n\x1a\nabc"))
    with pytest.raises(APIError) as exc:
        await validate_upload(upload)
    assert exc.value.code == "MIME_MISMATCH"


@pytest.mark.anyio
async def test_file_too_large_rejected():
    old = settings.MAX_FILE_SIZE_MB
    settings.MAX_FILE_SIZE_MB = 1
    try:
        upload = UploadFile(filename="x.pdf", file=io.BytesIO(b"%PDF-" + b"a" * (2 * 1024 * 1024)))
        with pytest.raises(APIError) as exc:
            await validate_upload(upload)
        assert exc.value.code == "FILE_TOO_LARGE"
    finally:
        settings.MAX_FILE_SIZE_MB = old


@pytest.mark.anyio
async def test_corrupted_png_rejected():
    upload = UploadFile(filename="broken.png", file=io.BytesIO(b"\x89PNG\r\n\x1a\nbroken"))
    with pytest.raises(APIError) as exc:
        await validate_upload(upload)
    assert exc.value.code == "INVALID_IMAGE"
