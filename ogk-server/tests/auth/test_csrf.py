import pytest

from tests.conftest import PASSWORD, csrf_headers

pytestmark = pytest.mark.anyio

BODY = {"email": "a@example.com", "password": PASSWORD}


async def test_get_sets_csrf_cookie(client):
    response = await client.get("/api/health")
    cookie = next(v for v in response.headers.get_list("set-cookie") if v.startswith("ogk_csrf="))
    assert "secure" in cookie.lower()
    assert "httponly" not in cookie.lower()


async def test_write_without_token_rejected(client):
    await client.get("/api/health")
    response = await client.post("/api/auth/register", json=BODY)
    assert response.status_code == 403
    assert response.json() == {"detail": "csrf_failed"}


async def test_write_without_cookie_rejected(client):
    response = await client.post("/api/auth/register", json=BODY, headers={"X-CSRF-Token": "abc"})
    assert response.status_code == 403


async def test_write_with_wrong_token_rejected(client):
    await client.get("/api/health")
    response = await client.post("/api/auth/register", json=BODY, headers={"X-CSRF-Token": "sai"})
    assert response.status_code == 403


async def test_logout_without_token_rejected(client):
    assert (await client.post("/api/auth/register", json=BODY, headers=await csrf_headers(client))).status_code == 201
    response = await client.post("/api/auth/logout")
    assert response.status_code == 403
    assert (await client.get("/api/auth/me")).status_code == 200


async def test_login_rotates_csrf_token(client):
    before = (await csrf_headers(client))["X-CSRF-Token"]
    await client.post("/api/auth/register", json=BODY, headers={"X-CSRF-Token": before})
    assert client.cookies["ogk_csrf"] != before
