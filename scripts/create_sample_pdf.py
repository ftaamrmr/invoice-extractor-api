#!/usr/bin/env python3
"""
scripts/create_sample_pdf.py

Converts the sample invoice text files into PDF files for API testing.

Usage:
    python scripts/create_sample_pdf.py

Output:
    sample_files/sample_invoice_en.pdf   — English invoice PDF (always created)
    sample_files/sample_invoice_fr.pdf   — French invoice PDF (always created)
    sample_files/sample_invoice_it.pdf   — Italian invoice PDF (always created)
    sample_files/sample_invoice_hi.pdf   — Hindi invoice PDF (always created)
    sample_files/sample_invoice_ar.pdf   — Arabic invoice PDF (created if Arabic
                                           font support is available; see notes below)

Requirements:
    pip install reportlab

Arabic PDF notes:
    ReportLab does not include Arabic fonts by default, and Arabic text in PDFs
    requires a Unicode-capable font AND right-to-left (BiDi) shaping.
    This script attempts to use the "Amiri" font if it is available at:
        scripts/fonts/Amiri-Regular.ttf
    Download it free from: https://fonts.google.com/specimen/Amiri
    If the font is not found, the Arabic PDF is skipped and a clear message is shown.
    The English PDF is always created and is sufficient for testing the API.

    For most testing purposes the English PDF is enough. Arabic parsing can be
    tested without a PDF using the parser directly (see sample_files/README.md).
"""

import os
import sys

# ── Paths ─────────────────────────────────────────────────────────────────────

SCRIPT_DIR   = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
SAMPLE_DIR   = os.path.join(PROJECT_ROOT, "sample_files")
FONTS_DIR    = os.path.join(SCRIPT_DIR, "fonts")

ARABIC_FONT_PATH = os.path.join(FONTS_DIR, "Amiri-Regular.ttf")

# ── Check reportlab ───────────────────────────────────────────────────────────

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_LEFT, TA_RIGHT
    from reportlab.platypus import SimpleDocTemplate, Paragraph, HRFlowable, Preformatted
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
except ImportError:
    print("\n[ERROR] reportlab is not installed.")
    print("Run:  pip install reportlab\n")
    sys.exit(1)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _register_arabic_font() -> bool:
    """
    Try to register the Amiri Arabic font with ReportLab.
    Returns True if successful, False otherwise.
    """
    if not os.path.isfile(ARABIC_FONT_PATH):
        return False
    try:
        pdfmetrics.registerFont(TTFont("Amiri", ARABIC_FONT_PATH))
        return True
    except Exception as exc:
        print(f"  [WARN] Could not register Arabic font: {exc}")
        return False


def _bidi_reshape(text: str) -> str:
    """
    Apply Unicode BiDi algorithm and Arabic letter shaping.
    Requires 'python-bidi' and 'arabic-reshaper' packages.
    Falls back to raw text if those packages are not installed.
    """
    try:
        import arabic_reshaper
        from bidi.algorithm import get_display
        reshaped = arabic_reshaper.reshape(text)
        return get_display(reshaped)
    except ImportError:
        return text  # render without shaping (will look reversed, but won't crash)


def create_simple_pdf(txt_path: str, pdf_path: str, title: str) -> None:
    """Create a clean, left-to-right invoice PDF from a .txt file."""
    print(f"  Creating: {os.path.basename(pdf_path)}")

    with open(txt_path, encoding="utf-8") as fh:
        raw_text = fh.read()

    doc = SimpleDocTemplate(
        pdf_path,
        pagesize=A4,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
        topMargin=20 * mm,
        bottomMargin=20 * mm,
    )

    styles = getSampleStyleSheet()

    mono = ParagraphStyle(
        "Mono",
        parent=styles["Normal"],
        fontName="Courier",
        fontSize=9,
        leading=13,
        alignment=TA_LEFT,
    )
    title_style = ParagraphStyle(
        "InvTitle",
        parent=styles["Heading1"],
        fontSize=14,
        spaceAfter=8,
        alignment=TA_LEFT,
    )

    story = []
    story.append(Paragraph(title, title_style))
    story.append(HRFlowable(width="100%", thickness=1, spaceAfter=8))

    # Use Preformatted so each line from the .txt keeps its exact structure
    # (important for parser testing: totals, VAT, etc. stay aligned).
    story.append(Preformatted(raw_text, mono))

    doc.build(story)
    print(f"  [OK] Saved: {pdf_path}")


