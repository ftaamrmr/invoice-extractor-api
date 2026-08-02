from pathlib import Path

from app.services.parser import parse_invoice

BASE = Path(__file__).resolve().parent.parent / "sample_files"


def test_parser_en_sample():
    text = (BASE / "sample_invoice_en.txt").read_text(encoding="utf-8")
    data = parse_invoice(text)
    assert data["invoice_number"] or data["total_amount"] is not None


def test_parser_ar_sample():
    text = (BASE / "sample_invoice_ar.txt").read_text(encoding="utf-8")
    data = parse_invoice(text)
    assert data["currency"] or data["total_amount"] is not None


def test_parser_fr_it_hi_samples():
    for name in ["sample_invoice_fr.txt", "sample_invoice_it.txt", "sample_invoice_hi.txt"]:
        text = (BASE / name).read_text(encoding="utf-8")
        data = parse_invoice(text)
        assert isinstance(data["confidence_score"], float)
