"""Tests for rate-limiter identity resolution and spoofing prevention."""
from __future__ import annotations

from unittest.mock import MagicMock

from app.config import settings
from app.rate_limiter import InMemoryRateLimiter, resolve_identity


class _Headers:
    """Minimal case-insensitive headers stub."""

    def __init__(self, headers: dict) -> None:
        self._data = {k.lower(): v for k, v in headers.items()}

    def get(self, key: str, default: str = "") -> str:
        return self._data.get(key.lower(), default)


def _make_request(
    headers: dict,
    client_host: str = "1.2.3.4",
) -> MagicMock:
    req = MagicMock()
    req.client = MagicMock()
    req.client.host = client_host
    req.headers = _Headers(headers)
    return req


# ── proxy-secret validation ───────────────────────────────────────────────────

def test_rapidapi_user_trusted_when_proxy_secret_correct():
    correct_secret = settings.RAPIDAPI_PROXY_SECRET
    req = _make_request(
        {
            "X-RapidAPI-Proxy-Secret": correct_secret,
            "X-RapidAPI-User": "alice",
        }
    )
    identity = resolve_identity(req)
    assert identity == "rapidapi:alice"


def test_rapidapi_user_ignored_when_proxy_secret_wrong():
    req = _make_request(
        {
            "X-RapidAPI-Proxy-Secret": "completely-wrong-secret",
            "X-RapidAPI-User": "alice",
        }
    )
    identity = resolve_identity(req)
    assert identity.startswith("ip:")
    assert "alice" not in identity


def test_rapidapi_user_ignored_when_proxy_secret_missing():
    req = _make_request({"X-RapidAPI-User": "alice"})
    identity = resolve_identity(req)
    assert identity.startswith("ip:")
    assert "alice" not in identity


def test_rapidapi_subscription_trusted_when_proxy_secret_correct():
    correct_secret = settings.RAPIDAPI_PROXY_SECRET
    req = _make_request(
        {
            "X-RapidAPI-Proxy-Secret": correct_secret,
            "X-RapidAPI-Subscription": "pro-plan",
        }
    )
    identity = resolve_identity(req)
    assert identity == "rapidapi:pro-plan"


# ── spoofing: changing X-RapidAPI-User MUST NOT bypass rate limit ─────────────

def test_spoofed_rapidapi_user_does_not_bypass_rate_limit():
    """
    Without a valid proxy secret, different X-RapidAPI-User values from the same
    IP must all count against the same IP-based bucket — spoofing the header
    cannot reset or avoid the rate limit.
    """
    limiter = InMemoryRateLimiter()

    # Set a very low limit
    original_limit = settings.RATE_LIMIT_REQUESTS
    settings.RATE_LIMIT_REQUESTS = 2

    try:
        client_ip = "10.0.0.1"

        def ip_identity(_user_header: str) -> str:
            # No valid proxy secret → identity always resolves to IP
            req = _make_request({"X-RapidAPI-User": _user_header}, client_host=client_ip)
            return resolve_identity(req)

        # Exhaust the limit using the real IP identity
        ip_id = ip_identity("user-a")
        r1 = limiter.check(ip_id)
        r2 = limiter.check(ip_id)
        assert r1.allowed
        assert r2.allowed

        # Now spoofing a different user header — identity should still be the same IP
        spoof_id = ip_identity("user-b")
        assert spoof_id == ip_id, "Identity must be IP-based when proxy secret is absent"

        r3 = limiter.check(spoof_id)
        assert not r3.allowed, "Spoofed header must not reset the rate limit bucket"
    finally:
        settings.RATE_LIMIT_REQUESTS = original_limit


def test_legitimate_rapidapi_users_have_separate_buckets():
    """Two different RapidAPI users (with valid proxy secret) get independent buckets."""
    limiter = InMemoryRateLimiter()
    correct_secret = settings.RAPIDAPI_PROXY_SECRET

    original_limit = settings.RATE_LIMIT_REQUESTS
    settings.RATE_LIMIT_REQUESTS = 1

    try:
        req_alice = _make_request({"X-RapidAPI-Proxy-Secret": correct_secret, "X-RapidAPI-User": "alice"})
        req_bob = _make_request({"X-RapidAPI-Proxy-Secret": correct_secret, "X-RapidAPI-User": "bob"})

        id_alice = resolve_identity(req_alice)
        id_bob = resolve_identity(req_bob)

        assert id_alice != id_bob

        r_alice = limiter.check(id_alice)
        assert r_alice.allowed

        # Alice is now over limit, Bob should still be fine
        r_alice2 = limiter.check(id_alice)
        assert not r_alice2.allowed

        r_bob = limiter.check(id_bob)
        assert r_bob.allowed
    finally:
        settings.RATE_LIMIT_REQUESTS = original_limit
