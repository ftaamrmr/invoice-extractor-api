# Changelog

## [1.1.1] - 2026-08-03

### Security
- **OCR timeout hardening**: `pytesseract.image_to_string` now receives `timeout=OCR_TIMEOUT_SECONDS` directly, so the Tesseract subprocess itself is killed on timeout. Both the primary language call and the `eng` fallback enforce the timeout. A `TesseractError` containing "timed out" is unified to `OCRTimeoutError`, which propagates as `TimeoutError` and is safely surfaced as HTTP 504 `PROCESSING_TIMEOUT` without leaking system details.
- **Rate-limit identity hardening**: `X-RapidAPI-User` and `X-RapidAPI-Subscription` headers are now only trusted for rate-limit identity when `X-RapidAPI-Proxy-Secret` is verified with `secrets.compare_digest`. Without a valid proxy secret the identity falls back to IP, preventing header spoofing from bypassing per-user rate limits.
- **Production auth config guard**: `APP_ENV=production` is now rejected at startup when both `REQUIRE_RAPIDAPI_SECRET=false` and `DIRECT_API_ACCESS_ENABLED=false`, ensuring the API never starts in production without at least one authentication method active.

### Changed
- `MAX_CONCURRENT_OCR_JOBS` default changed from `2` to `1` (recommended for 1 vCPU servers).
- `.env.example` updated to reflect `MAX_CONCURRENT_OCR_JOBS=1` with a comment.

## [1.1.0] - 2026-08-02

### Added
- Strict production settings validation with explicit limits and auth safety checks.
- Unified error envelope with request IDs and safer public error messages.
- In-memory rate limiting for `/v1/*` with response headers.
- `/ready` endpoint with OCR/runtime dependency checks.
- Security/privacy headers and `Cache-Control: no-store` on extraction responses.
- New docs: production checklist, privacy policy, legal terms template.
- CI workflow for compile, lint, tests, and Docker build.

### Changed
- Hardened RapidAPI/direct-auth logic using constant-time comparisons.
- Rebuilt upload validator with chunked reading, magic-byte checks, PDF/image validation, and page limits.
- OCR now runs in threads with timeout + concurrency semaphore.
- Parser improved for multilingual number formats and capped line items.
- Docker and docker-compose updated for production defaults and health checks.
- Landing page refreshed with EN default + AR toggle + dark/light mode.

### Security
- Reduced sensitive logging surface; standardized structured logging in production.
- Removed committed Python cache artifacts.

## [1.0.0] - 2026-06-25
- Initial MVP release.
