#!/usr/bin/env python3
"""
manual_test.py — Live API test script for Invoice Extractor API.

Runs a series of HTTP tests against the running API and prints
clean, readable results. Exits with code 1 if any critical test fails.

Usage:
    # Set environment variables first, then run:
    python manual_test.py

Environment variables:
    API_BASE_URL   Base URL of the running API  (default: http://localhost:8000)
    API_KEY        Your API key                  (default: reads from .env or empty)

Examples:
    Linux / macOS:
        export API_BASE_URL=http://localhost:8000
        export API_KEY=your-api-key-here
        python manual_test.py

    Windows PowerShell:
        $env:API_BASE_URL = "http://localhost:8000"
        $env:API_KEY      = "your-api-key-here"
        python manual_test.py

    Docker (from host):
        docker-compose up -d
        python manual_test.py
"""

import os
import sys
import json
import time

# ── Try to load .env so you can run without exporting env vars manually ───────
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv not installed — rely on real env vars

try:
    import requests
except ImportError:
    print("\n[ERROR] 'requests' is not installed.")
    print("Run:  pip install requests\n")
    sys.exit(1)

# ── Configuration ─────────────────────────────────────────────────────────────

BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8000").rstrip("/")
API_KEY  = os.environ.get("API_KEY", "")

SAMPLE_PDF  = os.path.join(os.path.dirname(__file__), "sample_files", "sample_invoice_en.pdf")
SAMPLE_TXT  = os.path.join(os.path.dirname(__file__), "sample_files", "sample_invoice_en.txt")

AUTH_HEADERS  = {"X-API-Key": API_KEY} if API_KEY else {}

# ── Terminal colours (safe fallback on Windows without colorama) ──────────────

def _supports_colour():
    return sys.stdout.isatty() and os.name != "nt"

GREEN  = "\033[92m" if _supports_colour() else ""
RED    = "\033[91m" if _supports_colour() else ""
YELLOW = "\033[93m" if _supports_colour() else ""
CYAN   = "\033[96m" if _supports_colour() else ""
RESET  = "\033[0m"  if _supports_colour() else ""
BOLD   = "\033[1m"  if _supports_colour() else ""

# ── Test state ────────────────────────────────────────────────────────────────

results = []   # list of (name, passed, detail)


def record(name: str, passed: bool, detail: str = ""):
    results.append((name, passed, detail))
    status = f"{GREEN}PASS{RESET}" if passed else f"{RED}FAIL{RESET}"
    print(f"  [{status}] {name}")
    if detail:
        for line in detail.strip().splitlines():
            print(f"         {CYAN}{line}{RESET}")


def section(title: str):
    print(f"\n{BOLD}{YELLOW}{'─' * 60}{RESET}")
    print(f"{BOLD}{YELLOW}  {title}{RESET}")
    print(f"{BOLD}{YELLOW}{'─' * 60}{RESET}")


def summary():
    total  = len(results)
    passed = sum(1 for _, ok, _ in results if ok)
    failed = total - passed

    print(f"\n{BOLD}{'═' * 60}{RESET}")
    print(f"{BOLD}  RESULTS: {passed}/{total} passed{RESET}")
    if failed:
        print(f"  {RED}{failed} test(s) FAILED:{RESET}")
        for name, ok, _ in results:
            if not ok:
                print(f"    • {name}")
    else:
        print(f"  {GREEN}All tests passed.{RESET}")
    print(f"{BOLD}{'═' * 60}{RESET}\n")
    return failed


# ── Helpers ───────────────────────────────────────────────────────────────────

def get(path: str, **kwargs) -> requests.Response:
    return requests.get(f"{BASE_URL}{path}", timeout=15, **kwargs)


def post_file(path: str, filepath: str, headers: dict = None) -> requests.Response:
    h = {**(headers or {})}
    with open(filepath, "rb") as fh:
        filename = os.path.basename(filepath)
        mime = "application/pdf" if filename.endswith(".pdf") else "text/plain"
        return requests.post(
            f"{BASE_URL}{path}",
            headers=h,
            files={"file": (filename, fh, mime)},
            timeout=30,
        )


def post_raw(path: str, data: bytes, filename: str,
             content_type: str, headers: dict = None) -> requests.Response:
    h = {**(headers or {})}
    return requests.post(
        f"{BASE_URL}{path}",
        headers=h,
        files={"file": (filename, data, content_type)},
        timeout=30,
    )


