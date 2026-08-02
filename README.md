# Invoice Extractor API v1.1.0

Production-ready FastAPI service for extracting structured invoice data from PDF/images using **PyMuPDF + Tesseract OCR + rule-based parsing**.

## Key points
- Endpoints: `POST /v1/invoices/extract`, `POST /v1/invoices/extract-text`
- Supported OCR langs: `eng+ara+fra+ita+hin`
- No intentional invoice persistence after request completion
- Unified safe errors with `request_id`
- Request timeout + OCR timeout + OCR concurrency limit
- RapidAPI proxy-secret auth support

## Security defaults
- `INCLUDE_RAW_TEXT=false` by default.
- `DIRECT_API_ACCESS_ENABLED=false` by default.
- `REQUIRE_RAPIDAPI_SECRET=true` expected in production.
- Responses include `X-Request-ID` and extraction responses set `Cache-Control: no-store`.

## Run locally
```bash
cp .env.example .env
pip install -r requirements-dev.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## Docker
```bash
docker build -t invoice-extractor-api:1.1.0 .
docker run --rm -p 8000:8000 --env-file .env invoice-extractor-api:1.1.0
```

## Docs
- [COOLIFY_DEPLOYMENT.md](./COOLIFY_DEPLOYMENT.md)
- [RAPIDAPI_GUIDE.md](./RAPIDAPI_GUIDE.md)
- [PRODUCTION_CHECKLIST.md](./PRODUCTION_CHECKLIST.md)
- [PRIVACY.md](./PRIVACY.md)
- [TERMS_TEMPLATE.md](./TERMS_TEMPLATE.md)
