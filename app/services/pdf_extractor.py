"""
PDF text extraction using PyMuPDF (fitz).

Strategy:
  1. Try to extract native (embedded) text directly – fast and accurate.
  2. If the result is too sparse (< MIN_CHARS), signal that OCR is needed.
"""
from typing import Tuple, List

MIN_CHARS = 50  # below this we consider the PDF image-only / scanned


def extract_text_from_pdf(pdf_bytes: bytes) -> Tuple[str, bool]:
    """
    Extract text from a PDF.

    Returns:
        (text, needs_ocr)
        - text      : extracted text (may be empty / short)
        - needs_ocr : True when text is too short and OCR should be tried
    """
    try:
        import fitz  # PyMuPDF

        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        pages_text: List[str] = []

        for page in doc:
            pages_text.append(page.get_text())

        doc.close()
        full_text = "\n".join(pages_text).strip()

        needs_ocr = len(full_text) < MIN_CHARS
        return full_text, needs_ocr

    except ImportError:
        # PyMuPDF not installed – signal OCR needed
        return "", True
    except Exception as exc:
        # Corrupt or unreadable PDF
        return "", True


def pdf_pages_as_images(pdf_bytes: bytes) -> list:
    """
    Convert each PDF page to a PIL Image for OCR processing.
    Returns a list of PIL Image objects.
    """
    try:
        import fitz
        from PIL import Image

        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        images: list = []

        for page in doc:
            # Render at 2x zoom for better OCR accuracy
            mat = fitz.Matrix(2.0, 2.0)
            pix = page.get_pixmap(matrix=mat)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            images.append(img)

        doc.close()
        return images

    except Exception:
        return []
