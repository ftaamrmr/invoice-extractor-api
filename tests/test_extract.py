"""
Production-hardened tests for the /v1/invoices/extract endpoint.

Covers:
  - /health returns 200 (no auth)
  - Protected endpoint without key → 401 in production mode
  - Protected endpoint with wrong key → 401 in production mode
  - Protected endpoint with correct X-API-Key → 200
  - Protected endpoint with correct X-RapidAPI-Proxy-Secret → 200
  - Unsupported file type → 422 with UNSUPPORTED_FILE_TYPE
  - Empty file → 422 with EMPTY_FILE
  - File too large → 413 with FILE_TOO_LARGE
  - PDF extraction returns expected response shape
  - /extract-text endpoint works
  - Parser: invoice number, total, VAT, SAR currency, Arabic fields
"""
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.config import settings

# NOTE: conftest.py sets settings.API_KEY and settings.RAPIDAPI_PROXY_SECRET
# before this module loads, so these lambdas always use the current value.
def _headers_direct():
    return {"X-API-Key": settings.API_KEY}

def _headers_rapidapi():
    return {"X-RapidAPI-Proxy-Secret": settings.RAPIDAPI_PROXY_SECRET}

# Convenience aliases used in synchronous parser tests (no auth needed)



# ── Helper: build a minimal in-memory text PDF via PyMuPDF ────────────────────

def _make_text_pdf(text: str = "Invoice No: INV-001\nTotal: 1150.00 SAR") -> bytes:
    """Build a real text-embedded PDF for testing."""
    try:
        import fitz  # PyMuPDF
        doc = fitz.open()
        page = doc.new_page()
        page.insert_text((72, 100), text, fontsize=11)
        data = doc.tobytes()
        doc.close()
        return data
    except ImportError:
        return _minimal_bare_pdf()


def _minimal_bare_pdf() -> bytes:
    """Fallback: hand-crafted minimal PDF (no embedded text)."""
    return (
        b"%PDF-1.4\n"
        b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
        b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
        b"3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R"
        b"/Resources<<>>>>endobj\n"
        b"xref\n0 4\n"
        b"0000000000 65535 f\n"
        b"0000000009 00000 n\n"
        b"0000000058 00000 n\n"
        b"0000000115 00000 n\n"
        b"trailer<</Size 4/Root 1 0 R>>\nstartxref\n200\n%%EOF"
    )


# ── Fixture: production mode context manager ──────────────────────────────────

class _ProductionMode:
    """Context manager that temporarily sets APP_ENV=production."""
    def __enter__(self):
        self._original = settings.APP_ENV
        settings.APP_ENV = "production"
        return self

    def __exit__(self, *_):
        settings.APP_ENV = self._original


def _prod():
    return _ProductionMode()


# ── Health check (public – no auth) ──────────────────────────────────────────

@pytest.mark.anyio
async def test_health_returns_200():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/health")
    assert r.status_code == 200


@pytest.mark.anyio
async def test_health_response_shape():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/health")
    body = r.json()
    assert body["status"] == "ok"
    assert "service" in body
    assert "version" in body
    assert "environment" in body


