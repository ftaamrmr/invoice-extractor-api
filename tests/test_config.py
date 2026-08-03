import pytest

from app.config import Settings


def test_rejects_invalid_env():
    with pytest.raises(Exception):
        Settings(APP_ENV="invalid")


def test_rejects_weak_prod_rapidapi_secret():
    with pytest.raises(Exception):
        Settings(APP_ENV="production", REQUIRE_RAPIDAPI_SECRET=True, RAPIDAPI_PROXY_SECRET="change-me")


def test_allows_empty_api_key_if_direct_disabled():
    # REQUIRE_RAPIDAPI_SECRET=true so at least one auth method is enabled
    settings = Settings(APP_ENV="production", DIRECT_API_ACCESS_ENABLED=False, REQUIRE_RAPIDAPI_SECRET=True, RAPIDAPI_PROXY_SECRET="a-very-strong-secret-xyz")
    assert settings.API_KEY == ""


def test_rejects_non_positive_limits():
    with pytest.raises(Exception):
        Settings(MAX_FILE_SIZE_MB=0)


def test_rejects_production_with_both_auth_methods_disabled():
    """Production must reject when neither RapidAPI nor direct-API auth is enabled."""
    with pytest.raises(Exception, match="at least one auth method"):
        Settings(
            APP_ENV="production",
            REQUIRE_RAPIDAPI_SECRET=False,
            DIRECT_API_ACCESS_ENABLED=False,
        )


def test_allows_production_with_only_direct_api_enabled():
    s = Settings(
        APP_ENV="production",
        REQUIRE_RAPIDAPI_SECRET=False,
        DIRECT_API_ACCESS_ENABLED=True,
        API_KEY="a-strong-api-key-for-prod",
    )
    assert s.DIRECT_API_ACCESS_ENABLED is True


def test_allows_production_with_only_rapidapi_enabled():
    s = Settings(
        APP_ENV="production",
        REQUIRE_RAPIDAPI_SECRET=True,
        RAPIDAPI_PROXY_SECRET="a-very-strong-secret-xyz",
        DIRECT_API_ACCESS_ENABLED=False,
    )
    assert s.REQUIRE_RAPIDAPI_SECRET is True
