import pytest

from app.config import Settings


def test_rejects_invalid_env():
    with pytest.raises(Exception):
        Settings(APP_ENV="invalid")


def test_rejects_weak_prod_rapidapi_secret():
    with pytest.raises(Exception):
        Settings(APP_ENV="production", REQUIRE_RAPIDAPI_SECRET=True, RAPIDAPI_PROXY_SECRET="change-me")


def test_allows_empty_api_key_if_direct_disabled():
    settings = Settings(APP_ENV="production", DIRECT_API_ACCESS_ENABLED=False, REQUIRE_RAPIDAPI_SECRET=False)
    assert settings.API_KEY == ""


def test_rejects_non_positive_limits():
    with pytest.raises(Exception):
        Settings(MAX_FILE_SIZE_MB=0)
