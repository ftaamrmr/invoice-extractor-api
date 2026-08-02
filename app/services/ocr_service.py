from __future__ import annotations

import asyncio
import subprocess
from collections.abc import Iterable

from app.config import settings
from app.services.image_extractor import (
    extract_text_from_image_bytes,
    extract_text_from_pil_image,
)

_ocr_semaphore = asyncio.Semaphore(settings.MAX_CONCURRENT_OCR_JOBS)


def _ocr_many(images: Iterable) -> str:
    parts: list[str] = []
    for img in images:
        text = extract_text_from_pil_image(img)
        if text:
            parts.append(text)
    return "\n\n".join(parts).strip()


async def ocr_image_bytes(image_bytes: bytes) -> str:
    if not settings.ENABLE_OCR:
        raise RuntimeError("OCR is disabled.")
    async with _ocr_semaphore:
        return await asyncio.wait_for(
            asyncio.to_thread(extract_text_from_image_bytes, image_bytes),
            timeout=settings.OCR_TIMEOUT_SECONDS,
        )


async def ocr_pil_images(images: list) -> str:
    if not settings.ENABLE_OCR:
        raise RuntimeError("OCR is disabled.")
    async with _ocr_semaphore:
        return await asyncio.wait_for(
            asyncio.to_thread(_ocr_many, images),
            timeout=settings.OCR_TIMEOUT_SECONDS,
        )


def check_tesseract_ready(required_languages: str) -> tuple[bool, str]:
    try:
        version_run = subprocess.run(
            ["tesseract", "--version"],
            capture_output=True,
            text=True,
            check=False,
            timeout=5,
        )
        if version_run.returncode != 0:
            return False, "tesseract binary not available"

        langs_run = subprocess.run(
            ["tesseract", "--list-langs"],
            capture_output=True,
            text=True,
            check=False,
            timeout=5,
        )
        if langs_run.returncode != 0:
            return False, "tesseract languages check failed"

        available = {line.strip() for line in langs_run.stdout.splitlines() if line.strip() and "languages" not in line.lower()}
        missing = [lang for lang in required_languages.split("+") if lang and lang not in available]
        if missing:
            return False, f"missing tesseract languages: {', '.join(missing)}"
        return True, "ok"
    except Exception:
        return False, "tesseract check failed"