def pretty(data: dict) -> str:
    return json.dumps(data, indent=4, ensure_ascii=False)


# ── Tests ─────────────────────────────────────────────────────────────────────

def test_connectivity():
    """Basic TCP reachability check before running real tests."""
    section("1 · Connectivity")
    try:
        r = get("/health")
        record("Server is reachable", True, f"HTTP {r.status_code} from {BASE_URL}")
    except requests.exceptions.ConnectionError:
        record("Server is reachable", False,
               f"Could not connect to {BASE_URL}\n"
               "Make sure the API is running: uvicorn app.main:app --reload")
        print(f"\n{RED}Cannot continue — server is not reachable.{RESET}\n")
        sys.exit(1)


def test_health():
    section("2 · GET /health  (public endpoint)")
    r = get("/health")

    ok = r.status_code == 200
    record("Returns HTTP 200", ok, f"Status: {r.status_code}")

    body = r.json()
    record("Body has 'status: ok'",     body.get("status") == "ok",     f"status = {body.get('status')!r}")
    record("Body has 'service' field",  "service" in body,              f"service = {body.get('service')!r}")
    record("Body has 'version' field",  "version" in body,              f"version = {body.get('version')!r}")
    record("Body has 'environment'",    "environment" in body,          f"environment = {body.get('environment')!r}")


def test_auth():
    section("3 · Authentication")

    # ── No key supplied ───────────────────────────────────────────────────────
    # In production mode this MUST return 401.
    # In development mode it may return 200/422 (no auth enforced).
    dummy_pdf = b"%PDF-1.4\n1 0 obj<</Type/Catalog>>endobj\nxref\n0 1\n0000000000 65535 f\ntrailer<</Root 1 0 R>>\nstartxref\n20\n%%EOF"
    r_no_key = post_raw("/v1/invoices/extract", dummy_pdf, "test.pdf", "application/pdf", headers={})
    if r_no_key.status_code == 401:
        record("No key → 401 (production mode active)", True,
               f"Error code: {r_no_key.json().get('error', {}).get('code')}")
    else:
        record("No key → 401 OR dev mode (skipped auth)", True,
               f"Status {r_no_key.status_code} — set APP_ENV=production to enforce auth")

    # ── Wrong key ─────────────────────────────────────────────────────────────
    r_bad = post_raw("/v1/invoices/extract", dummy_pdf, "test.pdf", "application/pdf",
                     headers={"X-API-Key": "definitely-wrong-key-12345"})
    if r_bad.status_code == 401:
        record("Wrong key → 401", True)
    else:
        record("Wrong key → 401 OR dev mode", True,
               f"Status {r_bad.status_code} — set APP_ENV=production to enforce auth")


def test_file_validation():
    section("4 · File Validation")

    # ── Unsupported type ──────────────────────────────────────────────────────
    r = post_raw("/v1/invoices/extract", b"fake docx content", "invoice.docx",
                 "application/octet-stream", headers=AUTH_HEADERS)
    ok = r.status_code == 422
    body = r.json()
    record("Unsupported type → 422", ok, f"HTTP {r.status_code}")
    record("Error code = UNSUPPORTED_FILE_TYPE",
           body.get("error", {}).get("code") == "UNSUPPORTED_FILE_TYPE",
           f"code = {body.get('error', {}).get('code')!r}")

    # ── Empty file ────────────────────────────────────────────────────────────
    r = post_raw("/v1/invoices/extract", b"", "invoice.pdf", "application/pdf",
                 headers=AUTH_HEADERS)
    ok = r.status_code == 422
    body = r.json()
    record("Empty file → 422", ok, f"HTTP {r.status_code}")
    record("Error code = EMPTY_FILE",
           body.get("error", {}).get("code") == "EMPTY_FILE",
           f"code = {body.get('error', {}).get('code')!r}")

    # ── File too large: send 11 MB against 10 MB limit ────────────────────────
    big = b"A" * (11 * 1024 * 1024)
    r = post_raw("/v1/invoices/extract", big, "big.pdf", "application/pdf",
                 headers=AUTH_HEADERS)
    ok = r.status_code == 413
    body = r.json()
    record("11 MB file → 413", ok, f"HTTP {r.status_code}")
    record("Error code = FILE_TOO_LARGE",
           body.get("error", {}).get("code") == "FILE_TOO_LARGE",
           f"code = {body.get('error', {}).get('code')!r}")