def create_arabic_pdf(txt_path: str, pdf_path: str, font_available: bool) -> None:
    """
    Create an Arabic invoice PDF from a .txt file.
    Requires the Amiri font in scripts/fonts/Amiri-Regular.ttf.
    """
    if not font_available:
        print(f"\n  [SKIP] Arabic PDF not created — Amiri font not found.")
        print(f"  To enable Arabic PDF generation:")
        print(f"    1. Download Amiri-Regular.ttf from https://fonts.google.com/specimen/Amiri")
        print(f"    2. Place it at: {ARABIC_FONT_PATH}")
        print(f"    3. Run: pip install arabic-reshaper python-bidi")
        print(f"    4. Re-run this script.")
        print(f"\n  You can still test Arabic parsing with the .txt file directly.")
        return

    print(f"  Creating: {os.path.basename(pdf_path)}")

    with open(txt_path, encoding="utf-8") as fh:
        raw_text = fh.read()

    doc = SimpleDocTemplate(
        pdf_path,
        pagesize=A4,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
        topMargin=20 * mm,
        bottomMargin=20 * mm,
    )

    ar_style = ParagraphStyle(
        "Arabic",
        fontName="Amiri",
        fontSize=10,
        leading=16,
        alignment=TA_RIGHT,
        wordWrap="RTL",
    )
    title_style = ParagraphStyle(
        "ArTitle",
        fontName="Amiri",
        fontSize=14,
        spaceAfter=8,
        alignment=TA_RIGHT,
    )

    story = []
    story.append(Paragraph(_bidi_reshape("فاتورة ضريبية — نموذج اختبار"), title_style))
    story.append(HRFlowable(width="100%", thickness=1, spaceAfter=8))

    for line in raw_text.splitlines():
        safe = line.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        shaped = _bidi_reshape(safe) if safe.strip() else "&nbsp;"
        story.append(Paragraph(shaped, ar_style))

    doc.build(story)
    print(f"  [OK] Saved: {pdf_path}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print("\nInvoice Extractor API — Sample PDF Generator")
    print("=" * 50)

    os.makedirs(SAMPLE_DIR, exist_ok=True)
    os.makedirs(FONTS_DIR, exist_ok=True)

    # Source .txt files to generate (lang_code, filename, pdf_title)
    samples = [
        ("en", "sample_invoice_en.txt", "Invoice Extractor API — English Sample Invoice"),
        ("fr", "sample_invoice_fr.txt", "Invoice Extractor API — French Sample Invoice"),
        ("it", "sample_invoice_it.txt", "Invoice Extractor API — Italian Sample Invoice"),
        ("hi", "sample_invoice_hi.txt", "Invoice Extractor API — Hindi Sample Invoice"),
    ]

    # Check source .txt files exist
    for lang, fname, _ in samples:
        path = os.path.join(SAMPLE_DIR, fname)
        if not os.path.isfile(path):
            print(f"\n[ERROR] Source file not found: {path}")
            print("Make sure you are running from the project root directory.")
            sys.exit(1)

    # Generate left-to-right PDFs
    for lang, fname, title in samples:
        txt_path = os.path.join(SAMPLE_DIR, fname)
        pdf_path = os.path.join(SAMPLE_DIR, fname.replace(".txt", ".pdf"))
        create_simple_pdf(txt_path, pdf_path, title)

    # Generate Arabic PDF (optional, requires Amiri font)
    ar_txt = os.path.join(SAMPLE_DIR, "sample_invoice_ar.txt")
    ar_pdf = os.path.join(SAMPLE_DIR, "sample_invoice_ar.pdf")
    if os.path.isfile(ar_txt):
        print("\n  Generating Arabic PDF...")
        arabic_font_ok = _register_arabic_font()
        create_arabic_pdf(ar_txt, ar_pdf, arabic_font_ok)
    else:
        print(f"\n  [SKIP] Arabic source not found: {ar_txt}")

    print("\n" + "=" * 50)
    print("Done. Files in sample_files/:")
    for fname in sorted(os.listdir(SAMPLE_DIR)):
        if fname.endswith(".pdf"):
            fpath = os.path.join(SAMPLE_DIR, fname)
            size_kb = os.path.getsize(fpath) / 1024
            print(f"  {fname:<35}  {size_kb:.1f} KB")

    print("\nNext step — run the manual test suite:")
    print("  python manual_test.py\n")


if __name__ == "__main__":
    main()
