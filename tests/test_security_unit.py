import pytest
from fastapi import Request

from app.core.security import get_api_key_from_header, verify_admin


def test_get_api_key_from_header_present():
    scope = {"type": "http", "headers": [(b"x-api-key", b"abc")]}  # minimal ASGI scope
    req = Request(scope)
    assert get_api_key_from_header(req) == "abc"


def test_get_api_key_from_header_missing():
    scope = {"type": "http", "headers": []}
    req = Request(scope)
    with pytest.raises(Exception):
        get_api_key_from_header(req)


@pytest.mark.asyncio
async def test_verify_admin_invalid_and_valid(monkeypatch):
    # Missing
    with pytest.raises(Exception):
        await verify_admin(None)
    # Wrong
    with pytest.raises(Exception):
        await verify_admin("Bearer wrong")
    # Right
    from app.core.config import settings

    token = settings.ADMIN_BEARER_TOKEN
    ok = await verify_admin(f"Bearer {token}")
    assert ok == token
