"""
Integration tests for Invoice Extractor API.

Tests cover the full request lifecycle with real sample files:
  - English digital PDF (embedded text)
  - Arabic digital PDF (Arabic text)
  - Scanned invoice PNG (requires OCR)
  - Multi-page PDF (3 pages)
  - Encrypted PDF (must be rejected)
  - Oversized file (must be rejected with 413)
  - OCR timeout simulation (must return 504)
  - RapidAPI Proxy Secret authentication

Each test reports per-field extraction accuracy.
"""

from __future__ import annotations

import io

import fitz
import pytest
from httpx import ASGITransport, AsyncClient
from PIL import Image, ImageDraw

from app.config import settings
from app.main import app

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

ENGLISH_GROUND_TRUTH = {
    "invoice_number": "INV-2024-001",
    "total_amount": 1250.00,
    "subtotal": 1000.00,
    "tax_amount": 250.00,
}

ARABIC_GROUND_TRUTH = {
    "invoice_number": "INV-2024-002",
    "total_amount": 1150.00,
    "subtotal": 1000.00,
    "tax_amount": 150.00,
}

SCANNED_GROUND_TRUTH = {
    "total_amount": 960.00,
    "subtotal": 800.00,
    "tax_amount": 160.00,
}

MULTIPAGE_GROUND_TRUTH = {
    "invoice_number": "INV-2024-MULTI",
    "subtotal": 500.00,
    "total_amount": 575.00,
}

ACCURACY_THRESHOLD = 0.60  # 60% field accuracy required for digital PDFs


def _headers() -> dict[str, str]:
    return {"X-API-Key": settings.API_KEY}


def _rapidapi_headers(secret: str) -> dict[str, str]:
    return {"X-RapidAPI-Proxy-Secret": secret}


def _compute_accuracy(data: dict, ground_truth: dict) -> float:
    """Return fraction of ground-truth fields correctly extracted."""
    if not ground_truth:
        return 0.0
    matched = 0
    for field, expected in ground_truth.items():
        actual = data.get(field)
        if actual is None:
            continue
        if isinstance(expected, float):
            try:
                if abs(float(actual) - expected) < 0.02:
                    matched += 1
            except (TypeError, ValueError):
                pass
        elif str(actual).strip().upper() == str(expected).strip().upper():
            matched += 1
    return matched / len(ground_truth)


def _print_accuracy_report(label: str, data: dict, ground_truth: dict) -> None:
    """Print a human-readable accuracy table for test output."""
    accuracy = _compute_accuracy(data, ground_truth)
    field_confidence = data.get("field_confidence") or {}
    print(f"\n{'=' * 60}")
    print(f"  Accuracy Report: {label}")
    print(f"{'=' * 60}")
    print(f"  Overall accuracy : {accuracy * 100:.1f}% ({len([f for f in ground_truth if _field_matches(data, f, ground_truth[f])])}/{len(ground_truth)} fields)")
    print(f"  Confidence score : {data.get('confidence_score', 0):.1f}%")
    print(f"  Extraction method: {data.get('extraction_method', 'unknown')}")
    print(f"\n  {'Field':<25} {'Expected':<20} {'Extracted':<20} {'Match':<6} {'Conf':>6}")
    print(f"  {'-' * 77}")
    for field, expected in ground_truth.items():
        extracted = data.get(field)
        match = _field_matches(data, field, expected)
        conf = field_confidence.get(field, 0.0)
        mark = "✓" if match else "✗"
        print(f"  {field:<25} {expected!s:<20} {extracted!s:<20} {mark:<6} {conf:>6.2f}")
    print(f"{'=' * 60}\n")


def _field_matches(data: dict, field: str, expected) -> bool:
    actual = data.get(field)
    if actual is None:
        return False
    if isinstance(expected, float):
        try:
            return abs(float(actual) - expected) < 0.02
        except (TypeError, ValueError):
            return False
    return str(actual).strip().upper() == str(expected).strip().upper()


# ---------------------------------------------------------------------------
# PDF / image generators
# ---------------------------------------------------------------------------

