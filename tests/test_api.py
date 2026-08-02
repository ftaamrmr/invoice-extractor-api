
import io

import pytest
from httpx import ASGITransport, AsyncClient
from PIL import Image

from app.config import settings
from app.main import app


def _headers():
    return {"X-API-Key": settings.API_KEY}


def _minimal_pdf() -> bytes:
    return (
        b"%PDF-1.4\n"
        b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
        b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
        b"3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R/Resources<<>>>>endobj\n"
        b"xref\n0 4\n0000000000 65535 f\n0000000009 00000 n\n0000000058 00000 n\n0000000115 00000 n\n"
        b"trailer<</Size 4/Root 1 0 R>>\nstartxref\n200\n%%EOF"
    )


def _tiny_png() -> bytes:
    image = Image.new("RGB", (1, 1), color="white")
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


@pytest.mark.anyio
async def test_health_and_ready():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        h = await c.get("/health")
        r = await c.get("/ready")
    assert h.status_code == 200
    assert r.status_code in (200, 503)


@pytest.mark.anyio
async def test_request_id_header_present():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/health")
    assert "x-request-id" in {k.lower() for k in r.headers.keys()}


@pytest.mark.anyio
async def test_extract_requires_auth_when_no_key():
    settings.DIRECT_API_ACCESS_ENABLED = True
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post("/v1/invoices/extract", files={"file": ("inv.pdf", _minimal_pdf(), "application/pdf")})
    assert r.status_code == 401


@pytest.mark.anyio
async def test_extract_text_guard_disabled():
    settings.INCLUDE_RAW_TEXT = False
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post("/v1/invoices/extract-text", headers=_headers(), files={"file": ("inv.pdf", _minimal_pdf(), "application/pdf")})
    assert r.status_code == 403


@pytest.mark.anyio
async def test_invalid_file_rejected():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post("/v1/invoices/extract", headers=_headers(), files={"file": ("fake.pdf", b"not_a_pdf", "application/pdf")})
    assert r.status_code in (415, 422)


@pytest.mark.anyio
async def test_rate_limit_headers_when_enabled(monkeypatch):
    settings.RATE_LIMIT_ENABLED = True
    settings.RATE_LIMIT_REQUESTS = 2
    settings.RATE_LIMIT_WINDOW_SECONDS = 60
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.post("/v1/invoices/extract", headers=_headers(), files={"file": ("inv.pdf", _minimal_pdf(), "application/pdf")})
        assert "x-ratelimit-limit" in {k.lower() for k in r.headers.keys()} or r.status_code == 429
    finally:
        settings.RATE_LIMIT_ENABLED = False


@pytest.mark.anyio
async def test_ocr_timeout_returns_structured_504(monkeypatch):
    settings.ENABLE_OCR = True

    async def fake_timeout(_: bytes) -> str:
        raise TimeoutError

    monkeypatch.setattr("app.services.invoice_extractor.ocr_image_bytes", fake_timeout)

    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.post("/v1/invoices/extract", headers=_headers(), files={"file": ("scan.png", _tiny_png(), "image/png")})
    finally:
        settings.ENABLE_OCR = False

    payload = r.json()
    assert r.status_code == 504
    assert payload["error"]["code"] == "PROCESSING_TIMEOUT"
    assert "x-request-id" in {k.lower() for k in r.headers.keys()}
