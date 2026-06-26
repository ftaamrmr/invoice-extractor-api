# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [1.0.0] - 2026-06-25

### Added — Initial MVP Release

- FastAPI application with PDF and image invoice extraction endpoints
- Rule-based invoice parser supporting English and Arabic layouts
- Text extraction from native PDFs via PyMuPDF
- OCR fallback for scanned PDFs and image invoices via pytesseract
- Configurable OCR language support (`OCR_LANGUAGES=eng+ara`)
- API key authentication for direct integrations
- X-RapidAPI-Proxy-Secret support for RapidAPI deployments
- Pydantic response schemas with confidence scoring (0–100)
- File upload validation (size, type, non-empty)
- Public landing page with English and Arabic sections
- Swagger UI and ReDoc at `/docs` and `/redoc`
- Docker and docker-compose production configuration
- Coolify deployment guide
- RapidAPI publishing guide
- Manual testing suite (`manual_test.py`) and sample invoice files
- Pytest automated tests for health, auth, validation, and parser

### Notes

- This is the first public release suitable for self-hosted SaaS and RapidAPI listing.
- Authentication defaults to `production` mode to prevent accidental open deployments.
- OCR requires Tesseract to be installed; it is included in the Docker image.

### Known Limitations

- Parser is rule-based (regex); highly unusual invoice layouts may not extract every field.
- Arabic OCR rendering into PDF is optional and requires the Amiri font.
- Line-item extraction is best-effort on simple tabular formats.
- No built-in rate limiting or usage analytics in this release.

