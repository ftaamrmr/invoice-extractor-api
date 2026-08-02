from __future__ import annotations

from typing import Literal
from urllib.parse import urlparse

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_ENV_VALUES = {"development", "test", "production"}
_WEAK_SECRET_VALUES = {
    "",
    "change-me",
    "changeme",
    "default",
    "placeholder",
    "your-secret",
    "your-api-key",
    "test",
}


class Settings(BaseSettings):
    APP_NAME: str = "Invoice Extractor API"
    APP_VERSION: str = "1.1.0"
    APP_ENV: Literal["development", "test", "production"] = "development"
    LOG_LEVEL: str = "INFO"

    DIRECT_API_ACCESS_ENABLED: bool = False
    API_KEY: str = ""
    REQUIRE_RAPIDAPI_SECRET: bool = True
    RAPIDAPI_PROXY_SECRET: str = ""

    MAX_FILE_SIZE_MB: int = 5
    MAX_PDF_PAGES: int = 5
    MAX_IMAGE_PIXELS: int = 25_000_000
    MAX_EXTRACTED_TEXT_LENGTH: int = 200_000

    ENABLE_OCR: bool = True
    OCR_LANGUAGES: str = "eng+ara+fra+ita+hin"
    OCR_TIMEOUT_SECONDS: int = 25
    REQUEST_TIMEOUT_SECONDS: int = 35
    MAX_CONCURRENT_OCR_JOBS: int = 2

    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_REQUESTS: int = 30
    RATE_LIMIT_WINDOW_SECONDS: int = 60
    TRUSTED_PROXY_HEADERS: bool = True

    CORS_ALLOWED_ORIGINS: str = ""
    EXPOSE_DOCS: bool = True
    INCLUDE_RAW_TEXT: bool = False
    MAX_LINE_ITEMS: int = 50

    ENABLE_HSTS: bool = False
    HSTS_MAX_AGE_SECONDS: int = 31_536_000

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True, extra="ignore")

    @field_validator("APP_ENV", mode="before")
    @classmethod
    def validate_app_env(cls, value: str) -> str:
        value = str(value).strip().lower()
        if value not in _ENV_VALUES:
            raise ValueError("APP_ENV must be one of: development, test, production")
        return value

    @field_validator("LOG_LEVEL", mode="before")
    @classmethod
    def normalize_log_level(cls, value: str) -> str:
        value = str(value).upper().strip()
        if value not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
            raise ValueError("LOG_LEVEL must be a valid logging level")
        return value

    @field_validator(
        "MAX_FILE_SIZE_MB",
        "MAX_PDF_PAGES",
        "MAX_IMAGE_PIXELS",
        "MAX_EXTRACTED_TEXT_LENGTH",
        "OCR_TIMEOUT_SECONDS",
        "REQUEST_TIMEOUT_SECONDS",
        "MAX_CONCURRENT_OCR_JOBS",
        "RATE_LIMIT_REQUESTS",
        "RATE_LIMIT_WINDOW_SECONDS",
        "MAX_LINE_ITEMS",
        "HSTS_MAX_AGE_SECONDS",
    )
    @classmethod
    def positive_values_only(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("Numeric limits/timeouts must be > 0")
        return value

    @field_validator("MAX_PDF_PAGES")
    @classmethod
    def logical_pdf_pages(cls, value: int) -> int:
        if value < 1 or value > 200:
            raise ValueError("MAX_PDF_PAGES must be between 1 and 200")
        return value

    @field_validator("MAX_CONCURRENT_OCR_JOBS")
    @classmethod
    def min_ocr_jobs(cls, value: int) -> int:
        if value < 1:
            raise ValueError("MAX_CONCURRENT_OCR_JOBS must be >= 1")
        return value

    @field_validator("CORS_ALLOWED_ORIGINS")
    @classmethod
    def validate_cors_origins(cls, value: str) -> str:
        if not value.strip():
            return ""
        parts = [x.strip() for x in value.split(",") if x.strip()]
        for origin in parts:
            parsed = urlparse(origin)
            if parsed.scheme not in {"http", "https"} or not parsed.netloc:
                raise ValueError(f"Invalid CORS origin: {origin}")
        return ",".join(parts)

    @model_validator(mode="after")
    def validate_security_config(self) -> Settings:
        if self.APP_ENV != "production":
            return self

        secret = self.RAPIDAPI_PROXY_SECRET.strip()
        if self.REQUIRE_RAPIDAPI_SECRET:
            if len(secret) < 16 or secret.lower() in _WEAK_SECRET_VALUES or "change-me" in secret.lower():
                raise ValueError(
                    "Invalid production config: RAPIDAPI_PROXY_SECRET is required and must be strong when REQUIRE_RAPIDAPI_SECRET=true"
                )

        if self.DIRECT_API_ACCESS_ENABLED:
            key = self.API_KEY.strip()
            if len(key) < 16 or key.lower() in _WEAK_SECRET_VALUES or "change-me" in key.lower():
                raise ValueError(
                    "Invalid production config: API_KEY must be strong when DIRECT_API_ACCESS_ENABLED=true"
                )

        return self

    @property
    def cors_allowed_origins_list(self) -> list[str]:
        if self.CORS_ALLOWED_ORIGINS.strip():
            return [x.strip() for x in self.CORS_ALLOWED_ORIGINS.split(",") if x.strip()]
        if self.APP_ENV == "development":
            return ["http://localhost:3000", "http://localhost:5173", "http://127.0.0.1:3000"]
        return []


try:
    settings = Settings()
except Exception as exc:
    raise RuntimeError(f"Configuration error: {exc}") from exc