@pytest.mark.anyio
async def test_health_requires_no_auth():
    """Health check must work without any API key."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/health")  # no headers at all
    assert r.status_code == 200


# ── Root endpoint (public) ────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_root_returns_200():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/")
    assert r.status_code == 200


# ── Authentication: production mode ──────────────────────────────────────────

@pytest.mark.anyio
async def test_extract_without_key_returns_401_in_production():
    with _prod():
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.post(
                "/v1/invoices/extract",
                files={"file": ("inv.pdf", _minimal_bare_pdf(), "application/pdf")},
            )
    assert r.status_code == 401
    body = r.json()
    assert body["error"]["code"] == "UNAUTHORIZED"


@pytest.mark.anyio
async def test_extract_with_wrong_key_returns_401_in_production():
    with _prod():
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.post(
                "/v1/invoices/extract",
                headers={"X-API-Key": "totally-wrong-key"},
                files={"file": ("inv.pdf", _minimal_bare_pdf(), "application/pdf")},
            )
    assert r.status_code == 401


@pytest.mark.anyio
async def test_extract_with_correct_api_key_passes_auth():
    """X-API-Key with the configured key must be accepted."""
    pdf = _make_text_pdf("Invoice No: TEST-001\nTotal: 100.00 USD")
    with _prod():
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.post(
                "/v1/invoices/extract",
                headers=_headers_direct(),
                files={"file": ("inv.pdf", pdf, "application/pdf")},
            )
    # 200 or 422 (if OCR unavailable) — both mean auth passed
    assert r.status_code in (200, 422)


@pytest.mark.anyio
async def test_extract_with_rapidapi_secret_passes_auth():
    """X-RapidAPI-Proxy-Secret with the configured secret must be accepted."""
    pdf = _make_text_pdf("Invoice No: TEST-002\nTotal: 200.00 SAR")
    with _prod():
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.post(
                "/v1/invoices/extract",
                headers=_headers_rapidapi(),
                files={"file": ("inv.pdf", pdf, "application/pdf")},
            )
    assert r.status_code in (200, 422)


# ── File validation ───────────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_unsupported_file_type_returns_422():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post(
            "/v1/invoices/extract",
            headers=_headers_direct(),
            files={"file": ("report.docx", b"fake content", "application/octet-stream")},
        )
    assert r.status_code == 422
    body = r.json()
    assert body["error"]["code"] == "UNSUPPORTED_FILE_TYPE"


@pytest.mark.anyio
async def test_empty_file_returns_422():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post(
            "/v1/invoices/extract",
            headers=_headers_direct(),
            files={"file": ("inv.pdf", b"", "application/pdf")},
        )
    assert r.status_code == 422
    body = r.json()
    assert body["error"]["code"] == "EMPTY_FILE"


@pytest.mark.anyio
async def test_file_too_large_returns_413():
    """Upload a file larger than MAX_FILE_SIZE_MB and expect 413."""
    original_limit = settings.MAX_FILE_SIZE_MB
    settings.MAX_FILE_SIZE_MB = 1  # temporarily lower the limit to 1 MB
    try:
        large_content = b"A" * (2 * 1024 * 1024)  # 2 MB
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.post(
                "/v1/invoices/extract",
                headers=_headers_direct(),
                files={"file": ("big.pdf", large_content, "application/pdf")},
            )
        assert r.status_code == 413
        body = r.json()
        assert body["error"]["code"] == "FILE_TOO_LARGE"
    finally:
        settings.MAX_FILE_SIZE_MB = original_limit


# ── Extraction: response shape ────────────────────────────────────────────────

@pytest.mark.anyio
async def test_extract_pdf_response_shape():
    pdf = _make_text_pdf("Invoice No: INV-2024-001\nTotal: 1150.00 SAR\nDate: 15/01/2024")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post(
            "/v1/invoices/extract",
            headers=_headers_direct(),
            files={"file": ("inv.pdf", pdf, "application/pdf")},
        )
    assert r.status_code == 200
    body = r.json()
    assert body["success"] is True
    assert "data" in body
    assert "meta" in body
    assert body["meta"]["file_type"] == "pdf"
    assert "confidence_score" in body["data"]
    assert "raw_text" in body["data"]
    assert "X-Processing-Time" in r.headers


@pytest.mark.anyio
async def test_extract_text_endpoint_returns_raw_text():
    pdf = _make_text_pdf("Invoice No: INV-TEXT-TEST\nTotal: 500.00 USD")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post(
            "/v1/invoices/extract-text",
            headers=_headers_direct(),
            files={"file": ("inv.pdf", pdf, "application/pdf")},
        )
    assert r.status_code == 200
    body = r.json()
    assert body["success"] is True
    assert "raw_text" in body["data"]


# ── Parser unit tests ─────────────────────────────────────────────────────────

def test_parser_extracts_invoice_number():
    from app.services.parser import parse_invoice
    result = parse_invoice("Invoice Number: INV-2024-009\nTotal Amount: 500.00")
    assert result["invoice_number"] == "INV-2024-009"


def test_parser_extracts_total_amount():
    from app.services.parser import parse_invoice
    result = parse_invoice("Total Amount: 1,150.00\nVAT: 150.00")
    assert result["total_amount"] == 1150.00


def test_parser_extracts_vat():
    from app.services.parser import parse_invoice
    result = parse_invoice("Subtotal: 1000.00\nVAT: 150.00\nTotal: 1150.00")
    assert result["tax_amount"] == 150.00


def test_parser_detects_sar_currency():
    from app.services.parser import parse_invoice
    result = parse_invoice("Total: 500 SAR\nInvoice No: 001")
    assert result["currency"] == "SAR"


def test_parser_detects_usd_currency():
    from app.services.parser import parse_invoice
    result = parse_invoice("Total: $250.00\nInvoice No: INV-US-01")
    assert result["currency"] == "USD"


def test_parser_confidence_increases_with_fields():
    from app.services.parser import parse_invoice
    low = parse_invoice("some random text")
    high = parse_invoice(
        "Invoice Number: INV-001\nInvoice Date: 01/01/2024\n"
        "Total Amount: 1150.00\nVAT: 150.00\nVendor: Acme Corp\nSAR"
    )
    assert high["confidence_score"] > low["confidence_score"]


def test_parser_arabic_invoice_number():
    from app.services.parser import parse_invoice
    result = parse_invoice("رقم الفاتورة: INV-2024-AR-001\nالإجمالي: 500")
    assert result["invoice_number"] == "INV-2024-AR-001"


def test_parser_arabic_total():
    from app.services.parser import parse_invoice
    result = parse_invoice("الإجمالي: 1150.00\nرقم الفاتورة: AR-001")
    assert result["total_amount"] == 1150.00


def test_parser_arabic_vat():
    from app.services.parser import parse_invoice
    result = parse_invoice("ضريبة القيمة المضافة: 150.00\nالإجمالي: 1150.00")
    assert result["tax_amount"] == 150.00


def test_parser_invoice_date():
    from app.services.parser import parse_invoice
    result = parse_invoice("Invoice Date: 15/01/2024\nTotal: 500.00")
    assert result["invoice_date"] == "15/01/2024"


def test_parser_returns_null_for_missing_fields():
    from app.services.parser import parse_invoice
    result = parse_invoice("Hello world, this is not an invoice.")
    assert result["invoice_number"] is None
    assert result["total_amount"] is None
    assert result["currency"] is None
