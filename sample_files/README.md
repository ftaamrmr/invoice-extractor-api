# Sample Files

This folder contains sample invoice files for manual testing of the Invoice Extractor API.

---

## Files

| File | Language | Description |
|---|---|---|
| `sample_invoice_en.txt` | English | Realistic SAR invoice with 3 line items, VAT, vendor details |
| `sample_invoice_ar.txt` | Arabic | Same invoice in Arabic with Arabic field labels |
| `sample_invoice_fr.txt` | French | EUR invoice with French labels and line items |
| `sample_invoice_it.txt` | Italian | EUR invoice with Italian labels and line items |
| `sample_invoice_hi.txt` | Hindi | INR invoice with Hindi labels and Devanagari numerals |
| `sample_invoice_*.pdf` | Various | PDF versions — generate with `python scripts/create_sample_pdf.py` |
| `README.md` | — | This file |

> **PDF files are not committed.** Generate them locally with the script below.

---

## Supported Languages

The parser has built-in regex support for invoices in the following languages:

- **English** (`eng`)
- **Arabic** (`ara`)
- **French** (`fra`)
- **Italian** (`ita`)
- **Hindi** (`hin`)

For OCR (scanned PDFs or image invoices), configure the languages you need in `.env`:

```bash
OCR_LANGUAGES=eng+ara+fra+ita+hin
```

> The Docker image ships all five Tesseract language packs. For local development you must install the matching packs.

---

## Generate PDF Samples

```bash
# From the project root (venv must be activated)
python scripts/create_sample_pdf.py
```

This generates `sample_invoice_en.pdf`, `sample_invoice_fr.pdf`, `sample_invoice_it.pdf`, and `sample_invoice_hi.pdf`. Arabic PDF generation is optional and requires downloading the Amiri font.

---

## What the Parser Should Extract

### English (`sample_invoice_en.txt` / `sample_invoice_en.pdf`)

| Field | Expected Value |
|---|---|
| `vendor_name` | Acme Technology Solutions LLC |
| `vendor_tax_number` | 300012345600003 |
| `invoice_number` | INV-2024-00142 |
| `invoice_date` | 15/01/2024 |
| `due_date` | 14/02/2024 |
| `payment_method` | Bank Transfer |
| `subtotal` | 10000.00 |
| `tax_amount` | 1500.00 |
| `total_amount` | 11500.00 |
| `currency` | SAR |

### French (`sample_invoice_fr.txt` / `sample_invoice_fr.pdf`)

| Field | Expected Value |
|---|---|
| `vendor_name` | Lumière Tech Solutions SARL |
| `vendor_tax_number` | FR12345678901 |
| `invoice_number` | FA-2025-0091 |
| `invoice_date` | 12/03/2025 |
| `due_date` | 12/04/2025 |
| `payment_method` | Virement bancaire |
| `subtotal` | 4000.00 |
| `tax_amount` | 800.00 |
| `total_amount` | 4800.00 |
| `currency` | EUR |

### Italian (`sample_invoice_it.txt` / `sample_invoice_it.pdf`)

| Field | Expected Value |
|---|---|
| `vendor_name` | Soluzioni Tech Italia S.r.l. |
| `vendor_tax_number` | IT98765432109 |
| `invoice_number` | IT-2025-0456 |
| `invoice_date` | 18/03/2025 |
| `due_date` | 17/04/2025 |
| `payment_method` | Bonifico bancario |
| `subtotal` | 2400.00 |
| `tax_amount` | 528.00 |
| `total_amount` | 2928.00 |
| `currency` | EUR |

### Hindi (`sample_invoice_hi.txt` / `sample_invoice_hi.pdf`)

| Field | Expected Value |
|---|---|
| `vendor_name` | भारतीय टेक सोल्यूशंस प्राइवेट लिमिटेड |
| `vendor_tax_number` | 27AABCU9603R1ZX |
| `invoice_number` | IND-2025-7788 |
| `invoice_date` | 20/03/2025 |
| `due_date` | 19/04/2025 |
| `payment_method` | NEFT / Bank Transfer |
| `subtotal` | 55000.00 |
| `tax_amount` | 9900.00 |
| `total_amount` | 64900.00 |
| `currency` | INR |

### Arabic (`sample_invoice_ar.txt`)

| Field | Expected Value |
|---|---|
| `vendor_tax_number` | 300012345600003 |
| `invoice_number` | INV-2024-00143 |
| `invoice_date` | 15/01/2024 |
| `due_date` | 14/02/2024 |
| `tax_amount` | 1500.00 |
| `total_amount` | 11500.00 |

---

## Test the Parser Directly (no server needed)

```bash
# From the project root with venv activated
python -c "
from app.services.parser import parse_invoice
import json

with open('sample_files/sample_invoice_fr.txt', encoding='utf-8') as f:
    text = f.read()

result = parse_invoice(text)
print(json.dumps({k: v for k, v in result.items() if k != 'raw_text'}, indent=2, ensure_ascii=False))
"
```

---

## Test via curl (API running on localhost:8000)

**Linux / macOS:**
```bash
export API_KEY=your-api-key-here

# Full extraction
curl -s -X POST http://localhost:8000/v1/invoices/extract \
  -H "X-API-Key: $API_KEY" \
  -F "file=@sample_files/sample_invoice_fr.pdf" | python3 -m json.tool

# Raw text only
curl -s -X POST http://localhost:8000/v1/invoices/extract-text \
  -H "X-API-Key: $API_KEY" \
  -F "file=@sample_files/sample_invoice_fr.pdf" | python3 -m json.tool
```

**Windows PowerShell:**
```powershell
$env:API_KEY = "your-api-key-here"

Invoke-RestMethod `
  -Uri "http://localhost:8000/v1/invoices/extract" `
  -Method POST `
  -Headers @{"X-API-Key" = $env:API_KEY} `
  -Form @{file = Get-Item "sample_files\sample_invoice_fr.pdf"}
```

---

## Use manual_test.py for Full Automated Checks

```bash
# Linux / macOS
export API_BASE_URL=http://localhost:8000
export API_KEY=your-api-key-here
python manual_test.py

# Windows PowerShell
$env:API_BASE_URL = "http://localhost:8000"
$env:API_KEY = "your-api-key-here"
python manual_test.py
```

---

## Notes

- The `.txt` files simulate what OCR would produce from a real scanned invoice.
- Confidence score will typically be 80–100 for these samples since most key fields are present.
- The parser supports mixed-language documents as long as field labels match one of the known patterns.
- Arabic regex patterns detect `رقم الفاتورة`, `الإجمالي`, `ضريبة القيمة المضافة`, etc.
- French patterns detect `Facture`, `Date de facture`, `Total TTC`, `TVA`, etc.
- Italian patterns detect `Fattura`, `Partita IVA`, `Imponibile`, `Importo totale`, etc.
- Hindi patterns detect `चालान संख्या`, `जीएसटीआईएन`, `उप-योग`, `कुल राशि`, etc.
- Never commit real customer invoices to this folder.
