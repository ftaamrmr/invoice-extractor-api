from __future__ import annotations

import asyncio
import logging
import os
import tempfile
import time
import uuid

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config import settings
from app.errors import APIError, error_response_payload
from app.logging_utils import configure_logging
from app.rate_limiter import rate_limiter, resolve_identity
from app.routes.extract import router as extract_router
from app.services.ocr_service import check_tesseract_ready

configure_logging()
logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Extract structured invoice fields from PDF and image files.",
    docs_url="/docs" if settings.EXPOSE_DOCS else None,
    redoc_url="/redoc" if settings.EXPOSE_DOCS else None,
    openapi_url="/openapi.json" if settings.EXPOSE_DOCS else None,
)

cors_origins = settings.cors_allowed_origins_list
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "X-API-Key", "X-RapidAPI-Proxy-Secret", "X-Request-ID"],
    expose_headers=["X-Request-ID", "X-Processing-Time", "X-RateLimit-Limit", "X-RateLimit-Remaining", "Retry-After"],
)

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.normpath(os.path.join(_BASE_DIR, "..", "static"))
if os.path.isdir(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.middleware("http")
async def request_context_middleware(request: Request, call_next):
    request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
    request.state.request_id = request_id
    started = time.monotonic()

    rate_result = None
    if settings.RATE_LIMIT_ENABLED and request.url.path.startswith("/v1/"):
        rate_result = rate_limiter.check(resolve_identity(request))
        if not rate_result.allowed:
            payload = error_response_payload("RATE_LIMIT_EXCEEDED", "Too many requests.", request_id)
            return JSONResponse(
                status_code=429,
                content=payload,
                headers={
                    "X-Request-ID": request_id,
                    "Retry-After": str(rate_result.retry_after),
                    "X-RateLimit-Limit": str(rate_result.limit),
                    "X-RateLimit-Remaining": str(rate_result.remaining),
                },
            )

    try:
        response = await asyncio.wait_for(call_next(request), timeout=settings.REQUEST_TIMEOUT_SECONDS)
    except TimeoutError:
        payload = error_response_payload("PROCESSING_TIMEOUT", "The request timed out.", request_id)
        return JSONResponse(status_code=504, content=payload, headers={"X-Request-ID": request_id})

    duration_ms = int((time.monotonic() - started) * 1000)

    response.headers["X-Request-ID"] = request_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["Content-Security-Policy"] = "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'"
    if settings.ENABLE_HSTS:
        response.headers["Strict-Transport-Security"] = f"max-age={settings.HSTS_MAX_AGE_SECONDS}; includeSubDomains"

    if rate_result is not None:
        response.headers["X-RateLimit-Limit"] = str(rate_result.limit)
        response.headers["X-RateLimit-Remaining"] = str(rate_result.remaining)

    logger.info(
        "request_complete",
        extra={
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "status": response.status_code,
            "processing_time": duration_ms,
        },
    )
    return response


@app.exception_handler(APIError)
async def api_error_handler(request: Request, exc: APIError):
    payload = error_response_payload(exc.code, exc.message, getattr(request.state, "request_id", "unknown"))
    headers = {"X-Request-ID": getattr(request.state, "request_id", "unknown")}
    if exc.headers:
        headers.update(exc.headers)
    return JSONResponse(status_code=exc.status_code, content=payload, headers=headers)


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    code_map = {
        400: "BAD_REQUEST",
        401: "UNAUTHORIZED",
        403: "FORBIDDEN",
        404: "NOT_FOUND",
        413: "FILE_TOO_LARGE",
        415: "UNSUPPORTED_FILE_TYPE",
        422: "UNPROCESSABLE_ENTITY",
        429: "RATE_LIMIT_EXCEEDED",
        500: "INTERNAL_SERVER_ERROR",
        503: "SERVICE_UNAVAILABLE",
    }
    code = code_map.get(exc.status_code, "HTTP_ERROR")
    message = "Request failed."
    payload = error_response_payload(code, message, getattr(request.state, "request_id", "unknown"))
    return JSONResponse(status_code=exc.status_code, content=payload, headers={"X-Request-ID": getattr(request.state, "request_id", "unknown")})


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    payload = error_response_payload("VALIDATION_ERROR", "Request validation failed.", getattr(request.state, "request_id", "unknown"))
    return JSONResponse(status_code=422, content=payload, headers={"X-Request-ID": getattr(request.state, "request_id", "unknown")})


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.error(
        "unhandled_exception",
        extra={
            "request_id": getattr(request.state, "request_id", "unknown"),
            "method": request.method,
            "path": request.url.path,
            "status": 500,
            "error_code": "INTERNAL_SERVER_ERROR",
        },
    )
    payload = error_response_payload(
        "INTERNAL_SERVER_ERROR",
        "An internal server error occurred.",
        getattr(request.state, "request_id", "unknown"),
    )
    return JSONResponse(status_code=500, content=payload, headers={"X-Request-ID": getattr(request.state, "request_id", "unknown")})


app.include_router(extract_router)


@app.get("/", include_in_schema=False)
async def root():
    index_path = os.path.join(STATIC_DIR, "index.html")
    if os.path.isfile(index_path):
        return FileResponse(index_path)
    return {
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/docs" if settings.EXPOSE_DOCS else None,
        "health": "/health",
    }


@app.get("/health", tags=["system"])
async def health():
    return {"status": "ok", "service": settings.APP_NAME, "version": settings.APP_VERSION}


@app.get("/ready", tags=["system"])
async def ready():
    checks: dict[str, str] = {}

    try:
        import fitz  # noqa: F401

        checks["pymupdf"] = "ok"
    except Exception:
        checks["pymupdf"] = "failed"

    try:
        from PIL import Image  # noqa: F401

        checks["pillow"] = "ok"
    except Exception:
        checks["pillow"] = "failed"

    try:
        with tempfile.NamedTemporaryFile(delete=True) as tmp:
            tmp.write(b"ok")
        checks["tempfile"] = "ok"
    except Exception:
        checks["tempfile"] = "failed"

    if settings.ENABLE_OCR:
        ok, msg = check_tesseract_ready(settings.OCR_LANGUAGES)
        checks["tesseract"] = "ok" if ok else msg
    else:
        checks["tesseract"] = "disabled"

    all_ok = all(v == "ok" or v == "disabled" for v in checks.values())
    payload = {
        "status": "ok" if all_ok else "not_ready",
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
    }
    return JSONResponse(status_code=200 if all_ok else 503, content=payload)
