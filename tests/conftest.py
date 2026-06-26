"""
Pytest configuration and shared fixtures.

Sets deterministic test credentials at import time so tests are independent
of whatever is in the local .env file. Individual tests override APP_ENV
temporarily via the _ProductionMode context manager defined in test_extract.py.
"""
# ── Pin settings before any test module imports app code ─────────────────────
# This block must run before test modules are collected.
from app.config import settings

settings.API_KEY = "test-api-key-for-pytest-only"
settings.RAPIDAPI_PROXY_SECRET = "test-rapidapi-secret-for-pytest-only"
settings.APP_ENV = "development"   # tests that need production mode set it explicitly
settings.ENABLE_OCR = False        # disable OCR so tests run without Tesseract
settings.MAX_FILE_SIZE_MB = 10