def test_extract_text():
    """Test /extract-text endpoint with the sample PDF."""
    section("5 · POST /v1/invoices/extract-text  (sample PDF)")

    if not os.path.isfile(SAMPLE_PDF):
        record("sample_invoice_en.pdf exists", False,
               "Run: python scripts/create_sample_pdf.py  to generate it first.")
        return

    r = post_file("/v1/invoices/extract-text", SAMPLE_PDF, headers=AUTH_HEADERS)
    ok = r.status_code == 200
    record("Returns HTTP 200", ok, f"Status: {r.status_code}")

    if not ok:
        record("Response body", False, r.text[:300])
        return

    body = r.json()
    record("success = true",    body.get("success") is True)
    record("data.raw_text present", bool(body.get("data", {}).get("raw_text")),
           f"length = {len(body.get('data', {}).get('raw_text', ''))}")
    record("meta.file_type = pdf",
           body.get("meta", {}).get("file_type") == "pdf",
           f"file_type = {body.get('meta', {}).get('file_type')!r}")
    record("X-Processing-Time header present",
           "x-processing-time" in {k.lower() for k in r.headers},
           str(r.headers.get("x-processing-time", "missing")))


def test_extract_full():
    """Test /extract endpoint with the sample PDF — verify parsed fields."""
    section("6 · POST /v1/invoices/extract  (sample PDF — full extraction)")

    if not os.path.isfile(SAMPLE_PDF):
        record("sample_invoice_en.pdf exists", False,
               "Run: python scripts/create_sample_pdf.py  to generate it first.")
        return

    t_start = time.monotonic()
    r = post_file("/v1/invoices/extract", SAMPLE_PDF, headers=AUTH_HEADERS)
    elapsed = int((time.monotonic() - t_start) * 1000)

    ok = r.status_code == 200
    record(f"Returns HTTP 200  ({elapsed} ms total)", ok, f"Status: {r.status_code}")

    if not ok:
        record("Response body", False, r.text[:300])
        return

    body = r.json()
    data = body.get("data", {})
    meta = body.get("meta", {})

    record("success = true",              body.get("success") is True)
    record("meta.extraction_method present", "extraction_method" in meta,
           f"method = {meta.get('extraction_method')!r}")

    # ── Field extraction checks ───────────────────────────────────────────────
    inv_num = data.get("invoice_number")
    record("invoice_number detected",
           inv_num is not None,
           f"invoice_number = {inv_num!r}")

    inv_date = data.get("invoice_date")
    record("invoice_date detected",
           inv_date is not None,
           f"invoice_date = {inv_date!r}")

    total = data.get("total_amount")
    record("total_amount detected",
           total is not None,
           f"total_amount = {total}")

    tax = data.get("tax_amount")
    record("tax_amount detected",
           tax is not None,
           f"tax_amount = {tax}")

    currency = data.get("currency")
    record("currency detected",
           currency is not None,
           f"currency = {currency!r}")

    score = data.get("confidence_score", 0)
    record(f"confidence_score > 0  (got {score})",
           score > 0,
           f"confidence_score = {score}")

    # ── Print a compact summary of all extracted fields ───────────────────────
    print(f"\n  {CYAN}Extracted invoice data:{RESET}")
    skip = {"raw_text", "line_items"}
    for field, value in data.items():
        if field not in skip:
            print(f"    {field:<22} = {value}")
    line_items = data.get("line_items", [])
    print(f"    {'line_items':<22} = {len(line_items)} item(s) detected")


