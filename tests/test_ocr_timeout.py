"""Tests for OCR timeout behaviour in image_extractor."""
from __future__ import annotations

from unittest.mock import patch

import pytest

from app.errors import OCRTimeoutError
from app.services.image_extractor import _ocr_image


def _fake_pil_image():
    from PIL import Image

    return Image.new("RGB", (10, 10), color="white")


def test_pytesseract_timeout_raises_ocr_timeout_error():
    """A Tesseract timeout on the primary language raises OCRTimeoutError."""
    import pytesseract

    timeout_exc = pytesseract.TesseractError(1, "Error, timed out")

    with patch("pytesseract.image_to_string", side_effect=timeout_exc), pytest.raises(OCRTimeoutError):
        _ocr_image(_fake_pil_image())


def test_pytesseract_fallback_eng_timeout_raises_ocr_timeout_error():
    """A Tesseract timeout on the eng fallback also raises OCRTimeoutError."""
    import pytesseract

    lang_exc = pytesseract.TesseractError(1, "Failed loading language")
    timeout_exc = pytesseract.TesseractError(1, "Error, timed out")

    def side_effect(image, lang=None, timeout=None):
        if lang and lang != "eng":
            raise lang_exc
        raise timeout_exc

    with patch("pytesseract.image_to_string", side_effect=side_effect), pytest.raises(OCRTimeoutError):
        _ocr_image(_fake_pil_image())


def test_pytesseract_non_timeout_error_raises_runtime_error():
    """A non-timeout Tesseract error after lang fallback raises RuntimeError."""
    import pytesseract

    lang_exc = pytesseract.TesseractError(1, "Failed loading language")
    binary_exc = pytesseract.TesseractError(1, "Tesseract not found")

    def side_effect(image, lang=None, timeout=None):
        if lang and lang != "eng":
            raise lang_exc
        raise binary_exc

    with patch("pytesseract.image_to_string", side_effect=side_effect), pytest.raises(RuntimeError, match="Tesseract OCR failed"):
        _ocr_image(_fake_pil_image())


def test_pytesseract_timeout_param_passed():
    """Confirm that timeout= is forwarded to pytesseract.image_to_string."""
    from app.config import settings

    captured: list = []

    def capturing_call(image, lang=None, timeout=None):
        captured.append(timeout)
        return "sample text"

    with patch("pytesseract.image_to_string", side_effect=capturing_call):
        result = _ocr_image(_fake_pil_image())

    assert result == "sample text"
    assert captured[0] == settings.OCR_TIMEOUT_SECONDS


@pytest.mark.anyio
async def test_ocr_service_timeout_propagates_as_timeout_error():
    """OCRTimeoutError raised in the thread propagates as TimeoutError from ocr_image_bytes."""
    from app.errors import OCRTimeoutError
    from app.services import ocr_service

    original_enable = ocr_service.settings.ENABLE_OCR
    ocr_service.settings.ENABLE_OCR = True

    def raise_ocr_timeout(image_bytes):
        raise OCRTimeoutError("timed out")

    with patch("app.services.ocr_service.extract_text_from_image_bytes", side_effect=raise_ocr_timeout), pytest.raises(TimeoutError):
        await ocr_service.ocr_image_bytes(b"fake")

    ocr_service.settings.ENABLE_OCR = original_enable
