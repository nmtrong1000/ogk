import pytest
from sqlalchemy import select

from app.core.db import get_sessionmaker
from app.modules.auth.models import Account
from tests.auth.conftest import register

pytestmark = pytest.mark.anyio


async def test_short_password_rejected(client):
    response = await register(client, "a@example.com", "123456789")
    assert response.status_code == 422
    assert response.json() == {"detail": "password_too_short"}


async def test_password_stored_as_argon2id(client):
    response = await register(client, "  A@Example.com ", "0123456789")
    assert response.status_code == 201
    assert response.json()["email"] == "a@example.com"
    assert response.json()["role"] == "parent"
    async with get_sessionmaker()() as db:
        account = (await db.execute(select(Account))).scalar_one()
    assert account.password_hash.startswith("$argon2id$")
    assert "0123456789" not in account.password_hash


async def test_register_logs_in(client):
    await register(client, "a@example.com")
    response = await client.get("/api/auth/me")
    assert response.status_code == 200
    assert response.json()["email"] == "a@example.com"


async def test_duplicate_email(client):
    await register(client, "a@example.com")
    client.cookies.delete("ogk_session")
    response = await register(client, "A@example.com")
    assert response.status_code == 409
    assert response.json() == {"detail": "email_taken"}


@pytest.mark.parametrize("email", ["no-at", "@example.com", "a@", "a@b@c", "a b@example.com"])
async def test_invalid_email(client, email):
    response = await register(client, email)
    assert response.status_code == 422
    assert response.json() == {"detail": "invalid_email"}
