import httpx
import pytest

from app.core.config import get_settings
from app.core.db import get_engine, get_sessionmaker
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


@pytest.fixture
async def client(settings_env):
    transport = httpx.ASGITransport(app=create_app())
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    await get_engine().dispose()
