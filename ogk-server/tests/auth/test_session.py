from datetime import timedelta

import pytest

from app.core.db import utcnow
from app.modules.auth import service
from tests.conftest import csrf_headers, login, register

pytestmark = pytest.mark.anyio


def _cookie(response, name):
    return next(v for v in response.headers.get_list("set-cookie") if v.startswith(f"{name}="))


async def test_session_cookie_attributes(client):
    response = await register(client, "a@example.com")
    cookie = _cookie(response, "ogk_session").lower()
    assert "httponly" in cookie
    assert "secure" in cookie
    assert "samesite=lax" in cookie
    assert "max-age=43200" in cookie
    assert "path=/" in cookie


async def test_old_cookie_rejected_after_logout(client):
    await register(client, "a@example.com")
    old_token = client.cookies["ogk_session"]

    response = await client.post("/api/auth/logout", headers=await csrf_headers(client))
    assert response.status_code == 204
    assert "ogk_session" not in client.cookies

    client.cookies.set("ogk_session", old_token, domain="test.local")
    response = await client.get("/api/auth/me")
    assert response.status_code == 401
    assert response.json() == {"detail": "not_authenticated"}


async def test_login_replaces_previous_session(client):
    await register(client, "a@example.com")
    first = client.cookies["ogk_session"]
    await login(client, "a@example.com")
    assert client.cookies["ogk_session"] != first

    client.cookies.set("ogk_session", first, domain="test.local")
    assert (await client.get("/api/auth/me")).status_code == 401


async def test_session_expires_after_12_hours(client, monkeypatch):
    start = utcnow()
    monkeypatch.setattr(service, "now", lambda: start)
    await register(client, "a@example.com")
    monkeypatch.setattr(service, "now", lambda: start + timedelta(hours=11, minutes=59))
    assert (await client.get("/api/auth/me")).status_code == 200
    monkeypatch.setattr(service, "now", lambda: start + timedelta(hours=12))
    assert (await client.get("/api/auth/me")).status_code == 401


async def test_session_token_not_stored_in_db(client):
    from sqlalchemy import select

    from app.core.db import get_sessionmaker
    from app.modules.auth.models import AuthSession

    await register(client, "a@example.com")
    token = client.cookies["ogk_session"]
    async with get_sessionmaker()() as db:
        ids = list((await db.execute(select(AuthSession.id))).scalars())
    assert token not in ids
    assert len(ids) == 1 and len(ids[0]) == 64
