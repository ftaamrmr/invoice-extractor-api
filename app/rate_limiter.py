from __future__ import annotations

import ipaddress
import secrets
import threading
import time
from dataclasses import dataclass

from fastapi import Request

from app.config import settings


@dataclass
class RateLimitResult:
    allowed: bool
    remaining: int
    retry_after: int
    limit: int


class InMemoryRateLimiter:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._buckets: dict[str, dict[str, float | int]] = {}
        self._ops = 0

    def _cleanup(self, now: float) -> None:
        cutoff = now - (settings.RATE_LIMIT_WINDOW_SECONDS * 3)
        expired = [k for k, v in self._buckets.items() if v["window_start"] < cutoff]
        for key in expired:
            self._buckets.pop(key, None)

    def check(self, identity: str) -> RateLimitResult:
        now = time.time()
        with self._lock:
            self._ops += 1
            if self._ops % 200 == 0:
                self._cleanup(now)

            bucket = self._buckets.get(identity)
            if bucket is None:
                self._buckets[identity] = {"window_start": now, "count": 1}
                return RateLimitResult(True, settings.RATE_LIMIT_REQUESTS - 1, 0, settings.RATE_LIMIT_REQUESTS)

            window_start = float(bucket["window_start"])
            count = int(bucket["count"])
            elapsed = now - window_start

            if elapsed >= settings.RATE_LIMIT_WINDOW_SECONDS:
                bucket["window_start"] = now
                bucket["count"] = 1
                return RateLimitResult(True, settings.RATE_LIMIT_REQUESTS - 1, 0, settings.RATE_LIMIT_REQUESTS)

            if count >= settings.RATE_LIMIT_REQUESTS:
                retry_after = max(1, int(settings.RATE_LIMIT_WINDOW_SECONDS - elapsed))
                return RateLimitResult(False, 0, retry_after, settings.RATE_LIMIT_REQUESTS)

            bucket["count"] = count + 1
            remaining = max(0, settings.RATE_LIMIT_REQUESTS - int(bucket["count"]))
            return RateLimitResult(True, remaining, 0, settings.RATE_LIMIT_REQUESTS)


def _safe_client_ip(request: Request) -> str:
    fallback = (request.client.host if request.client else "unknown").strip() or "unknown"
    if not settings.TRUSTED_PROXY_HEADERS:
        return fallback

    try:
        client_ip_obj = ipaddress.ip_address(fallback)
        proxy_trusted = client_ip_obj.is_private or client_ip_obj.is_loopback
    except Exception:
        proxy_trusted = False

    if not proxy_trusted:
        return fallback

    forwarded_for = request.headers.get("x-forwarded-for", "")
    if forwarded_for:
        candidate = forwarded_for.split(",")[0].strip()
        try:
            ipaddress.ip_address(candidate)
            return candidate
        except Exception:
            pass

    x_real_ip = request.headers.get("x-real-ip", "").strip()
    if x_real_ip:
        try:
            ipaddress.ip_address(x_real_ip)
            return x_real_ip
        except Exception:
            pass

    return fallback


def _rapidapi_proxy_secret_valid(request: Request) -> bool:
    """Return True only when the request carries a correct RapidAPI proxy secret."""
    configured_secret = settings.RAPIDAPI_PROXY_SECRET.strip()
    if not configured_secret:
        return False
    incoming_secret = request.headers.get("x-rapidapi-proxy-secret", "")
    if not incoming_secret:
        return False
    return secrets.compare_digest(incoming_secret, configured_secret)


def resolve_identity(request: Request) -> str:
    # Only trust RapidAPI identity headers when the proxy secret is verified.
    if _rapidapi_proxy_secret_valid(request):
        rapidapi_identity = request.headers.get("x-rapidapi-user") or request.headers.get("x-rapidapi-subscription")
        if rapidapi_identity:
            return f"rapidapi:{rapidapi_identity[:128]}"
    return f"ip:{_safe_client_ip(request)}"


rate_limiter = InMemoryRateLimiter()
