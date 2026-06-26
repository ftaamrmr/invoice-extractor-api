"""
API key authentication for protected endpoints.

Public endpoints (no auth required):
    /  /health  /docs  /redoc  /openapi.json  /static/*

Protected endpoints require ONE of:
    - Header  X-API-Key                (direct / self-hosted usage)
    - Header  X-RapidAPI-Proxy-Secret  (RapidAPI proxy traffic)

APP_ENV behaviour:
    production  → key is ALWAYS required; missing or wrong key → 401.
    development → key is optional; missing key is allowed for easy local testing.
                  If a key IS provided in dev mode it is still validated.
"""
from typing import Optional
from fastapi import Header, HTTPException, status
from app.config import settings

# Placeholder values that must not be accepted as real keys in production
_PLACEHOLDER_KEYS = {
    "change-me-api-key",
    "change-me-local-api-key",
    "change-me-rapidapi-secret",
}


def _is_valid_key(provided: Optional[str], expected: str) -> bool:
    """Return True only if the provided key matches expected and is not a placeholder."""
    if not provided:
        return False
    if provided in _PLACEHOLDER_KEYS:
        return False
    return provided == expected


def verify_api_key(
    x_api_key: Optional[str] = Header(default=None),
    x_rapidapi_proxy_secret: Optional[str] = Header(default=None),
) -> None:
    """
    FastAPI dependency injected into every protected route.
    Raises HTTP 401 when authentication fails in production mode.
    """
    is_production = settings.APP_ENV == "production"

    # ── Development: allow unauthenticated requests ───────────────────────────
    if not is_production:
        if x_api_key is None and x_rapidapi_proxy_secret is None:
            return  # skip auth in dev when no key supplied

    # ── Check RapidAPI proxy secret ───────────────────────────────────────────
    if _is_valid_key(x_rapidapi_proxy_secret, settings.RAPIDAPI_PROXY_SECRET):
        return

    # ── Check direct API key ──────────────────────────────────────────────────
    if _is_valid_key(x_api_key, settings.API_KEY):
        return

    # ── Reject ────────────────────────────────────────────────────────────────
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={
            "success": False,
            "error": {
                "code": "UNAUTHORIZED",
                "message": "Valid API key is required. "
                           "Provide X-API-Key or X-RapidAPI-Proxy-Secret header.",
            },
        },
    )
