import json

import httpx
import pytest

from service.core.server_client import ServerClient
from tests.core.conftest import make_ca


@pytest.mark.anyio
async def test_health_over_https_with_ca(https_server):
    url, ca_path = https_server.url, https_server.ca_path
    client = ServerClient(url, ca_path)
    try:
        assert await client.health() == {"status": "ok"}
    finally:
        await client.aclose()


@pytest.mark.anyio
async def test_health_rejects_unknown_ca(https_server, tmp_path):
    url = https_server.url
    _, other_ca = make_ca(tmp_path, "other-ca")
    client = ServerClient(url, other_ca)
    try:
        with pytest.raises(httpx.ConnectError):
            await client.health()
    finally:
        await client.aclose()


@pytest.mark.anyio
async def test_health_raises_on_server_error():
    transport = httpx.MockTransport(lambda request: httpx.Response(503, json={"status": "error"}))
    client = ServerClient("https://server", transport=transport)
    try:
        with pytest.raises(httpx.HTTPStatusError):
            await client.health()
    finally:
        await client.aclose()


@pytest.mark.anyio
async def test_create_child_view_code_posts_with_device_token():
    seen = []

    def handle(request):
        seen.append(request)
        return httpx.Response(201, json={"expires_at": "2026-11-19T08:01:00Z"})

    client = ServerClient("https://server", transport=httpx.MockTransport(handle))
    try:
        result = await client.create_child_view_code("tok", 9, "c" * 43)
    finally:
        await client.aclose()
    assert result == {"expires_at": "2026-11-19T08:01:00Z"}
    (request,) = seen
    assert (request.method, request.url.path) == ("POST", "/api/device/child-view-codes")
    assert request.headers["Authorization"] == "Bearer tok"
    assert json.loads(request.content) == {"child_id": 9, "code": "c" * 43}