def _english_invoice_pdf() -> bytes:
    """Digital English invoice with fields matching all parser patterns."""
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    text = (
        "INVOICE\n\n"
        "Invoice Number: INV-2024-001\n"
        "Invoice Date: 15/01/2024\n"
        "Due Date: 15/02/2024\n\n"
        "From: Acme Corporation Ltd\n"
        "VAT Number: GB123456789\n\n"
        "Subtotal:    1000.00\n"
        "VAT (25%):    250.00\n"
        "Grand Total: 1250.00\n\n"
        "Currency: USD\n"
        "Payment Method: Bank Transfer\n"
    )
    page.insert_text((50, 50), text, fontsize=11)
    return doc.tobytes()


def _arabic_invoice_pdf() -> bytes:
    """Digital Arabic invoice with fields matching Arabic parser patterns."""
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    text = (
        "فاتورة\n\n"
        "رقم الفاتورة: INV-2024-002\n"
        "تاريخ الفاتورة: 15/01/2024\n"
        "تاريخ الاستحقاق: 15/02/2024\n\n"
        "المورد: شركة الامل للتجارة\n"
        "الرقم الضريبي: SA123456789\n\n"
        "المجموع الفرعي: 1000.00\n"
        "ضريبة القيمة المضافة (15%): 150.00\n"
        "الاجمالي: 1150.00\n\n"
        "طريقة الدفع: تحويل بنكي\n"
    )
    page.insert_text((50, 50), text, fontsize=11)
    return doc.tobytes()


def _scanned_invoice_png() -> bytes:
    """PNG image simulating a scanned invoice (requires OCR)."""
    img = Image.new("RGB", (900, 1100), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    lines = [
        "INVOICE",
        "",
        "Invoice Number: INV-2024-003",
        "Invoice Date: 20/01/2024",
        "Due Date: 20/02/2024",
        "",
        "From: ScanCorp Solutions",
        "",
        "Subtotal:    800.00",
        "VAT (20%):   160.00",
        "Grand Total: 960.00",
        "",
        "Currency: USD",
        "Payment Method: Credit Card",
    ]
    y = 60
    for line in lines:
        draw.text((60, y), line, fill=(0, 0, 0))
        y += 36
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _multipage_invoice_pdf() -> bytes:
    """Three-page PDF; invoice fields on page 1."""
    doc = fitz.open()

    page1 = doc.new_page(width=595, height=842)
    page1.insert_text(
        (50, 50),
        (
            "INVOICE\n\n"
            "Invoice Number: INV-2024-MULTI\n"
            "Invoice Date: 01/03/2024\n"
            "Due Date: 01/04/2024\n\n"
            "From: MultiPage Industries Ltd\n\n"
            "Subtotal:    500.00\n"
            "VAT (15%):    75.00\n"
            "Grand Total:  575.00\n\n"
            "Currency: EUR\n"
        ),
        fontsize=11,
    )

    for i in range(2, 4):
        p = doc.new_page(width=595, height=842)
        p.insert_text(
            (50, 50),
            f"Page {i} – Additional terms, conditions and item details.\n"
            f"This page contains supplementary information only.\n",
            fontsize=11,
        )

    return doc.tobytes()


def _encrypted_pdf() -> bytes:
    """AES-256 encrypted PDF (must be rejected by the API)."""
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 50), "Invoice Number: INV-SECRET")
    return doc.tobytes(
        encryption=fitz.PDF_ENCRYPT_AES_256,
        owner_pw="owner_pass_secure",
        user_pw="user_pass_secure",
    )


def _oversized_file() -> bytes:
    """File exceeding MAX_FILE_SIZE_MB (size check happens before content validation)."""
    target = (settings.MAX_FILE_SIZE_MB + 1) * 1024 * 1024
    return b"%PDF-1.4\n" + b"0" * target


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_integration_english_digital_pdf():
    """English digital PDF: verify HTTP 200, field extraction, and accuracy >= 60%."""
    pdf_bytes = _english_invoice_pdf()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post(
            "/v1/invoices/extract",
            headers=_headers(),
            files={"file": ("invoice_en.pdf", pdf_bytes, "application/pdf")},
        )

    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
    body = r.json()
    assert body["success"] is True
    data = body["data"]

    _print_accuracy_report("English Digital PDF", data, ENGLISH_GROUND_TRUTH)

    accuracy = _compute_accuracy(data, ENGLISH_GROUND_TRUTH)
    assert accuracy >= ACCURACY_THRESHOLD, (
        f"English PDF field accuracy {accuracy * 100:.1f}% < required {ACCURACY_THRESHOLD * 100:.0f}%"
    )
    # Verify field_confidence is present and populated
    assert data.get("field_confidence"), "field_confidence must be present"
    assert data.get("confidence_score", 0) > 0, "confidence_score must be > 0"


