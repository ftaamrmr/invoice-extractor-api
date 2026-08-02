import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from app.config import settings

settings.APP_ENV = "test"
settings.DIRECT_API_ACCESS_ENABLED = True
settings.API_KEY = "test-api-key-1234567890"
settings.REQUIRE_RAPIDAPI_SECRET = True
settings.RAPIDAPI_PROXY_SECRET = "test-rapidapi-secret-1234567890"
settings.ENABLE_OCR = False
settings.INCLUDE_RAW_TEXT = False
settings.RATE_LIMIT_ENABLED = False
