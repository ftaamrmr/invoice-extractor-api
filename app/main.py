"""
FastAPI application entry point.

Registers:
  - CORS middleware
  - Static file mount (/static)
  - Global exception handlers (validation errors, 404, 500)
  - Route: GET /          landing page
  - Route: GET /health    health check (no auth)
  - Router: /v1/invoices  extraction endpoints (auth required)
"""
import os
import logging

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config import settings
from app.routes.extract import router as extract_router

logger = logging.getLogger(__name__)

# ── App instance ──────────────────────────────────────────────────────────────

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "Extract structured invoice data from PDF and image files. "
        "Returns vendor name, invoice number, dates, amounts, line items, and more."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
    # Expose openapi schema so RapidAPI can import endpoint definitions
    openapi_url="/openapi.json",
)

# ── CORS (open for API consumers) ─────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["X-Processing-Time"],
)

# ── Static files ──────────────────────────────────────────────────────────────

# Resolve path relative to this file so it works from any working directory
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(_BASE_DIR, "..", "static")
STATIC_DIR = os.path.normpath(STATIC_DIR)

if os.path.isdir(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# ── Global exception handlers ─────────────────────────────────────────────────

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """
    Convert all HTTP errors to a consistent JSON envelope.
    Preserves the detail dict if our code already built one; wraps bare strings.
    """
    detail = exc.detail

    # If our own code raised with a structured dict, pass it through
    if isinstance(detail, dict) and "error" in detail:
        return JSONResponse(status_code=exc.status_code, content=detail)

    # Map common status codes to machine-readable error codes
    code_map = {
        400: "BAD_REQUEST",
        401: "UNAUTHORIZED",
        403: "FORBIDDEN",
        404: "NOT_FOUND",
        405: "METHOD_NOT_ALLOWED",
        413: "FILE_TOO_LARGE",
        422: "UNPROCESSABLE_ENTITY",
        429: "TOO_MANY_REQUESTS",
        500: "INTERNAL_SERVER_ERROR",
    }
    code = code_map.get(exc.status_code, "HTTP_ERROR")
    message = str(detail) if detail else code.replace("_", " ").title()

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {"code": code, "message": message},
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    FastAPI form/body validation errors (e.g. missing required file field).
    Returns 422 with a structured error envelope instead of FastAPI's default format.
    """
    errors = exc.errors()
    # Surface the first meaningful error message
    first = errors[0] if errors else {}
    message = first.get("msg", "Request validation failed.")
    loc = " → ".join(str(l) for l in first.get("loc", []))
    if loc:
        message = f"{loc}: {message}"

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "success": False,
            "error": {
                "code": "VALIDATION_ERROR",
                "message": message,
            },
        },
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """
    Catch-all for unexpected server errors.
    Logs the full traceback internally but never leaks it to the client.
    """
    logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected error occurred. Please try again later.",
            },
        },
    )


# ── Routers ───────────────────────────────────────────────────────────────────

app.include_router(extract_router)

# ── Root endpoint ─────────────────────────────────────────────────────────────

@app.get("/", include_in_schema=False)
async def root():
    """Serve static landing page if present, otherwise return API info JSON."""
    index_path = os.path.join(STATIC_DIR, "index.html")
    if os.path.isfile(index_path):
        return FileResponse(index_path)
    return JSONResponse({
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.APP_ENV,
        "docs": "/docs",
        "health": "/health",
        "endpoints": [
            "POST /v1/invoices/extract",
            "POST /v1/invoices/extract-text",
        ],
    })


# ── Health check ──────────────────────────────────────────────────────────────

@app.get("/health", tags=["system"], include_in_schema=True)
async def health():
    """
    Public health check endpoint. No authentication required.
    Used by Coolify, load balancers, and uptime monitors.
    """
    return {
        "status": "ok",
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.APP_ENV,
    }
