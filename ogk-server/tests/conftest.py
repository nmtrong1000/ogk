"""The test client uses https so httpx sends the Secure session and CSRF cookies."""

import base64
import os

import httpx
import pytest

from app.core.config import get_settings
from app.core.crypto import get_cipher
from app.core.db import Base, get_engine, get_sessionmaker
from app.core.security import CSRF_COOKIE
from app.core.signing import generate_key_pair, get_signing_key
from app.main import create_app
from app.modules.auth import service as auth_service
from app.modules.auth.models import ROLE_ADMIN


def _clear_caches() -> None:
    get_settings.cache_clear()
    get_engine.cache_clear()
    get_sessionmaker.cache_clear()
    get_cipher.cache_clear()
    get_signing_key.cache_clear()


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
def settings_env(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("OGK_DATABASE_URL", f"sqlite+aiosqlite:///{tmp_path / 'data' / 'test.db'}")
    monkeypatch.setenv("OGK_TLS_CERT", str(tmp_path / "server.crt"))
    monkeypatch.setenv("OGK_TLS_KEY", str(tmp_path / "server.key"))
    monkeypatch.setenv("OGK_DATA_KEY", base64.urlsafe_b64encode(os.urandom(32)).decode())
    signing_key, _ = generate_key_pair(tmp_path / "keys")
    monkeypatch.setenv("OGK_POLICY_SIGNING_KEY", str(signing_key))
    _clear_caches()
    yield
    _clear_caches()


BASE_URL = "https://test.local"


async def create_tables() -> None:
    async with get_engine().begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


def make_client(app) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url=BASE_URL)


async def csrf_headers(c: httpx.AsyncClient) -> dict[str, str]:
    if CSRF_COOKIE not in c.cookies:
        await c.get("/api/health")
    return {"X-CSRF-Token": c.cookies[CSRF_COOKIE]}


@pytest.fixture
async def app(settings_env):
    await create_tables()
    yield create_app()
    await get_engine().dispose()


@pytest.fixture
async def client(app):
    async with make_client(app) as c:
        yield c


PASSWORD = "dung-mat-khau-1"


async def register(c: httpx.AsyncClient, email: str, password: str = PASSWORD) -> httpx.Response:
    return await c.post(
        "/api/auth/register", json={"email": email, "password": password}, headers=await csrf_headers(c)
    )


async def login(c: httpx.AsyncClient, email: str, password: str = PASSWORD) -> httpx.Response:
    return await c.post("/api/auth/login", json={"email": email, "password": password}, headers=await csrf_headers(c))


async def create_admin(email: str = "admin@ogk.local", password: str = PASSWORD):
    async with get_sessionmaker()() as db:
        return await auth_service.create_account(db, email, password, role=ROLE_ADMIN)


@pytest.fixture
async def parent(client):
    response = await register(client, "parent@example.com")
    assert response.status_code == 201
    return client


@pytest.fixture
async def admin(app):
    await create_admin()
    async with make_client(app) as c:
        assert (await login(c, "admin@ogk.local")).status_code == 200
        yield c
