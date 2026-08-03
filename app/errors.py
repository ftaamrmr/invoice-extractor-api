from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class APIError(Exception):
    status_code: int
    code: str
    message: str
    headers: dict[str, str] | None = None


class OCRTimeoutError(Exception):
    """Raised when an OCR operation exceeds the configured timeout."""


def error_response_payload(code: str, message: str, request_id: str) -> dict[str, Any]:
    return {
        "success": False,
        "error": {"code": code, "message": message},
        "request_id": request_id,
    }
