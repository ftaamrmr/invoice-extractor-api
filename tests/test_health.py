"""
Tests for public endpoints: /health and /.

These must always return 200 without any authentication.
"""
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.config import settings


@pytest.mark.anyio
async def test_health_returns_200():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/health")
    assert r.status_code == 200


@pytest.mark.anyio
async def test_health_response_has_required_fields():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/health")
    body = r.json()
    assert body["status"] == "ok"
    assert body["service"] == settings.APP_NAME
    assert body["version"] == settings.APP_VERSION
    assert "environment" in body


@pytest.mark.anyio
async def test_health_works_without_api_key_in_production():
    """Health check must be public even when APP_ENV=production."""
    original = settings.APP_ENV
    settings.APP_ENV = "production"
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get("/health")
        assert r.status_code == 200
    finally:
        settings.APP_ENV = original


@pytest.mark.anyio
async def test_root_returns_200():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/")
    assert r.status_code == 200
