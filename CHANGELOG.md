# Changelog

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
