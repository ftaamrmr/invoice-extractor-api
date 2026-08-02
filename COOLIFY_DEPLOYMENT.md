# Coolify Deployment (v1.1.0)

## Required env vars
Set all values from `.env.example`, especially:
- `APP_ENV=production`
- `REQUIRE_RAPIDAPI_SECRET=true`
- strong `RAPIDAPI_PROXY_SECRET`
- optional strong `API_KEY` only if `DIRECT_API_ACCESS_ENABLED=true`

## Health paths
- Liveness: `/health`
- Readiness: `/ready`

## Troubleshooting
- **502/503**: check container logs, then `/ready` response.
- **unhealthy**: verify health check path `/health` and startup time.
- **tesseract/lang missing**: install required language packs and confirm `/ready`.
- **timeouts**: tune `OCR_TIMEOUT_SECONDS` and `REQUEST_TIMEOUT_SECONDS`.
- **OOM**: lower `MAX_FILE_SIZE_MB`, `MAX_PDF_PAGES`, or scale memory.
- **401**: verify `X-RapidAPI-Proxy-Secret` and auth settings.
- **SSL**: enable HTTPS/certificates in Coolify domain settings.
