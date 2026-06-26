# ── Base image ────────────────────────────────────────────────────────────────
# Use Python 3.11 slim for a small, production-ready image.
FROM python:3.11-slim

# ── System dependencies ───────────────────────────────────────────────────────
# - tesseract-ocr        : Tesseract OCR engine
# - tesseract-ocr-eng    : English language pack (required)
# - tesseract-ocr-ara    : Arabic language pack (required for Arabic invoices)
# - poppler-utils        : PDF rendering utilities (used by some OCR workflows)
# - libgl1 / libglib2.0  : Required by OpenCV / PyMuPDF rendering
# - curl                 : Used by Coolify health checks
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-eng \
    tesseract-ocr-ara \
    tesseract-ocr-fra \
    tesseract-ocr-ita \
    tesseract-ocr-hin \
    poppler-utils \
    libgl1 \
    libglib2.0-0 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# ── Working directory ─────────────────────────────────────────────────────────
WORKDIR /app

# ── Python dependencies ───────────────────────────────────────────────────────
# Copy requirements first to leverage Docker layer caching.
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# ── Application code ──────────────────────────────────────────────────────────
COPY . .

# ── Non-root user for security ────────────────────────────────────────────────
RUN useradd --system --no-create-home appuser && \
    chown -R appuser:appuser /app
USER appuser

# ── Runtime ───────────────────────────────────────────────────────────────────
EXPOSE 8000

# --proxy-headers       : Trust X-Forwarded-* headers from Coolify / Nginx
# --forwarded-allow-ips : Accept proxy headers from any upstream IP
CMD ["uvicorn", "app.main:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--proxy-headers", \
     "--forwarded-allow-ips=*"]
