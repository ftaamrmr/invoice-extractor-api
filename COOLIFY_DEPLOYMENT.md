# Deploying on Coolify

This guide walks you through deploying Invoice Extractor API on your VPS using [Coolify](https://coolify.io).

---

## Prerequisites

- A VPS with Coolify installed (Ubuntu 22.04 recommended, minimum 2 GB RAM for OCR)
- Your project pushed to a Git repository (GitHub, GitLab, or Gitea)
- Port 8000 available on the server (Coolify maps it via its reverse proxy)

---

## Step-by-Step Deployment

### 1. Log in to Coolify

Open your Coolify dashboard at `https://your-coolify-server`.

### 2. Create a New Resource

- Click **New Resource** → **Application**
- Select your Git provider and repository
- Choose the branch: `main`

### 3. Configure Build Settings

| Setting | Value |
|---|---|
| Build Pack | **Dockerfile** |
| Dockerfile path | `Dockerfile` |
| Port | `8000` |

### 4. Set Environment Variables

In the **Environment Variables** section, add **all** of the following.  
Replace placeholder values with your real secrets.

```
APP_NAME=Invoice Extractor API
APP_VERSION=1.0.0
APP_ENV=production
API_KEY=your-strong-random-api-key-here
RAPIDAPI_PROXY_SECRET=your-rapidapi-proxy-secret-here
MAX_FILE_SIZE_MB=10
ENABLE_OCR=true
OCR_LANGUAGES=eng+ara
```

**Critical notes:**
- `APP_ENV=production` is required — it enforces API key authentication on every request.
- `API_KEY` must be a strong random string. Generate one with:
  ```bash
  python -c "import secrets; print(secrets.token_urlsafe(32))"
  ```
- `RAPIDAPI_PROXY_SECRET` must match the value shown in your RapidAPI Provider Dashboard → API Settings → Proxy Secret.
- Never use the placeholder values from `.env.example` in production.

### 5. Configure Health Check

| Setting | Value |
|---|---|
| Health Check Path | `/health` |
| Health Check Method | `GET` |
| Health Check Interval | `30s` |
| Health Check Timeout | `10s` |
| Start Period | `15s` |

The `/health` endpoint requires no authentication and returns:
```json
{ "status": "ok", "service": "Invoice Extractor API", "version": "1.0.0", "environment": "production" }
```

### 6. Deploy

Click **Deploy** and wait for the build to complete (first build takes ~3–5 minutes due to Tesseract installation).

---

## Start Command

Coolify uses the `CMD` from the Dockerfile automatically. The start command is:

```
uvicorn app.main:app --host 0.0.0.0 --port 8000 --proxy-headers --forwarded-allow-ips=*
```

- `--proxy-headers` — required so Coolify's Nginx/Traefik reverse proxy passes the real client IP.
- `--forwarded-allow-ips=*` — required when the upstream proxy IP is dynamic (Coolify default).

---

## Post-Deployment Verification

```bash
# 1. Check the service is healthy
curl https://your-domain.com/health

# Expected response:
# {"status":"ok","service":"Invoice Extractor API","version":"1.0.0","environment":"production"}

# 2. Test authentication (should fail with no key)
curl -X POST https://your-domain.com/v1/invoices/extract \
  -F "file=@invoice.pdf"
# Expected: 401 UNAUTHORIZED

# 3. Test with a real API key
curl -X POST https://your-domain.com/v1/invoices/extract \
  -H "X-API-Key: your-api-key" \
  -F "file=@invoice.pdf"
# Expected: 200 with structured JSON
```

---

## Custom Domain

In Coolify:
1. Go to **Domains** for your service
2. Add your custom domain: `api.yourdomain.com`
3. Enable **Let's Encrypt** for free HTTPS (strongly recommended)

---

## Common Errors and Solutions

### Build fails: `tesseract not found`

The Dockerfile installs Tesseract automatically. Ensure the build process has internet access. If behind a proxy, configure Docker's `HTTP_PROXY` build args in Coolify settings.

### 401 on every request

- Check that `APP_ENV=production` is set in environment variables.
- Check that the `API_KEY` value in Coolify matches the `X-API-Key` header you send.
- Placeholder values (`change-me-*`) are rejected by the API — use a real key.

### OCR produces no text

- Confirm `ENABLE_OCR=true` is set.
- Confirm `OCR_LANGUAGES=eng+ara` is set (or `eng` for English only).
- Check container logs: `docker logs invoice-extractor-api`
- The Arabic language pack (`tesseract-ocr-ara`) is installed in the Dockerfile.

### Container crashes on startup

- Check for missing environment variables using Coolify logs.
- Ensure `API_KEY` and `RAPIDAPI_PROXY_SECRET` are set (even if not used, they must not be empty).

### App runs out of memory on large PDFs

- Increase VPS RAM or reduce `MAX_FILE_SIZE_MB`.
- Recommended minimum: 2 GB RAM when OCR is enabled.

---

## Updating the Deployment

Push new code to your Git branch. In Coolify click **Redeploy** or enable **Auto Deploy** in service settings.

---

## Recommended VPS Specs

| Tier | RAM | CPU | Storage | Notes |
|---|---|---|---|---|
| Minimal | 1 GB | 1 vCPU | 20 GB | Text-based PDFs only (ENABLE_OCR=false) |
| Standard | 2 GB | 2 vCPU | 40 GB | OCR enabled, light traffic |
| Production | 4 GB | 4 vCPU | 80 GB | OCR + high traffic + logs |
