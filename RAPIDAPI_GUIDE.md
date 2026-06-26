# Publishing on RapidAPI

Complete guide to list **Invoice Extractor PDF to JSON API** on [RapidAPI](https://rapidapi.com) and start earning money.

---

## Suggested API Listing

| Field | Recommended Value |
|---|---|
| **API Title** | Invoice Extractor PDF to JSON API |
| **Short Description** | Extract structured invoice data from PDF and image invoices using a simple API. |
| **Long Description** | See below. |
| **Category** | Finance / Document Processing / Accounting |
| **Visibility** | Public |
| **Keywords** | `invoice OCR`, `PDF invoice`, `invoice parser`, `receipt parser`, `document automation`, `accounting API`, `invoice to JSON`, `OCR invoice`, `invoice extraction`, `financial documents`, `multilingual invoice`, `Arabic invoice`, `French invoice`, `Italian invoice`, `Hindi invoice` |

### Long Description

> This API extracts important invoice fields such as invoice number, invoice date, due date, vendor name, vendor tax number, subtotal, tax amount (VAT), total amount, currency, payment method, and line items from PDF and image invoices.
>
> It is useful for accounting tools, ERP systems, document automation, receipt processors, bookkeeping platforms, and business workflow automation.
>
> Supports English, Arabic, French, Italian, and Hindi invoices. Returns a confidence score (0–100) so you know how reliable each extraction is.

---

## Suggested Pricing Plans

| Plan | Monthly Price | Requests/Month | Overage | Notes |
|---|---|---|---|---|
| **Free** | $0 | 50 | — | Great for evaluation and testing |
| **Starter** | $9 | 1,000 | $0.01/request | For freelancers and small tools |
| **Pro** | $29 | 10,000 | $0.005/request | For startups and integrations |
| **Business** | $79 | 50,000 | $0.002/request | For high-volume SaaS/ERP |

---

## Endpoints

### `POST /v1/invoices/extract`

**Description:** Upload a PDF or image invoice and receive structured JSON with invoice fields, line items, and a confidence score.

**Content-Type:** `multipart/form-data`

#### Headers

| Header | Required | Example / Source |
|---|---|---|
| `X-RapidAPI-Key` | Yes | RapidAPI user's subscription key (sent automatically by RapidAPI) |
| `X-RapidAPI-Host` | Yes | `invoice-extractor-pdf-to-json.p.rapidapi.com` (sent automatically) |
| `X-RapidAPI-Proxy-Secret` | Yes (backend only) | Must match `RAPIDAPI_PROXY_SECRET` in your server `.env` |

> Do **not** list `X-RapidAPI-Proxy-Secret` as a user-facing header — RapidAPI sends it automatically.

#### Parameters

| Name | Type | Required | Description |
|---|---|---|---|
| `file` | file | Yes | Invoice file: PDF, PNG, JPG, or JPEG. Maximum 10 MB by default. |

#### Response Fields

Top level:

| Field | Type | Description |
|---|---|---|
| `success` | boolean | `true` if extraction completed |
| `data` | object | Extracted invoice fields |
| `meta` | object | Metadata about the request and file |

`data` object:

| Field | Type | Description |
|---|---|---|
| `vendor_name` | string \| null | Invoice sender / vendor |
| `vendor_tax_number` | string \| null | VAT / tax registration number |
| `invoice_number` | string \| null | Invoice identifier |
| `invoice_date` | string \| null | Issue date as found in the document |
| `due_date` | string \| null | Payment due date |
| `currency` | string \| null | Detected currency code (SAR, USD, EUR, AED, GBP, INR, etc.) |
| `subtotal` | number \| null | Amount before tax |
| `tax_amount` | number \| null | Tax / VAT amount |
| `total_amount` | number \| null | Final total amount due |
| `payment_method` | string \| null | Payment method if detected |
| `line_items` | array | Detected line items (description, quantity, unit_price, total) |
| `confidence_score` | number | 0–100 score based on how many fields were found |
| `raw_text` | string | Full text extracted from the file |

`meta` object:

| Field | Type | Description |
|---|---|---|
| `filename` | string | Original uploaded filename |
| `file_type` | string | `pdf` or `image` |
| `extraction_method` | string | `pdf_text`, `ocr`, or `fallback` |
| `processing_time_ms` | integer | Server processing time in milliseconds |

#### Example Request (RapidAPI user's curl)

```bash
curl -X POST https://invoice-extractor-pdf-to-json.p.rapidapi.com/v1/invoices/extract \
  -H "X-RapidAPI-Key: USER_API_KEY" \
  -H "X-RapidAPI-Host: invoice-extractor-pdf-to-json.p.rapidapi.com" \
  -F "file=@invoice.pdf"
```

#### Supported OCR Languages

Configure the languages you need with the `OCR_LANGUAGES` environment variable:

| Value | Languages |
|---|---|
| `eng` | English |
| `eng+ara` | English + Arabic |
| `eng+ara+fra` | English + Arabic + French |
| `eng+ara+fra+ita+hin` | English + Arabic + French + Italian + Hindi |

> **Note:** The official Docker image includes all five language packs. For local development or non-Docker deployments, you must install the matching Tesseract language packs.

#### Example Response

```json
{
  "success": true,
  "data": {
    "vendor_name": "Acme Technology Solutions LLC",
    "vendor_tax_number": "300012345600003",
    "invoice_number": "INV-2024-00142",
    "invoice_date": "15/01/2024",
    "due_date": "14/02/2024",
    "currency": "SAR",
    "subtotal": 10000.00,
    "tax_amount": 1500.00,
    "total_amount": 11500.00,
    "payment_method": "Bank Transfer",
    "line_items": [
      {
        "description": "Enterprise Software License",
        "quantity": 1,
        "unit_price": 5000.00,
        "total": 5000.00
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

---

### `POST /v1/invoices/extract-text`

**Description:** Extract only the raw text from a PDF or image invoice. Useful for debugging, OCR quality checks, and RapidAPI test requests.

**Content-Type:** `multipart/form-data`

#### Headers

Same as `/v1/invoices/extract`.

#### Parameters

| Name | Type | Required | Description |
|---|---|---|---|
| `file` | file | Yes | Invoice file: PDF, PNG, JPG, or JPEG. |

#### Response Fields

| Field | Type | Description |
|---|---|---|
| `success` | boolean | `true` |
| `data.raw_text` | string | Extracted plain text |
| `meta` | object | Same as `/v1/invoices/extract` |

#### Example Request

```bash
curl -X POST https://invoice-extractor-pdf-to-json.p.rapidapi.com/v1/invoices/extract-text \
  -H "X-RapidAPI-Key: USER_API_KEY" \
  -H "X-RapidAPI-Host: invoice-extractor-pdf-to-json.p.rapidapi.com" \
  -F "file=@invoice.png"
```

---

## Error Codes

All errors return structured JSON:

```json
{
  "success": false,
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable error description."
  }
}
```

| HTTP | Code | Meaning |
|---|---|---|
| 400 | `BAD_REQUEST` | Generic malformed request |
| 401 | `UNAUTHORIZED` | Missing or invalid API key / proxy secret |
| 404 | `NOT_FOUND` | Endpoint does not exist |
| 413 | `FILE_TOO_LARGE` | File exceeds `MAX_FILE_SIZE_MB` |
| 422 | `UNSUPPORTED_FILE_TYPE` | File extension is not PDF/PNG/JPG/JPEG |
| 422 | `EMPTY_FILE` | Uploaded file has zero bytes |
| 422 | `EXTRACTION_FAILED` | Could not extract readable text from the file |
| 422 | `VALIDATION_ERROR` | FastAPI request validation error |
| 500 | `INTERNAL_SERVER_ERROR` | Unexpected server error |

---

## How RapidAPI Authentication Works

1. A user subscribes to your API on RapidAPI.
2. RapidAPI forwards their requests to your server, adding `X-RapidAPI-Proxy-Secret` automatically.
3. Your server validates this header against `RAPIDAPI_PROXY_SECRET` from your environment variables.
4. If valid, the request is processed.

You do **not** manage individual user API keys — RapidAPI handles billing, rate limiting, and key validation.

---

## Publishing Steps

1. **Create a RapidAPI provider account** at https://rapidapi.com/provider.
2. Click **Add New API**.
3. Enter the title, description, category, and keywords listed above.
4. Set the base URL to your hosted API, e.g. `https://api.yourdomain.com`.
5. Go to **API Settings → Proxy Secret** and copy the value into your server's `RAPIDAPI_PROXY_SECRET` env var.
6. Add the two endpoints: `POST /v1/invoices/extract` and `POST /v1/invoices/extract-text`.
7. Fill in parameters, response fields, and example responses for each endpoint.
8. Set pricing plans as described above.
9. Add a logo/icon (optional but improves conversion).
10. Submit the API for review.

---

## Pre-Publish Checklist

- [ ] API is deployed at a public HTTPS URL
- [ ] `APP_ENV=production` is set on the server
- [ ] `API_KEY` and `RAPIDAPI_PROXY_SECRET` are strong, non-placeholder values
- [ ] `/health` returns 200 from the public domain
- [ ] `POST /v1/invoices/extract` works from your local machine with the RapidAPI test flow
- [ ] `X-Processing-Time` header is returned
- [ ] HTTPS is enforced on the domain
- [ ] Swagger docs at `/docs` load correctly
- [ ] Pricing plans are configured in the RapidAPI dashboard

---

## Tips for Better Conversion

- Add a clear **Use Case** section: accounting, ERP, document automation, bookkeeping.
- Include 2–3 realistic example responses.
- Keep the Free plan at 50 requests/month so users can test without paying.
- Respond quickly to user questions in the RapidAPI discussion tab.
- Add a short demo video showing a real invoice upload and JSON result.

---

## After Publishing

- Monitor usage in the RapidAPI dashboard.
- Set billing notification emails.
- Review server logs for common extraction failures and improve the parser.
- Promote your API on LinkedIn, product directories, and developer communities.
