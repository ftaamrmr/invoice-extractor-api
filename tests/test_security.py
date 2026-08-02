import pytest

from app import security
from app.config import settings
from app.errors import APIError


def test_secure_equals_uses_compare_digest(monkeypatch):
    called = {"v": False}

    def fake_compare(a, b):
        called["v"] = True
        return a == b

    monkeypatch.setattr(security.secrets, "compare_digest", fake_compare)
    assert security._secure_equals("a", "a")
    assert called["v"] is True


def test_rapidapi_secret_auth_passes():
    settings.REQUIRE_RAPIDAPI_SECRET = True
    settings.RAPIDAPI_PROXY_SECRET = "rapidapi-secret-123456"
    security.verify_api_key(x_api_key=None, x_rapidapi_proxy_secret="rapidapi-secret-123456")


def test_direct_access_disabled_rejects_api_key():
    settings.DIRECT_API_ACCESS_ENABLED = False
    settings.API_KEY = "direct-key-123456"
    with pytest.raises(APIError):
        security.verify_api_key(x_api_key="direct-key-123456", x_rapidapi_proxy_secret=None)
