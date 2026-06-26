"""
Image text extraction via OCR.

Strategy:
  1. Try pytesseract with the configured OCR_LANGUAGES setting.
  2. Fall back to English-only if the language pack is missing.
  3. Try EasyOCR if pytesseract is not installed.
  4. Raise a clear, actionable error if neither engine is available.
"""
import io
from PIL import Image
from app.config import settings


def extract_text_from_image_bytes(image_bytes: bytes) -> str:
    """Run OCR on raw image bytes and return extracted text."""
    image = Image.open(io.BytesIO(image_bytes))
    # Convert to RGB to handle PNG with alpha channel or other modes
    if image.mode not in ("RGB", "L"):
        image = image.convert("RGB")
    return _ocr_image(image)


def extract_text_from_pil_image(image: "Image.Image") -> str:
    """Run OCR on a PIL Image object."""
    if image.mode not in ("RGB", "L"):
        image = image.convert("RGB")
    return _ocr_image(image)


def _ocr_image(image: "Image.Image") -> str:
    """
    Internal: try pytesseract → EasyOCR → raise helpful error.
    Uses OCR_LANGUAGES from settings (default: eng+ara).
    """
    lang = settings.OCR_LANGUAGES  # e.g. "eng+ara" or "eng"

    # ── pytesseract ───────────────────────────────────────────────────────────
    try:
        import pytesseract

        try:
            # Try with the configured language set (may include Arabic)
            text = pytesseract.image_to_string(image, lang=lang)
        except pytesseract.TesseractError:
            # Language pack not installed → fall back to English only
            try:
                text = pytesseract.image_to_string(image, lang="eng")
            except pytesseract.TesseractError as exc:
                raise RuntimeError(
                    f"Tesseract OCR failed: {exc}. "
                    "Make sure the Tesseract binary is installed and accessible."
                ) from exc
        return text.strip()

    except ImportError:
        pass  # pytesseract Python package not installed

    # ── EasyOCR fallback ──────────────────────────────────────────────────────
    try:
        import easyocr
        import numpy as np

        # Map tesseract lang string → EasyOCR lang list
        lang_list = _tesseract_lang_to_easyocr(lang)
        reader = easyocr.Reader(lang_list, gpu=False, verbose=False)
        img_array = np.array(image)
        results = reader.readtext(img_array, detail=0)
        return "\n".join(str(r) for r in results).strip()

    except ImportError:
        pass  # EasyOCR not installed

    # ── Nothing available ─────────────────────────────────────────────────────
    raise RuntimeError(
        "No OCR engine is available. "
        "Install pytesseract (+ Tesseract binary) or easyocr. "
        "See README.md for setup instructions. "
        "You can also set ENABLE_OCR=false to disable OCR for text-based PDFs only."
    )


def _tesseract_lang_to_easyocr(lang: str) -> list:
    """Convert tesseract lang string 'eng+ara' → EasyOCR list ['en', 'ar']."""
    mapping = {"eng": "en", "ara": "ar", "fra": "fr", "deu": "de", "spa": "es"}
    parts = lang.lower().split("+")
    return [mapping.get(p, p) for p in parts if p]
