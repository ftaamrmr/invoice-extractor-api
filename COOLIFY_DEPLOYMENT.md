# Coolify Deployment (v1.1.1)

## Required env vars
Set all values from `.env.example`, especially:
- `APP_ENV=production`
- `REQUIRE_RAPIDAPI_SECRET=true` **or** `DIRECT_API_ACCESS_ENABLED=true` (at least one must be set)
- Strong `RAPIDAPI_PROXY_SECRET` (≥16 chars, required when `REQUIRE_RAPIDAPI_SECRET=true`)
- Optional strong `API_KEY` only if `DIRECT_API_ACCESS_ENABLED=true`

## OCR concurrency
- `MAX_CONCURRENT_OCR_JOBS=1` is recommended for single-vCPU servers to avoid memory pressure.
- Increase only if the server has multiple CPUs and sufficient RAM.

## Health paths
- Liveness: `/health`
- Readiness: `/ready`

## Troubleshooting
- **502/503**: check container logs, then `/ready` response.
- **unhealthy**: verify health check path `/health` and startup time.
- **tesseract/lang missing**: install required language packs and confirm `/ready`.
- **timeouts**: tune `OCR_TIMEOUT_SECONDS` and `REQUEST_TIMEOUT_SECONDS`.
- **OOM**: lower `MAX_FILE_SIZE_MB`, `MAX_PDF_PAGES`, `MAX_CONCURRENT_OCR_JOBS`, or scale memory.
- **401**: verify `X-RapidAPI-Proxy-Secret` and auth settings.
- **startup error "at least one auth method"**: set `REQUIRE_RAPIDAPI_SECRET=true` or `DIRECT_API_ACCESS_ENABLED=true`.
- **SSL**: enable HTTPS/certificates in Coolify domain settings.
