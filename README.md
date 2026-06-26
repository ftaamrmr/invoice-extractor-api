# Invoice Extractor API

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111.0-009688.svg)](https://fastapi.tiangolo.com/)
[![Docker](https://img.shields.io/badge/Docker-ready-2496ED.svg)](https://www.docker.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)
[![Coolify](https://img.shields.io/badge/Coolify-ready-6366F1.svg)](./COOLIFY_DEPLOYMENT.md)

> Extract structured invoice data from PDF and image files.  
> Vendor name, invoice number, dates, VAT, total, currency, line items — and a confidence score.

Built with **FastAPI**. Ready for **local development**, **Docker deployment**, **Coolify VPS hosting**, and commercial distribution on **RapidAPI**.

---

## Quick Start

```bash
# 1. Clone the repo
git clone https://github.com/your-username/invoice-extractor-api.git
cd invoice-extractor-api

# 2. Create a virtual environment
python3 -m venv venv
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Copy the example .env and set APP_ENV=development for local testing
cp .env.example .env
# Edit .env: APP_ENV=development, API_KEY=any-value

# 5. Run the server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Open http://localhost:8000 for the landing page or http://localhost:8000/docs for Swagger UI.

---

## Docker Quick Start

```bash
cp .env.example .env
# Edit .env: APP_ENV=production, API_KEY=<strong-key>

docker-compose up --build -d

curl http://localhost:8000/health
```

---

## Features

- **Multilingual invoice parsing** — English, Arabic, French, Italian, and Hindi
- **PDF text extraction** using PyMuPDF (fast, no OCR needed for digital PDFs)
- **OCR fallback** for scanned PDFs and image invoices via pytesseract
- **Confidence score** (0–100) per extraction
- **API key authentication** via `X-API-Key` or `X-RapidAPI-Proxy-Secret`
- **Clean error responses** with machine-readable error codes
- **Swagger UI** at `/docs`
- **Docker + docker-compose** ready
- **Coolify** deployable
- **Manual testing suite** included

---

## Tech Stack

| Layer | Library |
|---|---|
| Framework | FastAPI + Uvicorn |
| PDF extraction | PyMuPDF (fitz) |
| Image handling | Pillow |
| OCR | pytesseract (Docker ships English, Arabic, French, Italian, Hindi packs) |
| Sample PDFs | reportlab |
| Validation | Pydantic v2 |
| Config | pydantic-settings + python-dotenv |
| Testing | pytest + httpx |
| Container | Docker + docker-compose |

---

## Project Structure

```
invoice-extractor-api/
├── app/
│   ├── main.py            # FastAPI app, routers, health check
│   ├── config.py          # Settings from .env
│   ├── security.py        # API key authentication
│   ├── schemas.py         # Pydantic request/response models
│   ├── services/          # Extractors, parser, OCR, validators
│   └── utils/             # Text cleaning helpers
├── tests/                 # pytest automated tests
├── sample_files/          # Sample invoices for testing
├── scripts/               # create_sample_pdf.py
├── static/
│   └── index.html         # Bilingual landing page
├── manual_test.py         # Live API tester
├── Dockerfile             # Production image
├── docker-compose.yml
├── requirements.txt
├── .env.example
├── README.md              # This file
├── RAPIDAPI_GUIDE.md      # Sell on RapidAPI
├── COOLIFY_DEPLOYMENT.md  # Self-hosted Coolify guide
├── LICENSE                # MIT
├── SECURITY.md            # Security policy
├── CHANGELOG.md           # Release notes
└── VERSION                # 1.0.0
```

---

## Local Setup

### Prerequisites

- Python 3.11+
- (Optional) Tesseract OCR binary — required only for scanned PDFs and image files

**Install Tesseract on Ubuntu/Debian:**
```bash
sudo apt-get install tesseract-ocr tesseract-ocr-eng tesseract-ocr-ara tesseract-ocr-fra tesseract-ocr-ita tesseract-ocr-hin
```

**Install Tesseract on macOS:**
```bash
brew install tesseract tesseract-lang
```

**Install Tesseract on Windows:**
Download the installer from https://github.com/UB-Mannheim/tesseract/wiki  
Install to `C:\Program Files\Tesseract-OCR` and add it to your PATH.

---

### Linux / macOS (bash)

```bash
# 1. Clone the repo
git clone https://github.com/your-username/invoice-extractor-api.git
cd invoice-extractor-api

# 2. Create virtual environment
python3 -m venv venv
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Create .env (then edit it with your real API_KEY)
cp .env.example .env

# 5. Set APP_ENV=development for local testing (no API key required)
# Edit .env and change: APP_ENV=development

# 6. Run the server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Windows PowerShell

```powershell
# 1. Clone the repo
git clone https://github.com/your-username/invoice-extractor-api.git
cd invoice-extractor-api

# 2. Create virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1

# 3. Install dependencies
pip install -r requirements.txt

# 4. Copy .env.example to .env and edit it
Copy-Item .env.example .env
# Open .env in your editor and set:
#   APP_ENV=development    (skip auth for local testing)
#   API_KEY=any-value-here

# 5. Run the server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Open http://localhost:8000 for the landing page or http://localhost:8000/docs for Swagger UI.

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `APP_NAME` | Invoice Extractor API | Service name |
| `APP_ENV` | **production** | `production` enforces auth; use `development` locally |
| `API_KEY` | *(must change)* | Your direct API key for `X-API-Key` header |
| `RAPIDAPI_PROXY_SECRET` | *(must change)* | RapidAPI proxy secret (from provider dashboard) |
| `MAX_FILE_SIZE_MB` | 10 | Maximum upload size in MB |
| `ENABLE_OCR` | true | Enable OCR for scanned PDFs and images |
| `OCR_LANGUAGES` | eng+ara | Tesseract language string, e.g. `eng+ara+fra+ita+hin` |

---

## API Endpoints

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/` | No | Landing page |
| GET | `/health` | No | Health check |
| GET | `/docs` | No | Swagger UI |
| POST | `/v1/invoices/extract` | Yes | Full structured extraction |
| POST | `/v1/invoices/extract-text` | Yes | Raw text only |

---

## API Examples

### 1. Full invoice extraction

```bash
curl -X POST http://localhost:8000/v1/invoices/extract \
  -H "X-API-Key: your-api-key" \
  -F "file=@sample_files/sample_invoice_en.pdf"
```

### 2. Raw text only

Useful for debugging OCR or parser output.

```bash
curl -X POST http://localhost:8000/v1/invoices/extract-text \
  -H "X-API-Key: your-api-key" \
  -F "file=@sample_files/sample_invoice_en.pdf"
```

### 3. RapidAPI call

RapidAPI automatically adds `X-RapidAPI-Key` and `X-RapidAPI-Host`; the request is proxied to your server with `X-RapidAPI-Proxy-Secret`.

```bash
curl -X POST https://invoice-extractor-pdf-to-json.p.rapidapi.com/v1/invoices/extract \
  -H "X-RapidAPI-Key: USER_API_KEY" \
  -H "X-RapidAPI-Host: invoice-extractor-pdf-to-json.p.rapidapi.com" \
  -F "file=@invoice.pdf"
```

### 4. Health check

```bash
curl http://localhost:8000/health
```

### Sample successful response

```json
{
  "success": true,
  "data": {
    "vendor_name": "Acme Corp Ltd",
    "vendor_tax_number": "300012345600003",
    "invoice_number": "INV-2024-00142",
    "invoice_date": "15/01/2024",
    "due_date": "14/02/2024",
    "currency": "SAR",
    "subtotal": 1000.00,
    "tax_amount": 150.00,
    "total_amount": 1150.00,
    "payment_method": "Bank Transfer",
    "line_items": [
      {
        "description": "Web Design Services",
        "quantity": 1.0,
        "unit_price": 1000.00,
        "total": 1000.00
      }
    ],
    "confidence_score": 90.0,
    "raw_text": "..."
  },
  "meta": {
    "filename": "invoice.pdf",
    "file_type": "pdf",
    "extraction_method": "pdf_text",
    "processing_time_ms": 84
  }
}
```

### Error response example

```json
{
  "success": false,
  "error": {
    "code": "UNAUTHORIZED",
    "message": "Valid API key is required. Provide X-API-Key or X-RapidAPI-Proxy-Secret header."
  }
}
```

---

## Commercial Usage

This project is released under the **MIT License** (see `LICENSE`). You are free to:

- **Self-host** the API and sell subscriptions directly to your customers.
- **Publish** the API on marketplaces such as RapidAPI.
- **Modify and white-label** it for internal tools, ERP integrations, or accounting platforms.
- **Build a SaaS** around it with your own billing layer.

### Suggested revenue models

| Model | Description |
|---|---|
| **RapidAPI listing** | Free + paid tiers with usage caps. RapidAPI handles payments and rate limiting. |
| **Direct SaaS** | Host on Coolify, sell monthly plans, and bill via Stripe or a local payment gateway. |
| **Enterprise integrations** | One-time setup fee + monthly maintenance for custom parser rules. |

### Branding and pricing (suggested)

- Product name: **Invoice Extractor PDF to JSON API**
- Tagline: *Extract structured invoice data from PDF and image invoices using a simple API.*
- Plans: Free 50 req/mo, Starter $9/mo 1,000 req, Pro $29/mo 10,000 req, Business $79/mo 50,000 req.

For step-by-step marketplace setup see [`RAPIDAPI_GUIDE.md`](./RAPIDAPI_GUIDE.md).  
For self-hosted deployment see [`COOLIFY_DEPLOYMENT.md`](./COOLIFY_DEPLOYMENT.md).

---

## Docker Setup

```bash
# Build and start
docker-compose up --build -d

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

The API will be available at http://localhost:8000.

---

## Manual Testing

A complete manual testing script is provided: `manual_test.py`.  
It runs real HTTP requests against the API and also tests the parser directly against the text samples.

### Prerequisites

```bash
pip install requests reportlab
```

Or reinstall from requirements:

```bash
pip install -r requirements.txt
```

---

### Generate the sample PDF

First create `sample_files/sample_invoice_en.pdf`:

```bash
python scripts/create_sample_pdf.py
```

This generates an English PDF. Arabic PDF generation is optional and requires downloading the Amiri font (see the script help or `sample_files/README.md`).

---

### Run on Windows PowerShell

```powershell
# 1. Open PowerShell in the project root directory:
cd C:\path\to\invoice-extractor-api

# 2. Create a virtual environment and activate it
python -m venv venv
.\venv\Scripts\Activate.ps1

# 3. Install dependencies
pip install -r requirements.txt

# 4. Copy the environment file and edit it
Copy-Item .env.example .env
# Open .env and set:
#   APP_ENV=development          (no API key required locally)
#   API_KEY=any-value-you-want

# 5. Start the API
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

In a **second PowerShell window**:

```powershell
cd C:\path\to\invoice-extractor-api
.\venv\Scripts\Activate.ps1

# Generate the sample PDF
python scripts/create_sample_pdf.py

# Run the manual tests
$env:API_BASE_URL = "http://localhost:8000"
$env:API_KEY      = "any-value-you-want"    # must match .env API_KEY
python manual_test.py
```

---

### Run with Docker

```bash
# 1. Copy and edit the environment file
cp .env.example .env
# Set: APP_ENV=production, API_KEY=your-real-key, RAPIDAPI_PROXY_SECRET=...

# 2. Start the container
docker-compose up --build -d

# 3. Generate the sample PDF (if reportlab is installed locally)
python scripts/create_sample_pdf.py
```

Then run the manual tester against the container:

```bash
# Linux / macOS
export API_BASE_URL=http://localhost:8000
export API_KEY=your-real-key
python manual_test.py

# Windows PowerShell
$env:API_BASE_URL = "http://localhost:8000"
$env:API_KEY      = "your-real-key"
python manual_test.py
```

---

### What manual_test.py verifies

- `GET /health` returns 200 with required fields
- `POST /v1/invoices/extract-text` works on `sample_invoice_en.pdf`
- `POST /v1/invoices/extract` extracts key fields (invoice_number, invoice_date, total_amount, tax_amount, currency, confidence_score)
- Missing/wrong API key behaviour (401 in production, skipped in development)
- Unsupported file type → 422
- Empty file → 422
- File too large → 413
- Parser direct tests on `sample_invoice_en.txt`
- Parser Arabic direct tests on `sample_invoice_ar.txt`

For more details see `sample_files/README.md`.

---

## Docker Setup

```bash
# Build and start
docker-compose up --build -d

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

The API will be available at http://localhost:8000.

---

## Testing

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run a specific test file
pytest tests/test_health.py -v
```

---

## Confidence Score

| Field found | Points |
|---|---|
| invoice_number | +20 |
| invoice_date | +15 |
| total_amount | +25 |
| tax_amount | +10 |
| vendor_name | +10 |
| currency | +10 |
| line_items | +10 |
| **Maximum** | **100** |

---

## Error Codes

| Code | HTTP | Meaning |
|---|---|---|
| `UNAUTHORIZED` | 401 | Missing or invalid API key |
| `UNSUPPORTED_FILE_TYPE` | 422 | File extension not allowed |
| `EMPTY_FILE` | 422 | Uploaded file has zero bytes |
| `FILE_TOO_LARGE` | 422 | File exceeds MAX_FILE_SIZE_MB |
| `EXTRACTION_FAILED` | 422 | Could not read text from file |

---

## Monetization Strategy

1. **Publish on RapidAPI** – see `RAPIDAPI_GUIDE.md`
2. **Deploy on VPS via Coolify** – see `COOLIFY_DEPLOYMENT.md`
3. Use RapidAPI's built-in billing and rate limiting per plan tier
4. Offer custom plans via direct contact for enterprise customers

---

## Limitations

- Rule-based parser: may miss fields on unusual invoice layouts
- OCR accuracy depends on Tesseract quality and image resolution
- Line-item extraction is best-effort on simple table formats
- Arabic OCR requires `tesseract-ocr-ara` language pack installed
- French, Italian, and Hindi parsing requires matching Tesseract packs for OCR; digital PDFs work without OCR

---

## Future Improvements

- **LLM-based parsing** (GPT-4o, Claude, or local model) for higher accuracy
- **PostgreSQL** with user accounts and usage tracking
- **Stripe integration** for self-hosted billing
- **Admin dashboard** with request logs and analytics
- **Redis queue** for async batch processing
- **ZATCA e-invoice support** (Saudi Arabia XML format)
- **Webhook callbacks** when processing completes
- **Batch extraction** endpoint for multiple invoices
- **Multi-language OCR** expansion (German, Spanish, Chinese, etc.)
- **EasyOCR** as default fallback (no binary required)