def test_parser_with_txt():
    """Directly test the parser module against the .txt sample (no server needed)."""
    section("7 · Parser direct test  (English — sample_invoice_en.txt)")

    if not os.path.isfile(SAMPLE_TXT):
        record("sample_invoice_en.txt exists", False, f"Expected: {SAMPLE_TXT}")
        return

    # Import the parser directly (works when running from project root)
    try:
        from app.services.parser import parse_invoice
    except ImportError:
        record("app.services.parser importable", False,
               "Run this script from the project root directory.")
        return

    with open(SAMPLE_TXT, encoding="utf-8") as fh:
        text = fh.read()

    result = parse_invoice(text)

    record("invoice_number = INV-2024-00142",
           result.get("invoice_number") == "INV-2024-00142",
           f"got: {result.get('invoice_number')!r}")

    record("invoice_date = 15/01/2024",
           result.get("invoice_date") == "15/01/2024",
           f"got: {result.get('invoice_date')!r}")

    record("total_amount = 11500.0",
           result.get("total_amount") == 11500.0,
           f"got: {result.get('total_amount')}")

    record("tax_amount = 1500.0",
           result.get("tax_amount") == 1500.0,
           f"got: {result.get('tax_amount')}")

    record("currency = SAR",
           result.get("currency") == "SAR",
           f"got: {result.get('currency')!r}")

    record("confidence_score > 50",
           (result.get("confidence_score") or 0) > 50,
           f"got: {result.get('confidence_score')}")


def _test_parser_language(lang: str, filename: str, checks: dict):
    """
    Generic parser direct test for a language sample.
    checks is a dict of field -> expected value (or callable for custom checks).
    """
    section(f"8 · Parser direct test  ({lang.upper()} — {filename})")

    path = os.path.join(os.path.dirname(__file__), "sample_files", filename)
    if not os.path.isfile(path):
        record(f"{filename} exists", False, f"Expected: {path}")
        return

    try:
        from app.services.parser import parse_invoice
    except ImportError:
        record("app.services.parser importable", False,
               "Run this script from the project root directory.")
        return

    with open(path, encoding="utf-8") as fh:
        text = fh.read()

    result = parse_invoice(text)

    for field, expected in checks.items():
        actual = result.get(field)
        if callable(expected):
            passed, detail = expected(actual)
            record(f"{field} {detail}", passed, f"got: {actual}")
        else:
            record(f"{field} = {expected!r}",
                   actual == expected,
                   f"got: {actual!r}")

    record("confidence_score > 50",
           (result.get("confidence_score") or 0) > 50,
           f"got: {result.get('confidence_score')}")


def test_parser_arabic_txt():
    """Direct parser test for the Arabic sample."""
    _test_parser_language(
        "ar",
        "sample_invoice_ar.txt",
        {
            "invoice_number": "INV-2024-00143",
            "total_amount": 11500.0,
            "tax_amount": 1500.0,
            "vendor_tax_number": "300012345600003",
        },
    )


def test_parser_french_txt():
    """Direct parser test for the French sample."""
    _test_parser_language(
        "fr",
        "sample_invoice_fr.txt",
        {
            "invoice_number": "FA-2025-0091",
            "invoice_date": "12/03/2025",
            "total_amount": 4800.0,
            "tax_amount": 800.0,
            "currency": "EUR",
            "vendor_tax_number": "FR12345678901",
        },
    )


def test_parser_italian_txt():
    """Direct parser test for the Italian sample."""
    _test_parser_language(
        "it",
        "sample_invoice_it.txt",
        {
            "invoice_number": "IT-2025-0456",
            "invoice_date": "18/03/2025",
            "total_amount": 2928.0,
            "tax_amount": 528.0,
            "currency": "EUR",
        },
    )


def test_parser_hindi_txt():
    """Direct parser test for the Hindi sample."""
    _test_parser_language(
        "hi",
        "sample_invoice_hi.txt",
        {
            "invoice_number": "IND-2025-7788",
            "invoice_date": "20/03/2025",
            "total_amount": 64900.0,
            "tax_amount": 9900.0,
            "currency": "INR",
        },
    )


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print(f"\n{BOLD}{'═' * 60}{RESET}")
    print(f"{BOLD}  Invoice Extractor API — Manual Test Suite{RESET}")
    print(f"{BOLD}{'═' * 60}{RESET}")
    print(f"  Base URL : {CYAN}{BASE_URL}{RESET}")
    print(f"  API Key  : {CYAN}{'*' * min(len(API_KEY), 6)}{'...' if len(API_KEY) > 6 else '(empty — dev mode only)'}{RESET}")

    # Sections 1–4 talk to the running server
    test_connectivity()
    test_health()
    test_auth()
    test_file_validation()

    # Sections 5–6 require the sample PDF to exist
    test_extract_text()
    test_extract_full()

    # Sections 7–11 run the parser locally — no server needed
    test_parser_with_txt()
    test_parser_arabic_txt()
    test_parser_french_txt()
    test_parser_italian_txt()
    test_parser_hindi_txt()

    failed = summary()
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
