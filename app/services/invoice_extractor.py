from __future__ import annotations

import asyncio
import time

from app.config import settings
from app.services.ocr_service import ocr_image_bytes, ocr_pil_images
from app.services.parser import parse_invoice
from app.services.pdf_extractor import extract_text_from_pdf, pdf_pages_as_images

_MIN_TEXT_CHARS = 50


def _empty_parsed() -> dict:
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
        "field_confidence": {},
        "raw_text": "",
    }


def _truncate_text(text: str) -> str:
    if len(text) > settings.MAX_EXTRACTED_TEXT_LENGTH:
        return text[: settings.MAX_EXTRACTED_TEXT_LENGTH]
    return text


async def extract_from_pdf(pdf_bytes: bytes) -> dict:
    start = time.monotonic()
    extraction_method = "pdf_text"
    error_msg = None

    text, needs_ocr = await asyncio.to_thread(extract_text_from_pdf, pdf_bytes)

    if needs_ocr or len(text.strip()) < _MIN_TEXT_CHARS:
        if settings.ENABLE_OCR:
            extraction_method = "ocr"
            try:
                images = await asyncio.to_thread(pdf_pages_as_images, pdf_bytes)
                if images:
                    text = await ocr_pil_images(images)
                if not text.strip():
                    extraction_method = "fallback"
                    error_msg = "OCR produced no text from PDF pages."
            except TimeoutError:
                extraction_method = "fallback"
                error_msg = "OCR timed out."
            except Exception:
                extraction_method = "fallback"
                error_msg = "OCR processing failed."
        elif not text.strip():
            extraction_method = "fallback"
            error_msg = "PDF appears scanned and OCR is disabled."

    text = _truncate_text(text)
    elapsed_ms = int((time.monotonic() - start) * 1000)

    try:
        parsed = parse_invoice(text) if text.strip() else _empty_parsed()
    except Exception:
        parsed = _empty_parsed()

    return {
        "extraction_method": extraction_method,
        "parsed": parsed,
        "processing_time_ms": elapsed_ms,
        "error": error_msg,
    }


async def extract_from_image(image_bytes: bytes) -> dict:
    start = time.monotonic()
    extraction_method = "ocr"
    error_msg = None
    text = ""

    try:
        text = await ocr_image_bytes(image_bytes)
    except TimeoutError:
        extraction_method = "fallback"
        error_msg = "OCR timed out."
    except Exception:
        extraction_method = "fallback"
        error_msg = "OCR processing failed."

    text = _truncate_text(text)
    elapsed_ms = int((time.monotonic() - start) * 1000)

    try:
        parsed = parse_invoice(text) if text.strip() else _empty_parsed()
    except Exception:
        parsed = _empty_parsed()

    return {
        "extraction_method": extraction_method,
        "parsed": parsed,
        "processing_time_ms": elapsed_ms,
        "error": error_msg,
    }
