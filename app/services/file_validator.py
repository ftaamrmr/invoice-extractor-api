"""
File validation service.

Checks (in order):
  1. Extension is in the allowed list
  2. File is not empty
  3. File does not exceed MAX_FILE_SIZE_MB

All failures raise HTTPException with a machine-readable error envelope.
"""
from fastapi import HTTPException, UploadFile, status
from app.config import settings

ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg"}


def _error(http_status: int, code: str, message: str) -> HTTPException:
    return HTTPException(
        status_code=http_status,
        detail={"success": False, "error": {"code": code, "message": message}},
    )


async def validate_upload(file: UploadFile) -> bytes:
    """
    Validate the uploaded file and return its raw bytes.
    Raises HTTPException on any validation failure.
    """
    # ── Extension check ───────────────────────────────────────────────────────
    filename = file.filename or ""
    ext = ("." + filename.rsplit(".", 1)[-1].lower()) if "." in filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise _error(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "UNSUPPORTED_FILE_TYPE",
            "Only PDF, PNG, JPG, and JPEG files are supported.",
        )

    # ── Read bytes ────────────────────────────────────────────────────────────
    content = await file.read()

    # ── Empty file ────────────────────────────────────────────────────────────
    if len(content) == 0:
        raise _error(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "EMPTY_FILE",
            "The uploaded file is empty.",
        )

    # ── Size limit ────────────────────────────────────────────────────────────
    # Compute limit from current settings so runtime env changes are respected
    max_bytes = settings.MAX_FILE_SIZE_MB * 1024 * 1024
    if len(content) > max_bytes:
        raise _error(
            status.HTTP_413_CONTENT_TOO_LARGE,
            "FILE_TOO_LARGE",
            f"File size exceeds the allowed limit of {settings.MAX_FILE_SIZE_MB} MB.",
        )

    return content
