from __future__ import annotations

import io
import os
import re
from dataclasses import dataclass

from fastapi import UploadFile
from PIL import Image, UnidentifiedImageError

from app.config import settings
from app.errors import APIError

ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg"}
_CHUNK_SIZE = 64 * 1024
_PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
_JPEG_SIGNATURE = b"\xff\xd8\xff"


@dataclass
class ValidatedUpload:
    content: bytes
    filename: str
    sanitized_filename: str
    file_type: str
    size_bytes: int
    page_count: int | None = None


def sanitize_filename(filename: str) -> str:
    base = os.path.basename(filename or "uploaded_file")
    cleaned = re.sub(r"[^A-Za-z0-9._-]", "_", base)
    cleaned = cleaned.strip("._") or "uploaded_file"
    return cleaned[:120]


def _ext_for_filename(filename: str) -> str:
    if "." not in filename:
        return ""
    return "." + filename.rsplit(".", 1)[-1].lower()


def _detect_magic_type(content: bytes) -> str | None:
    if content.startswith(b"%PDF-"):
        return "pdf"
    if content.startswith(_PNG_SIGNATURE):
        return "png"
    if content.startswith(_JPEG_SIGNATURE):
        return "jpeg"
    return None


def _expected_type_for_ext(ext: str) -> str | None:
    if ext == ".pdf":
        return "pdf"
    if ext == ".png":
        return "png"
    if ext in {".jpg", ".jpeg"}:
        return "jpeg"
    return None


def _validate_image(content: bytes) -> tuple[str, int]:
    Image.MAX_IMAGE_PIXELS = settings.MAX_IMAGE_PIXELS
    try:
        with Image.open(io.BytesIO(content)) as img:
            img.verify()
        with Image.open(io.BytesIO(content)) as img2:
            width, height = img2.size
            if width <= 0 or height <= 0:
                raise APIError(422, "INVALID_IMAGE", "The image is invalid.")
            pixels = width * height
            if pixels > settings.MAX_IMAGE_PIXELS:
                raise APIError(413, "IMAGE_TOO_LARGE", "Image dimensions exceed allowed limits.")
            return "image", pixels
    except Image.DecompressionBombError:
        raise APIError(413, "IMAGE_TOO_LARGE", "Image dimensions exceed allowed limits.")
    except APIError:
        raise
    except (UnidentifiedImageError, OSError, ValueError):
        raise APIError(422, "INVALID_IMAGE", "The image is invalid.")


def _validate_pdf(content: bytes) -> int:
    try:
        import fitz

        with fitz.open(stream=content, filetype="pdf") as doc:
            if doc.is_encrypted or doc.needs_pass:
                raise APIError(422, "PDF_ENCRYPTED", "Encrypted PDF files are not supported.")
            page_count = doc.page_count
            if page_count <= 0:
                raise APIError(422, "INVALID_PDF", "The PDF is invalid.")
            if page_count > settings.MAX_PDF_PAGES:
                raise APIError(422, "PDF_PAGE_LIMIT_EXCEEDED", "PDF page count exceeds the allowed limit.")

            for page in doc:
                rect = page.rect
                if rect.width <= 0 or rect.height <= 0 or rect.width > 20_000 or rect.height > 20_000:
                    raise APIError(422, "INVALID_PDF", "The PDF has invalid page dimensions.")
            return page_count
    except APIError:
        raise
    except Exception:
        raise APIError(422, "INVALID_PDF", "The PDF is invalid.")


async def validate_upload(file: UploadFile) -> ValidatedUpload:
    filename = file.filename or "uploaded_file"
    ext = _ext_for_filename(filename)
    if ext not in ALLOWED_EXTENSIONS:
        raise APIError(415, "UNSUPPORTED_FILE_TYPE", "Only PDF, PNG, JPG, and JPEG files are supported.")

    max_bytes = settings.MAX_FILE_SIZE_MB * 1024 * 1024
    content = bytearray()

    try:
        while True:
            chunk = await file.read(_CHUNK_SIZE)
            if not chunk:
                break
            content.extend(chunk)
            if len(content) > max_bytes:
                raise APIError(413, "FILE_TOO_LARGE", "File size exceeds the allowed limit.")

        if not content:
            raise APIError(422, "EMPTY_FILE", "The uploaded file is empty.")

        magic_type = _detect_magic_type(content)
        if not magic_type:
            raise APIError(415, "UNSUPPORTED_FILE_TYPE", "Unsupported or invalid file content.")

        expected_type = _expected_type_for_ext(ext)
        if expected_type != magic_type:
            raise APIError(415, "MIME_MISMATCH", "File extension does not match file content.")

        page_count = None
        file_type = "pdf" if magic_type == "pdf" else "image"
        if file_type == "pdf":
            page_count = _validate_pdf(content)
        else:
            _validate_image(content)

        return ValidatedUpload(
            content=bytes(content),
            filename=filename,
            sanitized_filename=sanitize_filename(filename),
            file_type=file_type,
            size_bytes=len(content),
            page_count=page_count,
        )
    finally:
        await file.close()
