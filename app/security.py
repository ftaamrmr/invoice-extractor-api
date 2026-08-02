from __future__ import annotations

import secrets

from fastapi import Header

from app.config import settings
from app.errors import APIError


def _secure_equals(left: str | None, right: str) -> bool:
    if not left or not right:
        return False
    return secrets.compare_digest(left.strip(), right.strip())


def verify_api_key(
    x_api_key: str | None = Header(default=None),
    x_rapidapi_proxy_secret: str | None = Header(default=None),
) -> None:
    if settings.REQUIRE_RAPIDAPI_SECRET and x_rapidapi_proxy_secret:
        if _secure_equals(x_rapidapi_proxy_secret, settings.RAPIDAPI_PROXY_SECRET):
            return

    if settings.DIRECT_API_ACCESS_ENABLED:
        if _secure_equals(x_api_key, settings.API_KEY):
            return
    elif x_api_key:
        raise APIError(
            status_code=401,
            code="UNAUTHORIZED",
            message="Direct API access is disabled for this service.",
        )

    raise APIError(
        status_code=401,
        code="UNAUTHORIZED",
        message="Authentication failed for this endpoint.",
    )
