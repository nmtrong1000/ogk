import httpx
import pytest

from service.core.server_client import KEEPALIVE_SECONDS, CertificatePinError, ServerClient, cert_sha256

pytestmark = pytest.mark.anyio


async def test_matching_pin_connects(https_server):
    client = ServerClient(https_server.url, https_server.ca_path, pin_sha256=cert_sha256(https_server.cert_der))
    try:
        assert await client.health() == {"status": "ok"}
    finally:
        await client.aclose()


async def test_other_pin_is_rejected(https_server):
    client = ServerClient(https_server.url, https_server.ca_path, pin_sha256="0" * 64)
    try:
        with pytest.raises(CertificatePinError):
            await client.health()
    finally:
        await client.aclose()


async def test_pin_error_is_a_connect_error(https_server):
    client = ServerClient(https_server.url, https_server.ca_path, pin_sha256="0" * 64)
    try:
        with pytest.raises(httpx.ConnectError):
            await client.health()
    finally:
        await client.aclose()


async def test_new_server_cert_from_same_ca_is_rejected(https_server):
    pin = cert_sha256(https_server.cert_der)
    https_server.rotate()
    client = ServerClient(https_server.url, https_server.ca_path, pin_sha256=pin)
    try:
        with pytest.raises(CertificatePinError):
            await client.health()
    finally:
        await client.aclose()


async def test_capture_records_cert(https_server):
    client = ServerClient(https_server.url, https_server.ca_path, capture_pin=True)
    try:
        assert client.peer_cert_sha256 is None
        await client.health()
        assert client.peer_cert_sha256 == cert_sha256(https_server.cert_der)
    finally:
        await client.aclose()


async def test_pin_does_not_skip_ca_check(https_server, tmp_path):
    from tests.core.conftest import make_ca

    _, other_ca = make_ca(tmp_path, "other-ca")
    client = ServerClient(https_server.url, other_ca, pin_sha256=cert_sha256(https_server.cert_der))
    try:
        with pytest.raises(httpx.ConnectError):
            await client.health()
    finally:
        await client.aclose()


async def test_rejected_before_request_is_sent(https_server, monkeypatch):
    seen = []
    from tests.core import conftest

    monkeypatch.setattr(conftest.Handler, "do_GET", lambda self: seen.append(self.path))
    client = ServerClient(https_server.url, https_server.ca_path, pin_sha256="0" * 64)
    try:
        with pytest.raises(CertificatePinError):
            await client.device_me("secret-token")
    finally:
        await client.aclose()
    assert seen == []


def test_pinning_needs_ca():
    with pytest.raises(ValueError):
        ServerClient("https://server", pin_sha256="0" * 64)


async def test_pinned_pool_drops_idle_connections_before_server_does(https_server):
    client = ServerClient(https_server.url, https_server.ca_path, pin_sha256=cert_sha256(https_server.cert_der))
    try:
        pool = client._client._transport._pool
        assert pool._keepalive_expiry == KEEPALIVE_SECONDS < 5
    finally:
        await client.aclose()
