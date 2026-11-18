import httpx
import pytest
from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse

from app.core.config import get_settings
from app.core.security import client_ip

pytestmark = pytest.mark.anyio


def _app() -> FastAPI:
    app = FastAPI()

    @app.get("/ip")
    async def ip(request: Request):
        return PlainTextResponse(client_ip(request))

    return app


async def _ip(peer: str, forwarded: str | None = None) -> str:
    transport = httpx.ASGITransport(app=_app(), client=(peer, 50000))
    headers = {"X-Forwarded-For": forwarded} if forwarded else {}
    async with httpx.AsyncClient(transport=transport, base_url="https://test.local") as c:
        return (await c.get("/ip", headers=headers)).text


async def test_direct_call_uses_socket_ip(settings_env):
    assert await _ip("198.51.100.7") == "198.51.100.7"


async def test_direct_call_ignores_spoofed_header(settings_env):
    assert await _ip("198.51.100.7", "203.0.113.5") == "198.51.100.7"


@pytest.mark.parametrize("proxy", ["127.0.0.1", "::1"])
async def test_trusted_proxy_uses_forwarded_ip(settings_env, proxy):
    # Proxy của Vite (xfwd) chạy trên máy dev, kết nối đến server qua loopback.
    assert await _ip(proxy, "203.0.113.5") == "203.0.113.5"


async def test_trusted_proxy_without_header_uses_socket_ip(settings_env):
    assert await _ip("127.0.0.1") == "127.0.0.1"


async def test_rightmost_untrusted_hop_wins(settings_env):
    # Client tự thêm "1.2.3.4" vào header; proxy nối IP thật vào cuối.
    assert await _ip("127.0.0.1", "1.2.3.4, 203.0.113.5") == "203.0.113.5"
    assert await _ip("127.0.0.1", "203.0.113.5, 127.0.0.1") == "203.0.113.5"


async def test_browser_on_same_machine_via_proxy(settings_env):
    assert await _ip("127.0.0.1", "::1") == "::1"


async def test_invalid_header_falls_back_to_socket_ip(settings_env):
    assert await _ip("127.0.0.1", "not-an-ip") == "127.0.0.1"


async def test_trusted_proxies_configurable(settings_env, monkeypatch):
    monkeypatch.setenv("OGK_TRUSTED_PROXIES", "10.0.0.2")
    get_settings.cache_clear()
    assert await _ip("10.0.0.2", "203.0.113.5") == "203.0.113.5"
    assert await _ip("127.0.0.1", "203.0.113.5") == "127.0.0.1"
