# Security Policy

This document outlines security practices and how to report security issues for Invoice Extractor API.

---

## Supported Versions

| Version | Supported |
|---|---|
| 1.0.x | Yes |

---

## Security Best Practices

### API Keys

- **Never commit your real API key to Git.** Use `.env` locally and set environment variables in production.
- Generate a strong key:
  ```bash
  python -c "import secrets; print(secrets.token_urlsafe(32))"
  ```
- Rotate keys if you suspect they have been leaked.
- For RapidAPI deployments, rely on `RAPIDAPI_PROXY_SECRET`; the provider dashboard generates and validates user keys for you.

### APP_ENV

- Always set `APP_ENV=production` in Coolify, RapidAPI, and any public deployment.
- `APP_ENV=development` disables auth enforcement and is only for local testing.
- The application defaults to `production` so accidents are less likely.

### File Uploads

- Only the following file types are accepted: **PDF, PNG, JPG, JPEG**.
- Maximum upload size is controlled by `MAX_FILE_SIZE_MB` (default: 10 MB).
- Uploaded files are processed entirely in memory or temporary buffers and are **never stored permanently** on the server.
- Files larger than the configured limit are rejected with HTTP 413.

### Reverse Proxy / Network

- Run the application behind a reverse proxy with HTTPS in production.
- The Dockerfile starts Uvicorn with `--proxy-headers --forwarded-allow-ips=*` so it works with Coolify, Traefik, and Nginx by default.
- Restrict the allowed proxy IPs if your deployment has a known static upstream range.

### Dependencies

- Keep dependencies updated and review the `requirements.txt` regularly.
- Pin versions to reproducible releases before deploying.

### Docker

- The Dockerfile runs the app as an unprivileged `appuser`.
- Do not run the container as root in production.
- Do not mount sensitive host paths unnecessarily.

---

## Supported Environments

- Local development: Python 3.11+
- Container runtime: Docker with the provided `Dockerfile` and `docker-compose.yml`
- Managed hosting: Coolify with Dockerfile buildpack
- Marketplace: RapidAPI using `X-RapidAPI-Proxy-Secret`

---

## Reporting Security Issues

If you discover a security vulnerability, please report it privately.

1. Email the maintainer at **security@your-domain.com** with a descriptive subject line.
2. Do not disclose the issue publicly until it has been addressed.
3. Include steps to reproduce, affected versions, and any suggested remediation.
4. Allow reasonable time for a fix before publishing details.

You will receive acknowledgement within 72 hours.

---

## Security-Related Configuration Checklist

- [ ] API_KEY is a strong random string, not the default placeholder
- [ ] RAPIDAPI_PROXY_SECRET is set if using RapidAPI
- [ ] APP_ENV=production in deployed environments
- [ ] HTTPS is enabled on the public domain
- [ ] MAX_FILE_SIZE_MB matches your infrastructure capacity
- [ ] ENABLE_OCR and OCR_LANGUAGES match your use case
- [ ] Server firewall only exposes ports 80/443/8000 as needed
- [ ] Logs do not contain uploaded file contents or API keys

