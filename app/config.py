"""
Application configuration loaded from environment variables via .env file.

IMPORTANT: APP_ENV defaults to "production" so that authentication is always
enforced on Coolify and RapidAPI deployments. Set APP_ENV=development only
for local development to skip auth during testing.
"""
from pydantic_settings import BaseSettings
from pydantic_settings import SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "Invoice Extractor API"
    APP_VERSION: str = "1.0.0"

    # Defaults to production so deployed instances are always protected.
    # Set APP_ENV=development in your local .env to skip auth during testing.
    APP_ENV: str = "production"

    # ── Authentication ────────────────────────────────────────────────────────
    # Change these before deploying. Never use the default values in production.
    API_KEY: str = "change-me-api-key"
    RAPIDAPI_PROXY_SECRET: str = "change-me-rapidapi-secret"

    # ── File limits ───────────────────────────────────────────────────────────
    MAX_FILE_SIZE_MB: int = 10

    # ── OCR settings ─────────────────────────────────────────────────────────
    # Set ENABLE_OCR=false to disable OCR (app still works for text-based PDFs)
    ENABLE_OCR: bool = True
    # Tesseract language string. Requires matching language packs installed.
    # Common values: "eng" | "ara" | "eng+ara"
    OCR_LANGUAGES: str = "eng+ara"

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
    )


settings = Settings()
