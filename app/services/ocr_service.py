"""
OCR service: high-level wrapper that respects the ENABLE_OCR setting.

All callers should go through this module rather than importing
image_extractor directly so the ENABLE_OCR guard is always applied.
"""
from typing import List
from app.config import settings
from app.services.image_extractor import (
    extract_text_from_image_bytes,
    extract_text_from_pil_image,
)


def ocr_image_bytes(image_bytes: bytes) -> str:
    """
    Run OCR on raw image bytes.
    Raises RuntimeError if OCR is disabled or the OCR engine is unavailable.
    """
    if not settings.ENABLE_OCR:
        raise RuntimeError(
            "OCR is disabled. Set ENABLE_OCR=true in your .env to enable it."
        )
    return extract_text_from_image_bytes(image_bytes)


def ocr_pil_images(images: list) -> str:
    """
    Run OCR on a list of PIL Image objects (e.g. rendered PDF pages) and
    concatenate results with newline separators.
    Raises RuntimeError if OCR is disabled or the OCR engine is unavailable.
    """
    if not settings.ENABLE_OCR:
        raise RuntimeError(
            "OCR is disabled. Set ENABLE_OCR=true in your .env to enable it."
        )
    parts: List[str] = []
    for img in images:
        page_text = extract_text_from_pil_image(img)
        if page_text:
            parts.append(page_text)
    return "\n\n".join(parts).strip()
