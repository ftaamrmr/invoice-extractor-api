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
    """Run Tesseract OCR with the configured language set."""
    lang = settings.OCR_LANGUAGES  # e.g. "eng+ara" or "eng"

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
        raise RuntimeError(
            "pytesseract is not installed. Install pytesseract and the Tesseract binary, "
            "or set ENABLE_OCR=false to disable OCR for text-based PDFs only."
        ) from None