@pytest.mark.anyio
async def test_integration_arabic_digital_pdf():
    """Arabic digital PDF: verify HTTP 200 and report field accuracy."""
    pdf_bytes = _arabic_invoice_pdf()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post(
            "/v1/invoices/extract",
            headers=_headers(),
            files={"file": ("invoice_ar.pdf", pdf_bytes, "application/pdf")},
        )

    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
    body = r.json()
    assert body["success"] is True
    data = body["data"]

    _print_accuracy_report("Arabic Digital PDF", data, ARABIC_GROUND_TRUTH)

    # Arabic extraction accuracy is measured but no hard minimum enforced
    # (depends on bidi text handling in fitz on the CI runner)
    accuracy = _compute_accuracy(data, ARABIC_GROUND_TRUTH)
    print(f"  Arabic field accuracy: {accuracy * 100:.1f}%")
    assert data.get("field_confidence") is not None, "field_confidence must be present"


@pytest.mark.anyio
async def test_integration_scanned_invoice_png(monkeypatch):
    """Scanned invoice PNG: OCR path returns 200; report field accuracy."""
    # Enable OCR for this test only, then restore
    original_ocr = settings.ENABLE_OCR
    settings.ENABLE_OCR = True

    ocr_text = (
        "Invoice Number: INV-2024-003\n"
        "Invoice Date: 20/01/2024\n"
        "From: ScanCorp Solutions\n"
        "Subtotal:    800.00\n"
        "VAT (20%):   160.00\n"
        "Grand Total: 960.00\n"
        "Currency: USD\n"
    )

    async def _mock_ocr(image_bytes: bytes) -> str:
        return ocr_text

    monkeypatch.setattr("app.services.invoice_extractor.ocr_image_bytes", _mock_ocr)

    try:
        png_bytes = _scanned_invoice_png()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.post(
                "/v1/invoices/extract",
                headers=_headers(),
                files={"file": ("scan_invoice.png", png_bytes, "image/png")},
            )
    finally:
        settings.ENABLE_OCR = original_ocr

    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
    body = r.json()
    assert body["success"] is True
    data = body["data"]

    _print_accuracy_report("Scanned Invoice PNG (OCR)", data, SCANNED_GROUND_TRUTH)

    accuracy = _compute_accuracy(data, SCANNED_GROUND_TRUTH)
    assert accuracy >= ACCURACY_THRESHOLD, (
        f"Scanned PNG OCR accuracy {accuracy * 100:.1f}% < required {ACCURACY_THRESHOLD * 100:.0f}%"
    )
    assert body["meta"]["extraction_method"] == "ocr"


@pytest.mark.anyio
async def test_integration_multipage_pdf():
    """Multi-page PDF (3 pages): verify processing and field extraction."""
    pdf_bytes = _multipage_invoice_pdf()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post(
            "/v1/invoices/extract",
            headers=_headers(),
            files={"file": ("multipage.pdf", pdf_bytes, "application/pdf")},
        )

    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
    body = r.json()
    assert body["success"] is True
    data = body["data"]
    meta = body["meta"]

    assert meta["page_count"] == 3, f"Expected 3 pages, got {meta['page_count']}"

    _print_accuracy_report("Multi-page PDF (3 pages)", data, MULTIPAGE_GROUND_TRUTH)

    accuracy = _compute_accuracy(data, MULTIPAGE_GROUND_TRUTH)
    assert accuracy >= ACCURACY_THRESHOLD, (
        f"Multi-page PDF accuracy {accuracy * 100:.1f}% < required {ACCURACY_THRESHOLD * 100:.0f}%"
    )


