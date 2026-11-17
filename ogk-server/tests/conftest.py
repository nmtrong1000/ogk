import httpx
import pytest

from app.core.config import get_settings
from app.core.db import Base, get_engine, get_sessionmaker
from app.core.security import CSRF_COOKIE
from app.main import create_app


def _clear_caches() -> None:
    get_settings.cache_clear()
    get_engine.cache_clear()
    get_sessionmaker.cache_clear()


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
def settings_env(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("OGK_DATABASE_URL", f"sqlite+aiosqlite:///{tmp_path / 'data' / 'test.db'}")
    monkeypatch.setenv("OGK_TLS_CERT", str(tmp_path / "server.crt"))
    monkeypatch.setenv("OGK_TLS_KEY", str(tmp_path / "server.key"))
    _clear_caches()
    yield
    _clear_caches()


BASE_URL = "https://test.local"


async def create_tables() -> None:
    async with get_engine().begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


def make_client(app) -> httpx.AsyncClient:
    # https để httpx gửi cookie Secure.
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url=BASE_URL)


async def csrf_headers(c: httpx.AsyncClient) -> dict[str, str]:
    """Lấy cookie ogk_csrf (gọi một GET nếu chưa có) và trả header để gửi kèm request ghi."""
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
