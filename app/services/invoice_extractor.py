"""
High-level invoice extraction orchestrator.

Flow for PDF:
  1. Extract native (embedded) text via PyMuPDF.
  2. If text is too short AND OCR is enabled → render pages to images → OCR.
  3. Parse the resulting text with the rule-based parser.

Flow for image:
  1. Run OCR (if enabled).
  2. Parse the resulting text.

Return shape (always a dict, never raises):
  {
      "extraction_method": "pdf_text" | "ocr" | "fallback",
      "parsed": { ...InvoiceData fields... },
      "processing_time_ms": int,
      "error": str | None        # None on success
  }
"""
import time
import logging
from app.config import settings
from app.services.pdf_extractor import extract_text_from_pdf, pdf_pages_as_images
from app.services.ocr_service import ocr_image_bytes, ocr_pil_images
from app.services.parser import parse_invoice

logger = logging.getLogger(__name__)

# Minimum characters to consider PDF text extraction usable
_MIN_TEXT_CHARS = 50


def _empty_parsed() -> dict:
    """Return a zeroed InvoiceData-compatible dict."""
    return {
        "vendor_name": None,
        "vendor_tax_number": None,
        "invoice_number": None,
        "invoice_date": None,
        "due_date": None,
        "currency": None,
        "subtotal": None,
        "tax_amount": None,
        "total_amount": None,
        "payment_method": None,
        "line_items": [],
        "confidence_score": 0.0,
        "raw_text": "",
    }


def extract_from_pdf(pdf_bytes: bytes) -> dict:
    """
    Extract and parse invoice data from a PDF file.
    Always returns a dict; never raises.
    """
    start = time.monotonic()
    extraction_method = "pdf_text"
    error_msg = None

    # Step 1: native text extraction
    try:
        text, needs_ocr = extract_text_from_pdf(pdf_bytes)
    except Exception as exc:
        logger.warning("PDF native extraction failed: %s", exc)
        text, needs_ocr = "", True

    # Step 2: OCR fallback for scanned / image-only PDFs
    if needs_ocr or len(text.strip()) < _MIN_TEXT_CHARS:
        if settings.ENABLE_OCR:
            extraction_method = "ocr"
            try:
                images = pdf_pages_as_images(pdf_bytes)
                if images:
                    text = ocr_pil_images(images)
                    if not text.strip():
                        extraction_method = "fallback"
                        error_msg = "OCR produced no text from PDF pages."
                else:
                    extraction_method = "fallback"
                    error_msg = "Could not render PDF pages for OCR."
            except RuntimeError as exc:
                extraction_method = "fallback"
                error_msg = str(exc)
            except Exception as exc:
                logger.warning("OCR fallback failed: %s", exc)
                extraction_method = "fallback"
                error_msg = "OCR processing failed unexpectedly."
        else:
            # OCR disabled and text too short
            if not text.strip():
                extraction_method = "fallback"
                error_msg = (
                    "PDF appears to be scanned/image-based and OCR is disabled. "
                    "Set ENABLE_OCR=true to process scanned invoices."
                )

    elapsed_ms = int((time.monotonic() - start) * 1000)

    try:
        parsed = parse_invoice(text) if text.strip() else _empty_parsed()
    except Exception as exc:
        logger.warning("Parser failed: %s", exc)
        parsed = _empty_parsed()

    return {
        "extraction_method": extraction_method,
        "parsed": parsed,
        "processing_time_ms": elapsed_ms,
        "error": error_msg,
    }


def extract_from_image(image_bytes: bytes) -> dict:
    """
    Extract and parse invoice data from an image file.
    Always returns a dict; never raises.
    """
    start = time.monotonic()
    extraction_method = "ocr"
    error_msg = None
    text = ""

    try:
        text = ocr_image_bytes(image_bytes)
    except RuntimeError as exc:
        extraction_method = "fallback"
        error_msg = str(exc)
    except Exception as exc:
        logger.warning("Image OCR failed: %s", exc)
        extraction_method = "fallback"
        error_msg = "OCR processing failed unexpectedly."

    elapsed_ms = int((time.monotonic() - start) * 1000)

    try:
        parsed = parse_invoice(text) if text.strip() else _empty_parsed()
    except Exception as exc:
        logger.warning("Parser failed: %s", exc)
        parsed = _empty_parsed()

    return {
        "extraction_method": extraction_method,
        "parsed": parsed,
        "processing_time_ms": elapsed_ms,
        "error": error_msg,
    }
