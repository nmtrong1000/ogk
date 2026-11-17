import httpx
import pytest

from app.core.db import get_sessionmaker
from app.modules.auth import service
from app.modules.auth.models import ROLE_ADMIN
from tests.conftest import csrf_headers, make_client

PASSWORD = "dung-mat-khau-1"


async def register(c: httpx.AsyncClient, email: str, password: str = PASSWORD) -> httpx.Response:
    return await c.post("/api/auth/register", json={"email": email, "password": password}, headers=await csrf_headers(c))


async def login(c: httpx.AsyncClient, email: str, password: str = PASSWORD) -> httpx.Response:
    return await c.post("/api/auth/login", json={"email": email, "password": password}, headers=await csrf_headers(c))


async def create_admin(email: str = "admin@ogk.local", password: str = PASSWORD):
    async with get_sessionmaker()() as db:
        return await service.create_account(db, email, password, role=ROLE_ADMIN)


@pytest.fixture
async def parent(client):
    """Client đã đăng nhập bằng một tài khoản phụ huynh."""
    response = await register(client, "parent@example.com")
    assert response.status_code == 201
    return client


@pytest.fixture
async def admin(app):
    await create_admin()
    async with make_client(app) as c:
        assert (await login(c, "admin@ogk.local")).status_code == 200
        yield c
