from __future__ import annotations

MIN_CHARS = 50
RENDER_DPI = 150


def extract_text_from_pdf(pdf_bytes: bytes) -> tuple[str, bool]:
    try:
        import fitz

        with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
            pages_text: list[str] = [page.get_text() for page in doc]
            full_text = "\n".join(pages_text).strip()
            needs_ocr = len(full_text) < MIN_CHARS
            return full_text, needs_ocr
    except Exception:
        return "", True


def pdf_pages_as_images(pdf_bytes: bytes) -> list:
    try:
        import fitz
        from PIL import Image

        images: list = []
        with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
            zoom = RENDER_DPI / 72
            mat = fitz.Matrix(zoom, zoom)
            for page in doc:
                pix = page.get_pixmap(matrix=mat, alpha=False)
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                images.append(img)
        return images
    except Exception:
        return []