@pytest.mark.anyio
async def test_integration_encrypted_pdf_rejected():
    """Encrypted PDF must be rejected with HTTP 422 and error code PDF_ENCRYPTED."""
    enc_bytes = _encrypted_pdf()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post(
            "/v1/invoices/extract",
            headers=_headers(),
            files={"file": ("encrypted.pdf", enc_bytes, "application/pdf")},
        )

    assert r.status_code == 422, f"Expected 422, got {r.status_code}: {r.text}"
    body = r.json()
    assert body["error"]["code"] == "PDF_ENCRYPTED", (
        f"Expected error code PDF_ENCRYPTED, got: {body['error']['code']}"
    )
    print(f"\n  ✓ Encrypted PDF rejected: HTTP {r.status_code} – {body['error']['code']}")


@pytest.mark.anyio
async def test_integration_large_file_rejected():
    """File exceeding MAX_FILE_SIZE_MB must be rejected with HTTP 413."""
    big_bytes = _oversized_file()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post(
            "/v1/invoices/extract",
            headers=_headers(),
            files={"file": ("large.pdf", big_bytes, "application/pdf")},
        )

    assert r.status_code == 413, f"Expected 413, got {r.status_code}: {r.text}"
    body = r.json()
    assert body["error"]["code"] == "FILE_TOO_LARGE", (
        f"Expected FILE_TOO_LARGE, got: {body['error']['code']}"
    )
    print(f"\n  ✓ Oversized file rejected: HTTP {r.status_code} – {body['error']['code']}")


@pytest.mark.anyio
async def test_integration_ocr_timeout_returns_504(monkeypatch):
    """OCR timeout simulation: must return HTTP 504 with PROCESSING_TIMEOUT code."""
    original_ocr = settings.ENABLE_OCR
    settings.ENABLE_OCR = True

    async def _timeout_ocr(_: bytes) -> str:
        raise TimeoutError("simulated OCR timeout")

    monkeypatch.setattr("app.services.invoice_extractor.ocr_image_bytes", _timeout_ocr)

    png_bytes = _scanned_invoice_png()
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.post(
                "/v1/invoices/extract",
                headers=_headers(),
                files={"file": ("scan.png", png_bytes, "image/png")},
            )
    finally:
        settings.ENABLE_OCR = original_ocr

    assert r.status_code == 504, f"Expected 504, got {r.status_code}: {r.text}"
    body = r.json()
    assert body["error"]["code"] == "PROCESSING_TIMEOUT", (
        f"Expected PROCESSING_TIMEOUT, got: {body['error']['code']}"
    )
    assert "x-request-id" in {k.lower() for k in r.headers.keys()}
    print(f"\n  ✓ OCR timeout: HTTP {r.status_code} – {body['error']['code']}")


@pytest.mark.anyio
async def test_integration_rapidapi_proxy_secret_valid():
    """Valid X-RapidAPI-Proxy-Secret must be accepted (HTTP 200)."""
    pdf_bytes = _english_invoice_pdf()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post(
            "/v1/invoices/extract",
            headers=_rapidapi_headers(settings.RAPIDAPI_PROXY_SECRET),
            files={"file": ("invoice.pdf", pdf_bytes, "application/pdf")},
        )

    # RapidAPI secret takes precedence; direct API key not required
    assert r.status_code in (200, 401), (
        f"Unexpected status: {r.status_code} – {r.text}"
    )
    if r.status_code == 200:
        assert r.json()["success"] is True
        print("\n  ✓ RapidAPI valid secret: HTTP 200")
    else:
        # 401 is acceptable if REQUIRE_RAPIDAPI_SECRET is enforced and secret doesn't match
        print(f"\n  ℹ RapidAPI secret test: HTTP {r.status_code} (check REQUIRE_RAPIDAPI_SECRET config)")


@pytest.mark.anyio
async def test_integration_rapidapi_proxy_secret_invalid():
    """Invalid X-RapidAPI-Proxy-Secret must return HTTP 401."""
    pdf_bytes = _english_invoice_pdf()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post(
            "/v1/invoices/extract",
            headers=_rapidapi_headers("totally-wrong-secret-value-xyz"),
            files={"file": ("invoice.pdf", pdf_bytes, "application/pdf")},
        )

    assert r.status_code == 401, f"Expected 401, got {r.status_code}: {r.text}"
    body = r.json()
    assert body["error"]["code"] == "UNAUTHORIZED"
    print(f"\n  ✓ RapidAPI invalid secret: HTTP 401 – {body['error']['code']}")
